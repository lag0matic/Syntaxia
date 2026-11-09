import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { readFile, mkdir } from 'node:fs/promises';
import assert from 'node:assert/strict';

const server = spawn('python', ['-u', '-c', "import tempfile; from pathlib import Path; from server import make_server; tmp=tempfile.TemporaryDirectory(); srv=make_server(port=0,database=Path(tmp.name)/'qa.sqlite3'); print(srv.server_port,flush=True); srv.serve_forever()"], { stdio: ['ignore', 'pipe', 'pipe'] });
const port = await new Promise((resolve, reject) => { server.stdout.once('data', data => resolve(Number(String(data).trim()))); server.once('error', reject); server.once('exit', code => reject(new Error(`Test server exited ${code}`))); });
const base = `http://127.0.0.1:${port}`;
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const errors = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(base);
  await page.getByRole('heading',{name:'Your first Python program',exact:true}).waitFor();
  await page.locator('[data-id="py-01-message"]').click();
  const editor = page.getByRole('textbox', { name: 'Python code', exact: true });
  await editor.waitFor();
  await mkdir('qa', { recursive: true });
  await page.screenshot({ path: 'qa/classroom-desktop.png', fullPage: true });
  const write = async code => {
    const saved = page.waitForResponse(response => response.url().endsWith('/api/save') && response.request().postDataJSON()?.code === code && response.ok());
    await editor.fill(code);
    await saved;
  };
  const action = async (name, match) => { await page.getByRole('button', { name, exact: true }).click(); await page.locator('#feedback').filter({ hasText: match }).waitFor({ timeout: 45000 }); };
  await write('print("Hello from Python")');
  await action('Run', 'Run finished');
  assert.equal((await page.locator('#output').textContent()).trim(), 'Hello from Python', JSON.stringify({ editor: await editor.innerText(), saved: (await (await page.request.get(`${base}/api/bootstrap`)).json()).state.drafts }));
  await page.reload();
  await page.locator('#runtime-status').filter({ hasText: 'Python ready' }).waitFor();
  assert.match(await editor.innerText(), /Hello from Python/);
  await action('Test', '0 of 1 checks passed');
  await write('while True:\n    pass');
  await action('Run', 'Stopped after 5 seconds');
  await page.getByRole('button', { name: 'Run', exact: true }).click();
  await page.getByRole('button', { name: 'Stop', exact: true }).click();
  assert.match(await page.locator('#feedback').textContent(), /Stopped. Your code is unchanged/);
  await write('print("reset backup")');
  await page.getByRole('button', { name: 'Reset', exact: true }).click();
  await page.getByRole('button', { name: 'Save backup and reset' }).click();
  await page.locator('#feedback').filter({ hasText: 'Starter restored' }).waitFor();
  await action('Restore reset backup', 'Your last reset backup is restored');
  assert.match(await editor.innerText(), /reset backup/);
  await page.getByLabel('Free practice').check();
  assert.equal(await page.getByRole('button', { name: 'Submit', exact: true }).isDisabled(), true);
  await page.getByLabel('Free practice').uncheck();
  const solutions = JSON.parse(await readFile('tests/solutions.json', 'utf8'));
  const { course } = await (await page.request.get(`${base}/api/bootstrap`)).json();
  const foundations = course.chapters.find(chapter => chapter.id === 'python-foundations');
  for (const id of Object.keys(solutions)) if (!foundations.mission_ids.includes(id)) delete solutions[id];
  solutions['py-05-loops'] = 'sessions = int(input())\nnumber = 1\nwhile number <= sessions:\n    print(f"Session {number}")\n    number += 1\nprint("Ready.")\n';
  assert.equal(await page.locator('#compare').isVisible(), false);
  let index = 0;
  for (const [id, source] of Object.entries(solutions)) {
    await page.locator('.mission.active[data-id="' + id + '"]').waitFor();
    await write(source);
    await action('Test', /All \d+ example checks passed/);
    assert.equal(await page.locator('#comparison').isVisible(), false);
    assert.equal((await page.request.get(`${base}/api/bootstrap`)).ok(), true);
    await action('Submit', index === 6 ? 'Chapter complete!' : 'Mission complete!');
    await page.getByRole('button', { name: 'Back to editing', exact: true }).waitFor();
    assert.equal(await page.locator('#comparison').isVisible(), true);
    assert.equal(await editor.isVisible(), false);
    const passing = page.locator('[aria-label="Your passing code"]');
    assert.equal(await passing.getAttribute('contenteditable'), 'false');
    assert.match(await passing.innerText(), new RegExp(source.split('\n')[0].replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    if (index === 4) {
      assert.match(await passing.innerText(), /while number <= sessions/);
      assert.match(await page.locator('[aria-label="Reference solution"]').innerText(), /range/);
      await page.screenshot({ path: 'qa/solution-comparison.png', fullPage: true });
    }
    if (index === 0) {
      await page.getByRole('button', { name: 'Back to editing', exact: true }).click();
      await action('Submit', 'XP is awarded only once');
      await page.getByRole('button', { name: 'Back to editing', exact: true }).waitFor();
      assert.equal(await page.locator('#xp').textContent(), '10 XP');
    }
    if (index < 6) await page.getByRole('button', { name: 'Next mission →' }).click();
    index++;
  }
  assert.equal(await page.locator('#xp').textContent(), '90 XP');
  await page.reload(); await page.getByRole('button', { name: 'Back to editing', exact: true }).waitFor();
  assert.equal(await page.locator('#xp').textContent(), '90 XP');
  assert.match(await page.locator('#total-progress').textContent(), /Console builder/);
  const exported = await (await page.request.get(`${base}/api/export`)).json();
  assert.equal(Object.keys(exported.completions).length, 7);
  assert.ok(exported.snapshots.length >= 9);
  await page.screenshot({ path: 'qa/chapter-complete.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'qa/classroom-mobile-lesson.png', fullPage: true });
  await page.getByRole('button', { name: 'Code & results', exact: true }).click();
  await page.screenshot({ path: 'qa/classroom-mobile-code.png', fullPage: true });
  assert.equal(await page.locator('#comparison').isVisible(), true);
  await page.getByRole('button', { name: 'Back to editing', exact: true }).click();
  assert.equal(await editor.isVisible(), true);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.evaluate(() => { document.documentElement.style.fontSize = '32px'; });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
  await page.evaluate(() => { document.documentElement.style.fontSize = ''; });
  const otherPage = await context.newPage();
  await otherPage.goto(base); await otherPage.getByRole('button', { name: 'Back to editing', exact: true }).click();
  await otherPage.getByRole('textbox', { name: 'Python code', exact: true }).waitFor();
  await write('# changed in first tab');
  await page.locator('#save-status').filter({ hasText: 'Saved on this host' }).waitFor();
  await otherPage.getByRole('textbox', { name: 'Python code', exact: true }).fill('# conflicting change');
  await otherPage.locator('#feedback').filter({ hasText: 'A different tab changed' }).waitFor();
  assert.equal(await otherPage.getByRole('button', { name: 'Submit', exact: true }).isDisabled(), true);
  assert.deepEqual(errors, []);
  console.log('Browser checks passed: offline assets, Python Run/Test/Submit, seven missions, autosave/reload, stop/timeout, reset/restore, practice, XP, export, mobile layout.');
} finally {
  await browser.close(); server.kill();
}
