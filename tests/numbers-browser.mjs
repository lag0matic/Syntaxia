import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { readFile, mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';

// Simulate completed prerequisites in an isolated database, never the real one.
const setup = `import tempfile
from pathlib import Path
from server import make_server, catalog, connect, timestamp
tmp=tempfile.TemporaryDirectory()
srv=make_server(port=0,database=Path(tmp.name)/'qa.sqlite3')
with connect(srv.database) as db:
    for m in catalog()['missions']:
        if m['chapter'] in ('python-foundations', 'python-functions', 'python-scope'):
            db.execute('INSERT INTO completions VALUES(?,?,?,?)',(m['id'],m['reference']['code'],timestamp(),m['version']))
print(srv.server_port,flush=True)
srv.serve_forever()
`;
const server = spawn('python', ['-u', '-c', setup], { stdio:['ignore','pipe','pipe'] });
let browser, page;
try {
  const port = await new Promise((resolve,reject)=>{server.stdout.once('data',data=>resolve(Number(String(data).trim())));server.once('error',reject);server.once('exit',code=>reject(new Error(`Test server exited ${code}`)));});
  const base = `http://127.0.0.1:${port}`;
  browser = await chromium.launch({channel:'msedge',headless:true});
  const context = await browser.newContext({viewport:{width:1440,height:1000}});
  await context.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
  page = await context.newPage();
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);
  await page.getByRole('heading',{name:'Quote the whole job',exact:true}).waitFor();
  // Revisit the preceding chapter boss and verify that its Next button crosses the chapter boundary.
  await page.locator('[data-id="py-scope-08-toolkit"]').click();
  await page.getByRole('button',{name:'Back to editing',exact:true}).waitFor();
  await page.getByRole('button',{name:'Next mission →'}).click();
  await page.getByRole('heading',{name:'Quote the whole job',exact:true}).waitFor();
  assert.match(await page.locator('#total-progress').textContent(), /Chapter 4 · Numbers and comparisons/);
  assert.equal(await page.locator('#xp').textContent(),'370 XP');
  assert.equal(await page.locator('[data-id="py-num-02-grouping"]').isDisabled(),true);
  const editorText = () => page.getByRole('textbox',{name:'Python code',exact:true}).innerText();
  await mkdir('qa',{recursive:true});
  assert.equal(await page.locator('#offline-hints').evaluate(e=>e.open),false);
  assert.equal(await page.locator('#hints details').count(),3);
  assert.equal(await page.locator('#hints details[open]').count(),0);
  assert.match(await editorText(), /pass/);
  await page.locator('#offline-hints > summary').click();
  await page.locator('#hints details summary').first().click();
  await page.locator('#hints details p').first().waitFor();
  await page.locator('#offline-hints > summary').click();
  await page.screenshot({path:'qa/numbers-start.png',fullPage:true});
  const chapter=JSON.parse(await readFile('content/python-numbers.json','utf8'));
  const editor=page.getByRole('textbox',{name:'Python code',exact:true});
  const write=async code=>{
    const save=page.waitForResponse(r=>r.url().endsWith('/api/save') && r.ok() && r.request().postDataJSON()?.code===code);
    await editor.fill(code); await save;
  };
  const action=async(name,pattern)=>{
    await page.getByRole('button',{name,exact:true}).click();
    await page.locator('#feedback').filter({hasText:pattern}).waitFor({timeout:45000});
  };
  for (const [index,mission] of chapter.missions.entries()) {
    assert.equal(await page.locator('#lesson-title').textContent(),mission.title);
    assert.equal(await page.locator('#compare').isVisible(),false);
    if(index===0){
      await action('Submit','checks passed. Nothing lost');
      assert.equal(await page.locator('#compare').isVisible(),false);
    }
    await write(mission.reference.code);
    await action('Run','Run finished');
    await action('Test',/All \d+ example checks passed/);
    assert.equal(await page.locator('#compare').isVisible(),false);
    await action('Submit',index===11?'Chapter complete!':'Mission complete!');
    await page.getByRole('button',{name:'Back to editing',exact:true}).waitFor();
    const comparison=await (await page.request.get(`${base}/api/reference/${mission.id}`)).json();
    assert.equal(comparison.submitted_code,mission.reference.code);
    if(index===0){
      await page.reload();
      await page.getByRole('button',{name:'Back to editing',exact:true}).waitFor();
      assert.equal(await page.locator('#xp').textContent(),'380 XP');
    }
    if(index<11)await page.getByRole('button',{name:'Next mission →'}).click();
  }
  assert.equal(await page.locator('#xp').textContent(),'510 XP');
  assert.match(await page.locator('#total-progress').textContent(),/Number Navigator/);
  assert.equal(await page.locator('#chapter-count').textContent(),'12 of 12 missions complete');
  const exported=await (await page.request.get(`${base}/api/export`)).json();
  assert.equal(Object.keys(exported.completions).length,43);
  await page.screenshot({path:'qa/numbers-complete.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'Code & results',exact:true}).click();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);
  console.log('Passed: scope-to-numbers navigation, 12 missions Run/Test/Submit, failure gating, reference comparisons, persistence, 140 new XP, badge, and narrow layout.');
} catch(error) { console.log(await page?.locator("body").innerText()); await page?.screenshot({path:"qa/numbers-failure.png"}); throw error; } finally {await browser?.close();server.kill();}
