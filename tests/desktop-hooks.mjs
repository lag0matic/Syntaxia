import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';

const server = spawn('python', ['-u', '-c', "import tempfile; from pathlib import Path; from server import make_server; tmp=tempfile.TemporaryDirectory(); srv=make_server(port=0,database=Path(tmp.name)/'qa.sqlite3'); print(srv.server_port,flush=True); srv.serve_forever()"], { stdio: ['ignore', 'pipe', 'pipe'] });
const port = await new Promise((resolve, reject) => {
  server.stdout.once('data', data => resolve(Number(String(data).trim())));
  server.once('error', reject);
  server.once('exit', code => reject(new Error(`Test server exited ${code}`)));
});
const browser = await chromium.launch({ channel: 'msedge', headless: true });
try {
  const page = await browser.newPage();
  const url = `http://127.0.0.1:${port}/?desktop=1&mission=py-01-message`;
  await page.goto(url);
  const editor = page.getByRole('textbox', { name: 'Python code', exact: true });
  await editor.fill('# immediate desktop close: save this draft');
  const result = await page.evaluate(() => window.workshopDesktop.prepareLeave());
  assert.deepEqual(result, { ok: true, mission: 'py-01-message' });
  await page.reload();
  await editor.waitFor();
  assert.match(await editor.innerText(), /save this draft/);
  assert.match(await page.locator('#runtime-status').innerText(), /runs stay in the app/);
  // A stalled tutor request must not prevent a safe application close.
  await page.route('**/api/tutor/settings', route => route.fulfill({json:{has_key:true,model:'test',endpoint:'https://example.com/v1',reasoning:'low',max_output_tokens:2500}}));
  await page.reload();
  await page.locator('#tutor-send').waitFor();
  await page.locator('#tutor-question').fill('one hint please');
  let releaseTutor;
  const held = new Promise(resolve => { releaseTutor = resolve; });
  let started;
  const requested = new Promise(resolve => { started = resolve; });
  await page.route('**/api/tutor/chat', async route => { started(); await held; await route.abort(); });
  await page.locator('#tutor-send').click();
  await requested;
  await editor.fill('# close while tutor is pending');
  await page.locator('#save-status').filter({ hasText: 'Unsaved changes' }).waitFor();
  const reloadBlocked = await page.evaluate(() => window.workshopDesktop.prepareLeave());
  assert.equal(reloadBlocked.ok, false);
  assert.match(reloadBlocked.message, /tutor/);
  const closing = await page.evaluate(() => window.workshopDesktop.prepareLeave({closing:true}));
  assert.deepEqual(closing, {ok:true, mission:'py-01-message'});
  releaseTutor();
  await page.reload();
  await page.locator('#runtime-status').filter({ hasText: 'runs stay in the app' }).waitFor();
  assert.match(await editor.innerText(), /close while tutor is pending/);
  await page.route('**/api/save', route => route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ error: 'Simulated failed save' }) }));
  await editor.fill('# unsaved edits must block close');
  const blocked = await page.evaluate(() => window.workshopDesktop.prepareLeave());
  assert.equal(blocked.ok, false);
  assert.match(blocked.message, /Simulated failed save/);
  console.log('Desktop hooks passed: immediate close saves, reopen restores, pending tutor does not block closing, reload remains guarded, failed save blocks close.');
} finally {
  await browser.close();
  server.kill();
}
