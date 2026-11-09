import { createLessonUpdates } from './lesson-updates.js';
import { createJourney } from './journey.js';
import { appendInlineCode } from './inline-code.js';
import { createGrimoire } from './grimoire.js';
import { createTutor } from './tutor-chat.js';
import { EditorView, basicSetup } from 'codemirror';
import { EditorState, Compartment, Prec } from '@codemirror/state';
import { acceptCompletion } from '@codemirror/autocomplete';
import { keymap } from '@codemirror/view';
import { indentWithTab } from '@codemirror/commands';
import { python } from '@codemirror/lang-python';
import { HighlightStyle, indentUnit, syntaxHighlighting } from '@codemirror/language';
import { color, oneDarkHighlightStyle, oneDarkTheme } from '@codemirror/theme-one-dark';
import { tags } from '@lezer/highlight';

const editorTheme = [oneDarkTheme, syntaxHighlighting(HighlightStyle.define([
  ...oneDarkHighlightStyle.specs,
  { tag: tags.keyword, color: 'var(--custom-keyword, ' + color.violet + ')' },
  { tag: tags.string, color: 'var(--custom-string, ' + color.sage + ')' },
  { tag: tags.number, color: 'var(--custom-number, ' + color.chalky + ')' },
  { tag: tags.comment, color: 'var(--custom-comment, ' + color.stone + ')' },
]))];

const $ = selector => document.querySelector(selector);
let course, state, token, current, editor, busy = false, loadingCode = false;
let dirty = false, saveError = false, saveTimer, worker, runTimer, loadTimer, pending, generation = 0;
let saveQueue = Promise.resolve();
let comparisonViews = [], comparisonRequest = 0;
const editable = new Compartment();
const runners = { python: '/worker.js' };
let lessonUpdates;
const tutor = createTutor({
  settingsPanel(panel, openSettings) {
    lessonUpdates = createLessonUpdates(panel, api, openSettings, async () => {
      if (busy) throw new Error('Stop the running code before updating lessons.');
      await saveDraft();
    });
  },
  api, getContext: () => ({ mission: current?.id, code: editor ? getCode() : '',
    results: [$('#feedback').textContent, $('#output').textContent, $('#test-results').textContent].join('\n').slice(0,10000) }),
});
createGrimoire({ api, getState: () => state, openLesson: id => selectMission(id) });
const journey = createJourney({
  getCourse: () => course,
  getCompletions: () => state.completions,
  openLesson: id => selectMission(id).catch(showSaveError),
  nextMission: nextPendingMission,
});
$('#open-settings').addEventListener('click', () => tutor.openSettings());

const readyMessage = new URLSearchParams(location.search).has('desktop') ? 'Python ready · runs stay in the app' : 'Python ready · runs stay in the browser';
function currentChapter() { return course.chapters.find(chapter => chapter.id === current.chapter); }

function closeComparison() {
  comparisonRequest++;
  comparisonViews.forEach(view => view.destroy()); comparisonViews = [];
  $('#comparison').replaceChildren(); $('#comparison').hidden = true;
  document.body.classList.remove('comparing');
  $('#compare').textContent = 'Compare solutions';
}
async function showComparison() {
  const id = current.id;
  const request = ++comparisonRequest;
  try {
    const data = await api(`/api/reference/${encodeURIComponent(id)}`);
    if (current.id !== id || request !== comparisonRequest) return;
    if (!data.available) { feedback('A reference solution has not been added to this mission yet.'); return; }
    closeComparison();
    const grid = element('div', undefined, 'comparison-grid');
    for (const [title, code] of [['Your passing code', data.submitted_code], ['Reference solution', data.reference.code]]) {
      const pane = element('section', undefined, 'comparison-pane');
      pane.append(element('h2', title));
      const container = element('div', undefined, 'comparison-code'); pane.append(container); grid.append(pane);
      comparisonViews.push(new EditorView({ doc: code, parent: container, extensions: [basicSetup, python(), editorTheme, EditorState.readOnly.of(true), EditorView.editable.of(false), EditorView.lineWrapping, EditorView.contentAttributes.of({ 'aria-label': title, tabindex: '0' })] }));
    }
    const notes = element('section', undefined, 'comparison-notes');
    notes.append(element('h2', 'Why this approach?'));
    data.reference.notes.forEach(note => notes.append(prose('p', note)));
    notes.append(element('p', 'One clear solution, not the only correct answer. Compare the reasoning, then return to your editor to experiment.', 'comparison-caption'));
    $('#comparison').append(element('p', 'Comparing your most recent passing submission. Your working draft is kept separately.', 'comparison-caption'), grid, notes);
    const discuss = element('button', 'Explain these differences');
    discuss.id = 'explain-differences';
    discuss.addEventListener('click', () => tutor.discuss());
    $('#comparison').append(discuss);
    $('#comparison').hidden = false; document.body.classList.add('comparing');
    $('#compare').textContent = 'Back to editing';
    $('.coding').scrollTop = 0;
  } catch (error) {
    if (current.id === id && request === comparisonRequest) feedback(`Your work is saved, but the comparison could not load: ${error.message}`, 'error');
  }
}

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function prose(tag, text, className) {
  return appendInlineCode(element(tag, undefined, className), text);
}
function feedback(message, kind = '') {
  $('#feedback').textContent = message;
  $('#feedback').className = kind;
}
async function api(path, body) {
  const headers = { 'Content-Type': 'application/json', ...(token ? { 'X-Workshop-Token': token } : {}) };
  const response = await fetch(path, body ? { method: 'POST', headers, body: JSON.stringify(body) } : { headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
  return data;
}
function remember(key, value) { try { localStorage.setItem(key, value); } catch { /* Host storage remains authoritative. */ } }
function recall(key) { try { return localStorage.getItem(key); } catch { return null; } }
function unlocked(mission) { return mission.prerequisites.every(id => state.completions[id]); }
function getCode() { return editor.state.doc.toString(); }
function setCode(code) {
  loadingCode = true;
  editor.setState(EditorState.create({ doc: code, extensions: editorExtensions() }));
  loadingCode = false;
}
function editorExtensions() {
  return [basicSetup, python(), editorTheme, indentUnit.of('    '), keymap.of([indentWithTab]),
    Prec.highest(keymap.of([{ key: 'Tab', run: acceptCompletion }])),
    editable.of(EditorView.editable.of(!busy)),
    EditorView.contentAttributes.of({ 'aria-label': 'Python code', spellcheck: 'false' }),
    EditorView.theme({ '&': { backgroundColor: '#111113' }, '.cm-gutters': { backgroundColor: '#19191c' }, '.cm-scroller': { fontFamily: "'Cascadia Code', Consolas, monospace" } }),
    EditorView.updateListener.of(update => {
      if (!update.docChanged || loadingCode || !current) return;
      dirty = true;
      $('#save-status').textContent = 'Unsaved changes';
      clearTimeout(saveTimer);
      saveTimer = setTimeout(() => saveDraft().catch(showSaveError), 600);
    })];
}
function showSaveError(error) {
  saveError = true;
  $('#save-status').textContent = 'Not saved — download your code';
  feedback(error.message, 'error');
  updateControls();
}
function saveDraft() {
  clearTimeout(saveTimer);
  if (!dirty) return saveQueue;
  const mission = current.id;
  const code = getCode();
  $('#save-status').textContent = 'Saving…';
  const job = saveQueue.then(async () => {
    if (saveError) throw new Error('Saving is paused. Download your code, then reload the classroom.');
    const result = await api('/api/save', { mission, code, revision: state.drafts[mission]?.revision || 0 });
    state = result.state;
    if (current.id === mission && getCode() === code) {
      dirty = false;
      $('#save-status').textContent = 'Saved on this host';
    }
    return result;
  });
  saveQueue = job.catch(() => {});
  return job;
}
function updateControls() {
  for (const id of ['run', 'test', 'submit', 'reset', 'restore']) {
    $(`#${id}`).disabled = busy || !current || saveError || (id === 'submit' && $('#practice').checked);
  }
  $('#stop').disabled = !busy;
  $('#practice').disabled = busy;
  $('#stdin').disabled = busy;
  $('#next').disabled = busy || saveError;
  $('#compare').disabled = busy;
  if (editor) editor.dispatch({ effects: editable.reconfigure(EditorView.editable.of(!busy)) });
  document.querySelectorAll('.mission').forEach(button => {
    const mission = course.missions.find(m => m.id === button.dataset.id);
    button.disabled = busy || !unlocked(mission);
  });
}
function nextPendingMission() {
  const hasMainProgress = course.missions.some(m => !m.orientation && state.completions[m.id]);
  return course.missions.find(m => !state.completions[m.id] && unlocked(m) && (!m.orientation || !hasMainProgress));
}
function renderNavigation() {
  journey.refresh();
  const completed = course.missions.filter(m => state.completions[m.id]);
  const chapter = currentChapter();
  const chapterCompleted = completed.filter(m => m.chapter === chapter.id);
  $('#xp').textContent = `${completed.reduce((total, m) => total + m.xp, 0)} XP`;
  $('#chapter-progress').max = chapter.mission_ids.length;
  $('#chapter-progress').value = chapterCompleted.length;
  $('#chapter-count').textContent = `${chapterCompleted.length} of ${chapter.mission_ids.length} missions complete`;
  $('#total-progress').textContent = chapterCompleted.length === chapter.mission_ids.length ? `Chapter complete · ${chapter.badge}` : chapter.orientation ? chapter.title : `Chapter ${course.chapters.filter(c => !c.orientation).indexOf(chapter) + 1} · ${chapter.title}`;
  const upcoming = nextPendingMission();
  const note = $('.course-note'); note.replaceChildren(element('h3', upcoming ? 'Up next' : 'All caught up'));
  if (upcoming) {
    const nextChapter = course.chapters.find(c => c.id === upcoming.chapter);
    note.append(element('p', nextChapter.title));
    const nextLink = element('button', upcoming.title); nextLink.id = 'up-next-mission';
    nextLink.disabled = busy || saveError;
    nextLink.addEventListener('click', () => selectMission(upcoming.id).catch(showSaveError));
    note.append(nextLink);
  } else note.append(element('p', 'All main missions complete. Revisit a project or browse your grimoire.'));
  note.append(element('p', 'Hints are free. Take your time.'));
  const picker = $('#chapter-picker'); picker.replaceChildren();
  for (const chapter of course.chapters) {
    const count = chapter.mission_ids.filter(id => state.completions[id]).length;
    const option = element('option', `${chapter.title} (${count}/${chapter.mission_ids.length})`);
    option.value = chapter.id; option.selected = chapter.id === current.chapter;
    option.disabled = !chapter.mission_ids.some(id => unlocked(course.missions.find(m => m.id === id)));
    picker.append(option);
  }
  $('#missions').replaceChildren();
  let lessonNumber = 0;
  course.missions.forEach((mission, index) => {
    if (!mission.orientation) lessonNumber++;
    if (course.chapters.length > 1 && (index === 0 || course.missions[index - 1].chapter !== mission.chapter)) {
      const group = course.chapters.find(c => c.id === mission.chapter);
      const heading = element('h3', group.title);
      const count = group.mission_ids.filter(id => state.completions[id]).length;
      heading.append(element('span', `${count}/${group.mission_ids.length}`, 'chapter-status'));
      $('#missions').append(heading);
    }
    const done = !!state.completions[mission.id];
    const button = element('button', `${done ? '✓' : mission.orientation ? 'Start' : String(lessonNumber).padStart(2, '0')}  ${mission.title}`, `mission${current?.id === mission.id ? ' active' : ''}${done ? ' complete' : ''}`);
    button.dataset.id = mission.id;
    if (current?.id === mission.id) button.setAttribute('aria-current', 'step');
    if (!unlocked(mission)) button.title = 'Complete the previous mission to unlock this one.';
    button.addEventListener('click', () => selectMission(mission.id).catch(showSaveError));
    $('#missions').append(button);
  });
  updateControls();
}
async function selectMission(id) {
  if (busy) return;
  const mission = course.missions.find(m => m.id === id);
  if (!mission || !unlocked(mission)) return;
  if (current) await saveDraft();
  journey.hide();
  closeComparison();
  current = mission;
  tutor.selectMission(id);
  $('#compare').hidden = !state.completions[id];
  dirty = false;
  setCode(state.drafts[id]?.code ?? mission.starter);
  $('#save-status').textContent = state.drafts[id] ? 'Saved on this host' : 'Starter code';
  $('#lesson-title').textContent = mission.title;
  const chapter = currentChapter();
  $('#mission-number').textContent = `${mission.boss ? 'Chapter project' : 'Mission'} ${chapter.mission_ids.indexOf(mission.id) + 1} of ${chapter.mission_ids.length}`;
  $('#reward').textContent = state.completions[id] ? 'Completed' : `${mission.xp} XP`;
  const body = $('#lesson-body'); body.replaceChildren(prose('p', mission.concepts, 'concepts'));
  for (const section of mission.lesson) {
    body.append(prose('h2', section.heading), prose('p', section.text));
    if (section.code) { const pre = element('pre'); pre.append(element('code', section.code)); body.append(pre); }
  }
  body.append(element('h2', 'Your mission'), prose('p', mission.brief));
  const list = element('ul'); mission.requirements.forEach(requirement => list.append(prose('li', requirement))); body.append(list);
  body.append(element('h3', 'Expected behavior'), element('pre', mission.example));
  const hints = $('#hints'); hints.replaceChildren();
  mission.hints.forEach((hint, index) => {
    const details = element('details'); details.append(element('summary', `Hint ${index + 1}${index === 0 ? ' · start here' : ''}`), prose('p', hint)); hints.append(details);
  });
  $('#stdin').value = mission.input;
  $('#practice').checked = false;
  $('#output').textContent = '';
  $('#test-results').replaceChildren();
  $('#next').hidden = !state.completions[id] || course.missions.indexOf(mission) === course.missions.length - 1;
  feedback(state.completions[id] ? 'Completed. Keep experimenting; your completion and original passing submission are preserved.' : 'Run to experiment. Test checks examples; Submit also checks additional cases.');
  remember('workshop:last-mission', id);
  renderNavigation();
  if (state.completions[id]) await showComparison();
}
function disposeWorker() {
  clearTimeout(runTimer); clearTimeout(loadTimer);
  worker?.terminate(); worker = null;
}
function finishRun() { generation++; disposeWorker(); busy = false; pending = null; $('#runtime-status').textContent = readyMessage; updateControls(); }
function failRun(message) { finishRun(); feedback(message, 'error'); }
function startWorker() {
  disposeWorker();
  const runner = runners[current.language];
  if (!runner) { failRun(`The ${current.language} runner has not been installed yet.`); return; }
  worker = new Worker(runner);
  $('#runtime-status').textContent = 'Loading local Python…';
  loadTimer = setTimeout(() => failRun('Python took too long to load. Try Run again.'), 45000);
  worker.onerror = event => { event.preventDefault(); failRun('Could not start Python. Reload the page, or check that the local runtime files were built.'); };
  worker.onmessage = async ({ data }) => {
    if (data.type === 'ready') {
      clearTimeout(loadTimer);
      $('#runtime-status').textContent = readyMessage;
      if (pending) worker.postMessage(pending.request);
    } else if (data.type === 'started') {
      $('#runtime-status').textContent = 'Running · 5-second limit';
      runTimer = setTimeout(() => failRun('Stopped after 5 seconds. Check your loop or try a smaller input. Your code is unchanged.'), 5000);
    } else if (data.type === 'error') {
      failRun(data.message);
    } else if (data.type === 'result') {
      clearTimeout(runTimer);
      const job = pending;
      disposeWorker();
      try { await displayResult(data.result, job); }
      catch (error) { showSaveError(error); }
      finally { finishRun(); }
    }
  };
}
async function execute(mode) {
  if (busy || saveError) return;
  const activeGeneration = ++generation;
  busy = true; updateControls();
  try {
    await saveDraft();
    if (activeGeneration !== generation) return;
    $('#output').textContent = ''; $('#test-results').replaceChildren(); $('#next').hidden = true;
    feedback(mode === 'run' ? 'Running your program…' : 'Checking your code…');
    const request = { mode, code: getCode(), stdin: $('#stdin').value === '' ? [] : $('#stdin').value.replace(/\r\n/g, '\n').split('\n'), tests: mode === 'test' ? current.tests.filter(t => t.public) : current.tests };
    pending = { request, mission: current };
    startWorker();
  } catch (error) { busy = false; showSaveError(error); }
}
async function displayResult(result, job) {
  if (!job) return;
  if (result.mode === 'run') {
    $('#output').textContent = result.output + (result.error ? `\n${result.error}` : '');
    feedback(result.passed ? 'Run finished. Use Test when you are ready to check the requirements.' : 'Python found a problem. Read the final line of the error first, then check the indicated line in mission.py.', result.passed ? '' : 'error');
    return;
  }
  const passed = result.results.filter(r => r.passed).length;
  for (const item of result.results) {
    const li = element('li'); li.append(element('strong', `${item.passed ? '✓' : '✕'} ${item.label}`, item.passed ? 'pass' : 'fail'));
    if (!item.passed) {
      li.append(element('p', 'Sample input'), element('pre', item.sample_input));
      if (item.hint) li.append(element('p', item.hint));
      li.append(element('pre', item.error || `Expected:\n${item.expected}\n\nYour result:\n${item.actual || '(no output)'}`));
    }
    $('#test-results').append(li);
  }
  if (passed !== result.results.length) { feedback(`${passed} of ${result.results.length} checks passed. Nothing lost—adjust your code and try again.`, 'error'); return; }
  if (result.mode === 'test') { feedback(`All ${passed} example checks passed. Submit checks the full mission and records completion.`, 'success'); return; }
  const alreadyDone = !!state.completions[job.mission.id];
  const saved = await api('/api/submit', { mission: job.mission.id, code: job.request.code, revision: state.drafts[job.mission.id]?.revision || 0, version: job.mission.version, passed, digest: result.digest });
  state = saved.state; dirty = false;
  $('#save-status').textContent = 'Saved on this host';
  $('#reward').textContent = 'Completed';
  renderNavigation();
  const chapter = currentChapter();
  const chapterDone = chapter.mission_ids.every(id => state.completions[id]);
  feedback(alreadyDone ? `All ${passed} checks passed again. Completion kept; XP is awarded only once.` : chapterDone ? `Chapter complete! +${job.mission.xp} XP · ${chapter.badge} earned. Download your tool, then bring it back for a code review.` : `Mission complete! +${job.mission.xp} XP. The next mission is unlocked.`, 'success');
  $('#next').hidden = course.missions.indexOf(current) === course.missions.length - 1;
  $('#compare').hidden = false;
  await showComparison();
}
function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = element('a'); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function replaceFromBackup(route) {
  if (busy || saveError) return;
  busy = true; updateControls();
  try {
    await saveDraft();
    const saved = await api(route, { mission: current.id, code: getCode(), revision: state.drafts[current.id]?.revision || 0 });
    state = saved.state; setCode(saved.code); dirty = false; $('#save-status').textContent = 'Saved on this host';
    feedback(route.endsWith('reset') ? 'Starter restored. Your previous code is available through Restore reset backup.' : 'Your last reset backup is restored.');
  } catch (error) { feedback(error.message, 'error'); }
  finally { busy = false; updateControls(); }
}

$('#chapter-picker').addEventListener('change', event => {
  const missions = course.missions.filter(m => m.chapter === event.target.value);
  const next = missions.find(m => !state.completions[m.id] && unlocked(m)) || missions.find(unlocked);
  if (next) selectMission(next.id).catch(showSaveError);
});
const tutorShortcut = element('button', 'Tutor'); tutorShortcut.id = 'open-tutor';
document.querySelector('header').insertBefore(tutorShortcut, $('#export'));
tutorShortcut.addEventListener('click', () => {
  journey.hide();
  document.body.dataset.pane = 'lesson';
  document.querySelectorAll('[data-pane-button]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.paneButton === 'lesson')));
  $('#tutor').scrollIntoView({ block: 'start', behavior: 'smooth' });
  $('#tutor-question').focus({ preventScroll: true });
});

$('#run').addEventListener('click', () => execute('run'));
$('#test').addEventListener('click', () => execute('test'));
$('#submit').addEventListener('click', () => execute('submit'));
$('#stop').addEventListener('click', () => { finishRun(); feedback('Stopped. Your code is unchanged.'); });
$('#practice').addEventListener('change', () => { updateControls(); feedback($('#practice').checked ? 'Free practice: Run and Test are available. Your edits save normally; no completion or XP will be awarded.' : 'Mission mode: Submit is available.'); });
$('#next').addEventListener('click', () => { const next = course.missions[course.missions.indexOf(current) + 1]; if (next) selectMission(next.id).catch(showSaveError); });
$('#download').addEventListener('click', () => { if (current) download(`${current.id}.py`, getCode(), 'text/x-python'); });
$('#reset').addEventListener('click', () => $('#reset-dialog').showModal());
$('#cancel-reset').addEventListener('click', () => $('#reset-dialog').close());
$('#confirm-reset').addEventListener('click', () => { $('#reset-dialog').close(); replaceFromBackup('/api/reset'); });
$('#restore').addEventListener('click', () => replaceFromBackup('/api/restore'));
const compareButton = element('button', 'Compare solutions'); compareButton.id = 'compare'; compareButton.hidden = true;
$('.editor-heading').after(compareButton);
const comparison = element('div'); comparison.id = 'comparison'; comparison.hidden = true;
$('#editor').before(comparison);
compareButton.addEventListener('click', async () => {
  if (document.body.classList.contains('comparing')) { closeComparison(); editor.focus(); }
  else { try { await saveDraft(); await showComparison(); } catch (error) { showSaveError(error); } }
});
document.querySelectorAll('[data-pane-button]').forEach(button => button.addEventListener('click', () => {
  document.body.dataset.pane = button.dataset.paneButton;
  document.querySelectorAll('[data-pane-button]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
}));
$('#export').addEventListener('click', async () => {
  try { if (current) await saveDraft(); const backup = await api('/api/export'); download(`syntaxia-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(backup, null, 2), 'application/json'); feedback('Progress backup downloaded, including drafts, passing submissions, and reset backups.'); }
  catch (error) { showSaveError(error); }
});
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
window.workshopDesktop = {
  async requestLeave(requestId, closing) {
    let result;
    try { result = await this.prepareLeave({ closing }); }
    catch (error) { result = { ok: false, message: error.message }; }
    return api('/api/desktop/leave', { request_id: requestId, closing, ...result });
  },
  async prepareLeave({ closing = false } = {}) {
    if (!closing && tutor.isPending()) return { ok: false, message: 'Wait for the tutor request to finish before closing or reloading.' };
    if (busy && closing) finishRun();
    if (busy) return { ok: false, message: 'Stop the running code before closing or reloading the workshop.' };
    try {
      if (current) await saveDraft();
      if (saveError || dirty) return { ok: false, message: 'Your latest edits have not been saved. Please download your code before closing.' };
      return { ok: true, mission: current?.id };
    } catch (error) { return { ok: false, message: error.message }; }
  },
};

function registerTools() {
  const context = document.modelContext;
  if (!context?.registerTool) return;
  const lifecycle = new AbortController();
  window.addEventListener('pagehide', () => lifecycle.abort(), { once: true });
  const tool = { name: 'read_workshop_progress', description: 'Read current mission and completed course progress without changing code or awarding XP.', inputSchema: { type: 'object', properties: {}, additionalProperties: false }, annotations: { readOnlyHint: true }, execute(input) {
    if (!input || typeof input !== 'object' || Object.keys(input).length) throw new Error('Expected an empty object.');
    return { mission: current.id, completed: Object.keys(state.completions), xp: course.missions.filter(m => state.completions[m.id]).reduce((total, m) => total + m.xp, 0) };
  } };
  try { Promise.resolve(context.registerTool(tool, { signal: lifecycle.signal })).catch(() => {}); } catch { /* Optional browser integration. */ }
}

try {
  const initial = await api('/api/bootstrap');
  ({ course, state, token } = initial);
  tutor.applyAppearance(initial.appearance);
  $('#editor').replaceChildren();
  editor = new EditorView({ doc: '', extensions: editorExtensions(), parent: $('#editor') });
  $('.editor-heading label').removeAttribute('for');
  const requestedMission = new URLSearchParams(location.search).get('mission') || recall('workshop:last-mission');
  const last = course.missions.find(m => m.id === requestedMission && unlocked(m));
  const next = nextPendingMission() || course.missions.find(m => !m.orientation) || course.missions[0];
  await selectMission((last || next).id);
  $('#open-settings').disabled = false;
  $('#open-journey').disabled = false;
  $('#runtime-status').textContent = readyMessage;
  registerTools();
  lessonUpdates.start();
} catch (error) {
  feedback(`Could not load the classroom: ${error.message}. Keep the local server running and reload.`, 'error');
  $('#save-status').textContent = 'Classroom unavailable';
}
