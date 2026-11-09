import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';

const server = spawn('python', ['-u', '-c', "import tempfile; from pathlib import Path; from server import make_server; tmp=tempfile.TemporaryDirectory(); srv=make_server(port=0,database=Path(tmp.name)/'qa.sqlite3'); print(srv.server_port,flush=True); srv.serve_forever()"], { stdio: ['ignore', 'pipe', 'pipe'] });
let browser;
try {
  const port = await new Promise((resolve, reject) => { server.stdout.once('data', data => resolve(Number(String(data).trim()))); server.once('error', reject); });
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  await page.goto(`http://127.0.0.1:${port}`);
  const editor = page.getByRole('textbox', { name: 'Python code', exact: true });
  await editor.fill('session_minutes = 25\nsession_min');
  await editor.press('Control+End');
  await editor.press('Control+Space');
  await page.getByRole('option').filter({ hasText: 'session_minutes' }).waitFor();
  // CodeMirror intentionally ignores acceptance for 75ms after the menu opens.
  await page.waitForTimeout(100);
  await editor.press('Tab');
  assert.match(await editor.innerText(), /session_minutes = 25\nsession_minutes$/);
  assert.equal(await page.getByRole('listbox').count(), 0);
  await editor.press('Enter');
  await editor.press('Tab');
  assert.match(await editor.innerText(), /\n {4}$/);
  await editor.press('Shift+Tab');
  assert.doesNotMatch(await editor.innerText(), /\n {4}$/);
  console.log('Passed: Tab accepts variable completion, Tab indents four spaces without suggestions, Shift+Tab unindents. Real progress untouched.');
} finally {
  await browser?.close(); server.kill();
}
