import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
const script = [
'import tempfile',
'from pathlib import Path',
'import tutor',
'from server import make_server, connect',
"tmp=tempfile.TemporaryDirectory()",
"def fake(settings, key, payload):",
"    if payload['input'][-1]['content'] == 'simulate outage': raise tutor.TutorError('Test connection unavailable. Try again.')",
"    return ('What value comes back from the function? Try following that value into the next line.\\n\\n<img src=x onerror=alert(1)>', {'total_tokens': 42})",
'tutor.call_api=fake',
"srv=make_server(port=0,database=Path(tmp.name)/'qa.sqlite3')",
'with connect(srv.database) as db:',
"    db.execute('INSERT INTO completions VALUES(?,?,?,?)', ('py-01-message', 'print(\"saved passing code\")', 'today', 1))",
'print(srv.server_port,flush=True)',
'srv.serve_forever()'
].join('\n');
const server = spawn('python', ['-u','-c',script], {env:{...process.env,OPENAI_API_KEY:''},stdio:['ignore','pipe','pipe']});
const port = await new Promise((resolve,reject)=>{server.stdout.once('data',data=>resolve(Number(String(data).trim())));server.once('exit',code=>reject(Error('Server exit '+code)));server.once('error',reject);});
const browser = await chromium.launch({ channel:'msedge',headless:true });
try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  let requests=0;page.on('request',r=>{if(r.url().endsWith('/api/tutor/chat'))requests++;});
  await page.goto('http://127.0.0.1:'+port+'/?desktop=1&mission=py-01-message');
  await page.locator('#tutor-status').filter({hasText:'Add your API key'}).waitFor();
  assert.equal(requests,0);
  assert.equal(await page.locator('#tutor-send').isDisabled(),true);
  await page.locator('#tutor-settings-open').click();
  await page.locator('#tutor-key').fill('fake-browser-test-key');
  await page.locator('#tutor-reasoning').selectOption('low');
  await page.locator('#tutor-test').click();
  await page.locator('#tutor-settings-status').filter({hasText:'Connected.'}).waitFor();
  assert.equal(await page.locator('#tutor-key').inputValue(),'');
  await page.locator('#tutor-settings-close').click();
  await page.locator('#explain-differences').click();
  assert.equal(requests,0);
  await page.locator('#tutor-send').click();
  await page.locator('#tutor-status').filter({hasText:'42 tokens'}).waitFor();
  assert.equal(await page.locator('#tutor-messages .tutor-message').count(),2);
  assert.equal(await page.locator('#tutor-messages img').count(),0);
  assert.match(await page.locator('#tutor-messages').textContent(),/<img/);
  await page.reload();
  await page.locator('#tutor-messages .tutor-message').first().waitFor();
  assert.equal(await page.locator('#tutor-messages .tutor-message').count(),2);
  await page.getByRole('button',{name:/02 Count the cost/}).click();
  await page.locator('#tutor-status').filter({hasText:'replies on request'}).waitFor();
  assert.equal(await page.locator('#tutor-messages .tutor-message').count(),0);
  await page.locator('#tutor-question').fill('simulate outage');
  await page.locator('#tutor-send').click();
  await page.locator('#tutor-status').filter({hasText:'Test connection unavailable'}).waitFor();
  assert.equal(await page.locator('#tutor-question').inputValue(),'simulate outage');
  assert.equal(await page.locator('#tutor-messages .tutor-message').count(),0);
  await page.locator('#tutor-hint').click();
  await page.locator('#tutor-status').filter({hasText:'42 tokens'}).waitFor();
  await page.locator('#tutor').scrollIntoViewIfNeeded();
  await mkdir('qa',{recursive:true});
  await page.screenshot({path:'qa/tutor-desktop.png'});
  assert.equal(await page.locator('#tutor-messages').evaluate(e=>getComputedStyle(e).overflowY),'auto');
  await page.locator('#tutor-settings-open').click();
  await page.screenshot({path:'qa/tutor-settings.png'});
  await page.locator('#tutor-settings-close').click();
  await page.setViewportSize({width:600,height:900});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);
  console.log('Tutor UI passed: settings, encryption input clearing, no automatic calls, comparison chat, persisted/isolated histories, retry, safe rendering, scrolling and narrow layout. No live API used.');
} finally { await browser.close(); server.kill(); }

