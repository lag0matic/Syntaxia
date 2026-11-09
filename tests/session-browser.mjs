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
        if m['chapter'] in ('python-foundations', 'python-functions', 'python-scope', 'python-numbers'):
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
  await page.getByRole('heading',{name:'Describe a completed session',exact:true}).waitFor();
  // Revisit the preceding chapter boss and verify that its Next button crosses the chapter boundary.
  await page.locator('[data-id="py-num-12-boss"]').click();
  await page.getByRole('button',{name:'Back to editing',exact:true}).waitFor();
  await page.getByRole('button',{name:'Next mission →'}).click();
  await page.getByRole('heading',{name:'Describe a completed session',exact:true}).waitFor();
  assert.match(await page.locator('#total-progress').textContent(), /Chapter 5 · Project: session summary tool/);
  assert.equal(await page.locator('#xp').textContent(),'510 XP');
  assert.equal(await page.locator('[data-id="py-session-02-collect"]').isDisabled(),true);
  const editorText = () => page.getByRole('textbox',{name:'Python code',exact:true}).innerText();
  await mkdir('qa',{recursive:true});
  assert.equal(await page.locator('#up-next-mission').textContent(),'Describe a completed session');
  assert.equal(await page.locator('#offline-hints').evaluate(e=>e.open),false);
  await page.getByRole('textbox',{name:'Python code',exact:true}).fill('# draft survives reference reading');
  await page.locator('#open-grimoire').click();
  await page.locator('#grimoire-index button').first().waitFor();
  await page.locator('#grimoire-search').fill('modulo');
  await page.locator('#grimoire-index button', {hasText:'Remainder and unit splitting'}).click();
  assert.equal(await page.locator('#grimoire-article h3').textContent(),'Remainder and unit splitting');
  await page.locator('#grimoire-article').getByRole('button',{name:'True and floor division',exact:true}).click();
  assert.equal(await page.locator('#grimoire-article h3').textContent(),'True and floor division');
  await page.locator('#grimoire-back').click();
  assert.equal(await page.locator('#grimoire-article h3').textContent(),'Remainder and unit splitting');
  await page.locator('#grimoire-search').fill('no-such-concept-xyz');
  assert.match(await page.locator('#grimoire-status').textContent(),/No matching/);
  await page.locator('#grimoire-search').fill('');
  await page.screenshot({path:'qa/grimoire-desktop.png'});
  await page.locator('#grimoire-close').click();
  assert.match(await page.getByRole('textbox',{name:'Python code',exact:true}).innerText(),/draft survives/);
  const firstMission=JSON.parse(await readFile('content/python-session-project.json','utf8')).missions[0];
  await page.getByRole('textbox',{name:'Python code',exact:true}).fill(firstMission.starter);
  await page.locator('.lesson').evaluate(e=>e.scrollTop=0);
  await page.screenshot({path:'qa/session-start.png',fullPage:true});
  const chapter=JSON.parse(await readFile('content/python-session-project.json','utf8'));
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
    await action('Submit',index===2?'Chapter complete!':'Mission complete!');
    await page.getByRole('button',{name:'Back to editing',exact:true}).waitFor();
    const comparison=await (await page.request.get(`${base}/api/reference/${mission.id}`)).json();
    assert.equal(comparison.submitted_code,mission.reference.code);
    if(index===0){
      await page.reload();
      await page.getByRole('button',{name:'Back to editing',exact:true}).waitFor();
      assert.equal(await page.locator('#xp').textContent(),'520 XP');
    }
    if(index<2)await page.getByRole('button',{name:'Next mission →'}).click();
  }
  assert.equal(await page.locator('#xp').textContent(),'560 XP');
  assert.match(await page.locator('#total-progress').textContent(),/Session Scribe/);
  assert.equal(await page.locator('#chapter-count').textContent(),'3 of 3 missions complete');
  const pendingCourse = await (await page.request.get(`${base}/api/bootstrap`)).json();
  const nextPending = pendingCourse.course.missions.find(m => !m.orientation && !pendingCourse.state.completions[m.id] && m.prerequisites.every(id => pendingCourse.state.completions[id]));
  if (nextPending) assert.equal(await page.locator('#up-next-mission').textContent(), nextPending.title);
  else assert.match(await page.locator('.course-note').textContent(), /All caught up/);
  const exported=await (await page.request.get(`${base}/api/export`)).json();
  assert.equal(Object.keys(exported.completions).length,46);
  await page.screenshot({path:'qa/session-complete.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'Code & results',exact:true}).click();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.locator('#open-grimoire').click();
  await page.locator('#grimoire-index button').first().waitFor();
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await page.screenshot({path:'qa/grimoire-mobile.png'});
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#grimoire').isVisible(),false);
  assert.deepEqual(errors,[]);
  console.log('Passed: numbers-to-session navigation, grimoire and next-mission states, 3 missions Run/Test/Submit, failure gating, reference comparisons, persistence, 50 new XP, badge, and narrow layout.');
} catch(error) { console.log(await page?.locator("body").innerText()); await page?.screenshot({path:"qa/session-failure.png"}); throw error; } finally {await browser?.close();server.kill();}
