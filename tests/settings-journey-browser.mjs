import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const script = [
  'import sys',
  'from pathlib import Path',
  'from server import make_server, connect, catalog, timestamp',
  'server = make_server(port=0, database=Path(sys.argv[1]))',
  "if sys.argv[2] == 'seed':",
  "    course = catalog()",
  "    chapter = next(c for c in course['chapters'] if c['badge'] == 'Console builder')",
  "    with connect(server.database) as db:",
  "        db.executemany('INSERT INTO completions VALUES(?,?,?,?)',",
  "            [(m['id'], 'print(1)', timestamp(), m['version'])",
  "             for m in course['missions'] if m['id'] in chapter['mission_ids']])",
  'print(server.server_port, flush=True)',
  'server.serve_forever()',
].join('\n');

const folder = await mkdtemp(join(tmpdir(), 'syntaxia-settings-'));
const servers = [];
async function openServer(mode) {
  const server = spawn('python', ['-u', '-c', script, join(folder, 'test.sqlite3'), mode], {
    stdio: ['ignore', 'pipe', 'inherit'],
  });
  servers.push(server);
  const port = await new Promise((resolve, reject) => {
    server.stdout.once('data', data => resolve(Number(String(data).trim())));
    server.once('error', reject);
    server.once('exit', code => reject(Error('Server exited with code ' + code)));
  });
  return 'http://127.0.0.1:' + port;
}

let browser;
try {
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const root = page.locator('html');
  const settings = page.locator('#open-settings');
  const theme = page.getByLabel('Color palette');
  const reading = page.getByLabel('Reading text size');
  const editor = page.getByLabel('Editor text size');
  const saved = page.getByRole('status').filter({ hasText: 'Appearance saved.' });
  const original = await openServer('seed');
  await page.goto(original);
  await settings.click();
  assert.equal(await theme.inputValue(), 'amethyst');
  await theme.selectOption('forest');
  await reading.selectOption('20');
  await editor.selectOption('19');
  await page.getByText('Individual colors', { exact: true }).click();
  await page.getByLabel('Interface accent', { exact: true }).fill('#ffaaff');
  await page.getByLabel('Inline Python', { exact: true }).fill('#eeaa11');
  await page.getByLabel('Editor keywords', { exact: true }).fill('#ff00aa');
  await page.getByRole('button', { name: 'Save appearance' }).click();
  await saved.waitFor();
  assert.equal(await root.getAttribute('data-theme'), 'forest');
  assert.equal(await root.evaluate(e => getComputedStyle(e).getPropertyValue('--accent').trim()), '#ffaaff');
  assert.equal(await page.locator('code.inline-code').first().evaluate(e => getComputedStyle(e).color), 'rgb(238, 170, 17)');
  const keyword = page.locator('#editor .cm-line span').filter({ hasText: /^def$/ }).first();
  assert.equal(await keyword.evaluate(e => getComputedStyle(e).color), 'rgb(255, 0, 170)');
  assert.equal(await page.locator('#lesson-body').evaluate(e => getComputedStyle(e).fontSize), '20px');
  assert.equal(await page.locator('#editor .cm-editor').evaluate(e => getComputedStyle(e).fontSize), '19px');
  await page.getByRole('button', { name: 'Close', exact: true }).click();

  const restarted = await openServer('reopen');
  assert.notEqual(restarted, original);
  await page.goto(restarted);
  await settings.click();
  assert.equal(await theme.inputValue(), 'forest');
  assert.equal(await reading.inputValue(), '20');
  assert.equal(await editor.inputValue(), '19');
  await page.getByText('Individual colors', { exact: true }).click();
  assert.equal(await page.getByLabel('Editor keywords', { exact: true }).inputValue(), '#ff00aa');
  await page.getByRole('button', { name: 'Use default for editor keywords' }).click();
  await page.getByRole('button', { name: 'Save appearance' }).click();
  await saved.waitFor();
  assert.equal(await keyword.evaluate(e => getComputedStyle(e).color), 'rgb(198, 120, 221)');
  assert.equal(await root.evaluate(e => getComputedStyle(e).getPropertyValue('--accent').trim()), '#ffaaff');
  await page.locator('[data-settings-pane=tutor]').click();
  await page.getByLabel('API key', { exact: true }).waitFor();
  await page.locator('[data-settings-pane=appearance]').click();
  await page.getByRole('button', { name: 'Restore defaults' }).click();
  await saved.waitFor();
  assert.equal(await root.getAttribute('data-theme'), 'amethyst');
  assert.equal(await root.evaluate(e => getComputedStyle(e).getPropertyValue('--accent').trim()), '#c39af2');
  await page.screenshot({ path: 'qa/appearance-settings.png' });
  await page.getByRole('button', { name: 'Close', exact: true }).click();

  await page.locator('#open-journey').click();
  const journey = page.locator('#journey');
  await journey.getByRole('heading', { name: 'Journey', exact: true }).waitFor();
  assert.equal(await page.locator('.workspace').isVisible(), false);
  assert.equal(await journey.locator('.journey-summary dd').nth(1).textContent(), '90');
  assert.equal(await journey.locator('.journey-earned').count(), 1);
  assert.match(await journey.locator('.journey-badge').filter({ hasText: 'Console builder' }).textContent(), /Earned/);
  assert.equal(await journey.getByRole('button', { name: 'Build your session planner' }).count(), 2);
  await page.waitForFunction(() => {
    const badges = [...document.querySelectorAll('.journey-badge-art')];
    return badges.length === 10 && badges.every(badge => badge.complete && badge.naturalWidth === 160);
  });
  assert.equal(await journey.locator('.journey-badge.earned img').count(), 1);
  await page.screenshot({ path: 'qa/journey.png' });
  await page.setViewportSize({ width: 390, height: 850 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  const next = journey.locator('.journey-next button');
  const title = await next.textContent();
  await next.click();
  await journey.waitFor({ state: 'hidden' });
  assert.equal(await page.locator('#lesson-title').textContent(), title);
  let installs = 0;
  await page.route('**/api/lessons/check', route => route.fulfill({
    json: { supported: true, available: route.request().postDataJSON().manual },
  }));
  await page.route('**/api/lessons/install', route => {
    installs++;
    return route.fulfill({ json: { supported: true, installed: true } });
  });
  await page.reload();
  await settings.click();
  await page.getByRole('button', { name: 'Lessons', exact: true }).click();
  await page.locator('#lesson-update-status').filter({ hasText: 'Your lessons are up to date' }).waitFor();
  await page.getByRole('button', { name: 'Check for new lessons', exact: true }).click();
  await page.locator('#lesson-update-status').filter({ hasText: 'A lesson update is available' }).waitFor();
  assert.equal(installs, 0);
  await page.getByRole('button', { name: 'Install lesson update', exact: true }).click();
  await page.locator('#tutor-settings').waitFor({ state: 'hidden' });
  assert.equal(installs, 1);
  assert.deepEqual(errors, []);
  console.log('Settings and Journey passed with saved progress and a new server address.');
} finally {
  await browser?.close();
  await Promise.all(servers.map(server => {
    if (server.exitCode !== null || server.signalCode !== null) return;
    return new Promise(resolve => { server.once('exit', resolve); server.kill(); });
  }));
  await rm(folder, { recursive: true, force: true });
}

