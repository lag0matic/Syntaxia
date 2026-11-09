import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import {readFile,mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';

const setup = `import os,tempfile
from pathlib import Path
from server import make_server,catalog,connect,timestamp
tmp=tempfile.TemporaryDirectory()
srv=make_server(port=0,database=Path(tmp.name)/'qa.sqlite3')
if os.getenv('SYNTAXIA_QA_EXISTING')=='1':
    with connect(srv.database) as db:
        for m in catalog()['missions']:
            if m['id']=='py-decisions-02-and': break
            if not m.get('orientation'):
                db.execute('INSERT INTO completions VALUES(?,?,?,?)',(m['id'],m['reference']['code'],timestamp(),m['version']))
print(srv.server_port,flush=True)
srv.serve_forever()
`;
const servers=[];
async function start(existing) {
  const child=spawn('python',['-u','-c',setup],{env:{...process.env,OPENAI_API_KEY:'',SYNTAXIA_QA_EXISTING:existing?'1':'0'},stdio:['ignore','pipe','pipe']});
  servers.push(child);
  const port=await new Promise((resolve,reject)=>{child.stdout.once('data',d=>resolve(Number(String(d).trim())));child.once('error',reject);child.once('exit',code=>reject(Error('Test server exited '+code)));});
  return 'http://127.0.0.1:'+port;
}
let browser;
try {
  const fresh=await start(false),existing=await start(true);
  browser=await chromium.launch({channel:'msedge',headless:true});
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  await context.route('**/*',route=>[fresh,existing].some(origin=>route.request().url().startsWith(origin))?route.continue():route.abort());
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await mkdir('qa',{recursive:true});
  await page.goto(fresh);
  await page.getByRole('heading',{name:'Your first Python program',exact:true}).waitFor();
  assert.equal(await page.locator('#xp').textContent(),'0 XP');
  assert.equal(await page.locator('#up-next-mission').textContent(),'Your first Python program');
  assert.equal(await page.locator('[data-id="py-01-message"]').isDisabled(),false);
  await page.screenshot({path:'qa/beginner-tutorial.png'});
  const action=async(name,pattern)=>{await page.getByRole('button',{name,exact:true}).click();await page.locator('#feedback').filter({hasText:pattern}).waitFor({timeout:45000});};
  const write=async code=>{const response=page.waitForResponse(r=>r.url().endsWith('/api/save')&&r.ok()&&r.request().postDataJSON()?.code===code);await page.getByRole('textbox',{name:'Python code',exact:true}).fill(code);await response;};
  async function openBook() { await page.locator('#open-grimoire').click(); }
  async function bookHas(title) {
    await openBook();await page.locator('#grimoire-index button').first().waitFor();
    const found=await page.locator('#grimoire-index').getByRole('button',{name:title,exact:true}).count();
    await page.locator('#grimoire-close').click();return !!found;
  }
  await openBook();
  await page.locator('#grimoire-status').filter({hasText:'Reference pages unlock'}).waitFor();
  await page.locator('#grimoire-close').click();
  await action('Run','Run finished');
  assert.match(await page.locator('#output').textContent(),/Hello, world!/);
  await action('Submit','checks passed. Nothing lost');
  assert.equal(await page.locator('#xp').textContent(),'0 XP');
  await page.locator('#offline-hints > summary').click();
  await page.locator('#hints details > summary').nth(1).click();
  assert.equal(await page.locator('#hints details').nth(1).locator('code.inline-code').textContent(),'print()');
  await page.locator('#offline-hints > summary').click();
  await write('print("Hello, Syntaxia!")\n');
  await action('Test',/All 1 example checks passed/);
  await action('Submit','Chapter complete!');
  assert.match(await page.locator('#total-progress').textContent(),/First Page/);
  await page.locator('.comparison-notes code.inline-code').first().waitFor();
  assert.equal(await bookHas('Strings and quotation marks'),true);
  assert.equal(await bookHas('Insert values with f-strings'),false);
  await page.getByRole('button',{name:'Next mission →'}).click();
  const review=JSON.parse(await readFile('content/python-review.json','utf8'));
  for (const [i,mission] of review.missions.entries()) {
    await page.getByRole('heading',{name:mission.title,exact:true}).waitFor();
    if(i===0)assert.match(await page.locator('#total-progress').textContent(),/Chapter 1 · Console foundations/);
    await write(mission.reference.code);
    await action('Submit',i===6?'Chapter complete!':'Mission complete!');
    const titles=['Insert values with f-strings','Find a wrong result','Input and numeric conversion','Indentation and blocks','for loops and range()','Return, print and None','Either condition: or'];
    assert.equal(await bookHas(titles[i]),true);
    if(i<6)await page.getByRole('button',{name:'Next mission →'}).click();
  }
  assert.equal(await page.locator('#xp').textContent(),'100 XP');
  // A returning learner is not diverted to the tutorial, and code spans are
  // rendered safely even for angle brackets and arbitrary expressions.
  await page.route(existing+'/api/bootstrap',async route=>{
    const response=await route.fetch();const data=await response.json();
    const target=data.course.missions.find(m=>m.id==='py-decisions-02-and');
    target.lesson.push({heading:'Literal text check',text:'Ordinary and remains prose; `data["x"] ** 2` is code. <b>literal</b>.'});
    await route.fulfill({response,json:data});
  });
  await page.goto(existing);
  await page.getByRole('heading',{name:'Stay inside the window',exact:true}).waitFor();
  assert.equal(await page.locator('#up-next-mission').textContent(),'Stay inside the window');
  const code=await page.locator('#lesson-body p code.inline-code').allTextContents();
  assert.ok(code.includes('and'));assert.ok(code.includes('low <= value <= high'));
  assert.ok(code.includes('data["x"] ** 2'));
  assert.equal(await page.locator('#lesson-body b').count(),0);
  assert.match(await page.locator('#lesson-body').textContent(),/<b>literal<\/b>/);
  assert.equal(await page.locator('#lesson-body p code.inline-code').first().evaluate(e=>getComputedStyle(e).color===getComputedStyle(e.parentElement).color),false);
  await page.screenshot({path:'qa/inline-python-expressions.png'});
  assert.equal(await bookHas('Your first Python program'),false);
  assert.equal(await bookHas('Both conditions: and'),false);
  await page.locator('[data-id="py-session-03-tool"]').click();
  await page.getByRole('heading',{name:'Build the session summary tool',exact:true}).waitFor();
  assert.match(await page.locator('#total-progress').textContent(),/Session Scribe/);
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);
  console.log('Passed: fresh tutorial, optional returning-learner path, early grimoire unlocks, inline syntax and literal text safety, unchanged prior badges, narrow layout.');
} finally {await browser?.close();for(const server of servers)server.kill();}

