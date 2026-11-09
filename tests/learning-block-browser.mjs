import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import {readFile,mkdir} from 'node:fs/promises';
import assert from 'node:assert/strict';
const files=['python-decisions','python-repetition','python-lists','python-dictionaries'];
const chapters=await Promise.all(files.map(f=>readFile(`content/${f}.json`,'utf8').then(JSON.parse)));
const setup=`import tempfile
from pathlib import Path
from server import make_server,catalog,connect,timestamp
tmp=tempfile.TemporaryDirectory()
srv=make_server(port=0,database=Path(tmp.name)/'qa.sqlite3')
with connect(srv.database) as db:
    for m in catalog()['missions']:
        if m['chapter']=='python-decisions': break
        if m.get('orientation'): continue
        db.execute('INSERT INTO completions VALUES(?,?,?,?)',(m['id'],m['reference']['code'],timestamp(),m['version']))
print(srv.server_port,flush=True)
srv.serve_forever()
`;
const server=spawn('python',['-u','-c',setup],{env:{...process.env,OPENAI_API_KEY:''},stdio:['ignore','pipe','pipe']});
let browser,page;
try {
 const port=await new Promise((resolve,reject)=>{server.stdout.once('data',d=>resolve(Number(String(d).trim())));server.once('error',reject);server.once('exit',code=>reject(Error('Server exit '+code)));});
 const base=`http://127.0.0.1:${port}`;
 browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000}});
 await context.route('**/*',r=>r.request().url().startsWith(base)?r.continue():r.abort());
 page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base);
 await page.getByRole('heading',{name:chapters[0].missions[0].title,exact:true}).waitFor();
 assert.equal(await page.locator('#xp').textContent(),'560 XP');
 // The project-to-foundations boundary must keep earlier achievements intact.
 await page.locator('[data-id="py-session-03-tool"]').click();
 await page.getByRole('button',{name:'Next mission →'}).click();
 await page.getByRole('heading',{name:chapters[0].missions[0].title,exact:true}).waitFor();
 const editor=page.getByRole('textbox',{name:'Python code',exact:true});
 const write=async code=>{
   const saved=page.waitForResponse(r=>r.url().endsWith('/api/save')&&r.ok()&&r.request().postDataJSON()?.code===code);
   await editor.fill(code);await saved;
 };
 const action=async(name,pattern)=>{await page.getByRole('button',{name,exact:true}).click();await page.locator('#feedback').filter({hasText:pattern}).waitFor({timeout:45000});};
 const bookHas=async title=>{
   await page.locator('#open-grimoire').click();await page.locator('#grimoire-index button').first().waitFor();
   const found=await page.locator('#grimoire-index').getByRole('button',{name:title,exact:true}).count();
   await page.locator('#grimoire-close').click();return !!found;
 };
 assert.equal(await bookHas('Both conditions: and'),false);
 await mkdir('qa',{recursive:true});let xp=560,passed=0;
 for(const chapter of chapters) {
   for(const [i,m] of chapter.missions.entries()) {
     assert.equal(await page.locator('#lesson-title').textContent(),m.title);
     assert.equal(await page.locator('#compare').isVisible(),false);
     if(i<chapter.missions.length-1)assert.equal(await page.locator(`[data-id="${chapter.missions[i+1].id}"]`).isDisabled(),true);
     if(i===0) {
       assert.equal(await page.locator('#offline-hints').evaluate(e=>e.open),false);
       await action('Submit','checks passed. Nothing lost');
       await page.screenshot({path:`qa/${chapter.id}-start.png`,fullPage:true});
     }
     if(m.id==='py-lists-09-sort') {
       await write('def ordered_times(times):\n    times.sort()\n    return times');
       await action('Submit','checks passed. Nothing lost');
       assert.match(await page.locator('#test-results').textContent(),/changed an input|Returned an input object/);
     }
     await write(m.reference.code);
     if(m.boss) await action('Run','Run finished');
     await action('Test',/All \d+ example checks passed/);
     await action('Submit',m.boss?'Chapter complete!':'Mission complete!');
     xp+=m.xp;passed++;
     assert.equal(await page.locator('#xp').textContent(),`${xp} XP`);
     const ref=await(await page.request.get(`${base}/api/reference/${m.id}`)).json();
     assert.equal(ref.submitted_code,m.reference.code);
     if(m.id==='py-decisions-02-and')assert.equal(await bookHas('Both conditions: and'),true);
     if(m.id==='py-lists-04-append')assert.equal(await bookHas('Mutating a list with append'),true);
     if(m.boss) {
       assert.match(await page.locator('#total-progress').textContent(),new RegExp(chapter.badge));
       await page.reload();await page.getByRole('button',{name:'Back to editing',exact:true}).waitFor();
       assert.equal(await page.locator('#xp').textContent(),`${xp} XP`);
       console.log(`Passed chapter: ${chapter.title} (${passed}/42 missions)`);
     }
     if(passed<42)await page.getByRole('button',{name:'Next mission →'}).click();
   }
 }
 assert.equal(xp,1060);assert.match(await page.locator('.course-note').textContent(),/All caught up/);
 const exported=await(await page.request.get(`${base}/api/export`)).json();assert.equal(Object.keys(exported.completions).length,88);
 await page.locator('#open-grimoire').click();await page.locator('#grimoire-index button').first().waitFor();
 const book=JSON.parse(await readFile('content/grimoire.json','utf8'));
 assert.equal(await page.locator('#grimoire-index button').count(),book.entries.filter(e=>exported.completions[e.mission]).length);
 await page.locator('#grimoire-search').fill('items');
 await page.screenshot({path:'qa/learning-block-grimoire.png'});
 await page.locator('#grimoire-close').click();
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Code & results',exact:true}).click();
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 assert.deepEqual(errors,[]);
 console.log('Passed: 42 missions, 4 chapter boundaries/badges, collection grading, hidden hints, progressive grimoire unlocks, comparisons, persistence, 500 new XP and narrow layout.');
} catch(e) {if(page){await page.screenshot({path:'qa/learning-block-failure.png'});console.log(await page.locator('#feedback').textContent());}throw e;}
finally {await browser?.close();server.kill();}

