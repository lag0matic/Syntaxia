import { createAppearance } from './appearance.js';

export function createTutor({ api, getContext, settingsPanel }) {
  const oldHints = document.querySelector('#hints');
  const panel = document.createElement('section');
  panel.id = 'tutor';
  panel.setAttribute('aria-labelledby', 'tutor-heading');
  panel.innerHTML = '<div class="tutor-heading"><h2 id="tutor-heading">Tutor</h2><button id="tutor-settings-open" type="button">Settings</button></div><p class="tutor-guidance">Hints first. Ask for the full solution only when you want it.</p><div id="tutor-messages" role="log" aria-label="Tutor conversation" tabindex="0" aria-live="polite"></div><p id="tutor-status" role="status"></p><form id="tutor-form"><label for="tutor-question">Ask about this lesson</label><textarea id="tutor-question" rows="2" maxlength="4000" placeholder="What am I missing here?"></textarea><div class="tutor-actions"><button type="button" id="tutor-hint">Give me a hint</button><button type="submit" id="tutor-send" class="primary">Send</button></div></form><details id="offline-hints"><summary>Offline hints</summary><div id="hints"></div></details>';
  oldHints.replaceWith(panel);
  const dialog = document.createElement('dialog');
  dialog.id = 'tutor-settings';
  dialog.setAttribute('aria-labelledby', 'tutor-settings-heading');
  dialog.innerHTML = '<div class="settings-heading"><h2 id="tutor-settings-heading">Settings</h2><button type="button" id="tutor-settings-close">Close</button></div><nav class="settings-nav" aria-label="Settings sections"><button type="button" data-settings-pane="appearance" aria-controls="settings-appearance">Appearance</button><button type="button" data-settings-pane="tutor" aria-controls="settings-tutor">Tutor</button><button type="button" data-settings-pane="lessons" aria-controls="settings-lessons">Lessons</button></nav><div id="settings-appearance"></div><div id="settings-lessons" hidden></div><div id="settings-tutor" hidden><form id="tutor-settings-form"><label for="tutor-endpoint">API base URL</label><input id="tutor-endpoint" type="url" required placeholder="https://api.openai.com/v1"><p class="settings-help">An HTTPS endpoint compatible with the Responses API. Changing the endpoint clears the saved key unless you enter a new one.</p><label for="tutor-key">API key</label><input id="tutor-key" type="password" autocomplete="off" spellcheck="false" maxlength="4096" placeholder="Leave blank to keep the saved key"><p id="tutor-key-state" class="settings-help"></p><label class="key-remove"><input id="tutor-key-remove" type="checkbox"> Remove saved key</label><label for="tutor-model">Model name</label><input id="tutor-model" required maxlength="160" placeholder="gpt-6-luna"><label for="tutor-reasoning">Reasoning</label><select id="tutor-reasoning"><option value="omit">Provider default (omit setting)</option><option value="none">None</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="xhigh">Extra high</option><option value="max">Maximum</option></select><label for="tutor-limit">Maximum output tokens</label><input id="tutor-limit" type="number" min="256" max="16000" required><p class="settings-help">Includes reasoning tokens. Replies are instructed to stay brief regardless of this limit.</p><p class="settings-help">Sending shares this lesson, your current code and results, and recent chat context with the selected provider. Chat history and editor snapshots are saved on this PC. Keys are encrypted for your Windows account and are never included in progress exports.</p><p id="tutor-settings-status" role="status"></p><div class="tutor-actions"><button type="button" id="tutor-test">Save &amp; test connection</button><button type="submit" id="tutor-save">Save</button></div><p class="settings-help">A connection test sends a tiny API request and may use credits.</p></form></div>';
  document.body.append(dialog);
  const $ = id => document.getElementById(id);
  const appearance = createAppearance(dialog.querySelector('#settings-appearance'), api);
  const settingsNav = dialog.querySelectorAll('[data-settings-pane]');
  let settingsLoading = false, settingsLoaded = false;
  let mission, pending = false, loading = false, mode = 'hint', settingsBusy = false;
  const conversations = new Map(), drafts = new Map();
  let settings = { has_key: false, model: 'gpt-6-luna', endpoint: 'https://api.openai.com/v1' };
  function message(role, text) {
    const row = document.createElement('div'); row.className = 'tutor-message';
    const label = document.createElement('strong'); label.textContent = role === 'user' ? 'You' : 'Tutor'; row.append(label);
    // Render text and fenced snippets without interpreting provider HTML.
    const parts = text.split(/(\x60\x60\x60[\s\S]*?\x60\x60\x60)/g);
    for (const part of parts) {
      if (!part) continue;
      const fenced = part.startsWith('\x60\x60\x60');
      const node = document.createElement(fenced ? 'pre' : 'p');
      node.textContent = fenced ? part.replace(/^\x60\x60\x60[^\n]*\n?/, '').replace(/\x60\x60\x60$/, '') : part.trim();
      row.append(node);
    }
    $('tutor-messages').append(row);
  }
  function render() {
    $('tutor-messages').replaceChildren();
    const messages = conversations.get(mission) || [];
    if (!messages.length) {
      const note = document.createElement('p'); note.className = 'tutor-empty';
      note.textContent = 'Ask a question in your own words. I’ll start with a nudge, not the answer.';
      $('tutor-messages').append(note);
    } else for (const item of messages) message(item.role, item.content);
    $('tutor-messages').scrollTop = $('tutor-messages').scrollHeight;
  }
  function controls() {
    $('tutor-send').disabled = pending || loading || !mission || !settings.has_key;
    $('tutor-hint').disabled = pending || loading || !mission || !settings.has_key;
    $('tutor-question').disabled = pending || loading;
    $('tutor-settings-open').disabled = pending;
  }
  async function selectMission(id) {
    if (mission) drafts.set(mission, $('tutor-question').value);
    mission = id; mode = 'hint'; loading = true;
    $('tutor-question').value = drafts.get(id) || '';
    $('tutor-status').textContent = 'Loading conversation…'; render(); controls();
    try {
      const [config, history] = await Promise.all([api('/api/tutor/settings'), api('/api/tutor/history/' + encodeURIComponent(id))]);
      settings = config; conversations.set(id, history.messages);
      if (mission !== id) return;
      render();
      $('tutor-status').textContent = config.has_key ? config.model + ' · replies on request' : 'Add your API key in Settings to chat. Offline hints are available below.';
    } catch (error) {
      if (mission === id) $('tutor-status').textContent = error.message;
    } finally {
      if (mission === id) { loading = false; controls(); }
    }
  }
  async function send(event) {
    event?.preventDefault();
    if (pending || loading || !mission || !settings.has_key) return;
    const text = $('tutor-question').value.trim();
    if (!text) return;
    const id = mission;
    const context = getContext();
    if (context.mission !== id) return;
    pending = true; controls(); message('user', text);
    $('tutor-messages').scrollTop = $('tutor-messages').scrollHeight;
    $('tutor-status').textContent = 'Thinking…';
    try {
      const result = await api('/api/tutor/chat', { ...context, message: text, mode });
      conversations.set(id, result.messages); drafts.delete(id);
      if (mission === id) {
        mode = 'hint';
        $('tutor-question').value = ''; render();
        const used = result.usage?.total_tokens;
        $('tutor-status').textContent = used ? settings.model + ' · ' + used + ' tokens this reply' : settings.model;
      }
    } catch (error) {
      if (mission === id) { render(); $('tutor-status').textContent = error.message; }
    } finally {
      pending = false; controls();
    }
  }
  $('tutor-form').addEventListener('submit', send);
  $('tutor-question').addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); send(); }
  });
  $('tutor-hint').addEventListener('click', () => {
    $('tutor-question').value = 'Please give me one small hint without giving away the solution.'; send();
  });
  async function loadTutorSettings() {
    if (settingsLoading || settingsLoaded || settingsBusy) return;
    settingsLoading = true;
    settingsControls();
    $('tutor-settings-status').textContent = 'Loading tutor settings…';
    try {
      settings = await api('/api/tutor/settings');
      $('tutor-endpoint').value = settings.endpoint;
      $('tutor-model').value = settings.model;
      $('tutor-reasoning').value = settings.reasoning;
      $('tutor-limit').value = settings.max_output_tokens;
      $('tutor-key-remove').checked = false;
      $('tutor-key-state').textContent = settings.key_source === 'environment'
        ? 'Using OPENAI_API_KEY from this app\u2019s environment.'
        : settings.has_key ? 'A key is saved, encrypted for your Windows account.' : 'No key saved yet.';
      $('tutor-settings-status').textContent = '';
      settingsLoaded = dialog.open;
    } catch (error) {
      $('tutor-settings-status').textContent = error.message;
    } finally {
      settingsLoading = false;
      settingsControls();
    }
  }
  function settingsControls() {
    for (const field of $('tutor-settings-form').elements) {
      field.disabled = settingsBusy || !settingsLoaded;
    }
  }
  function openSettings(section = 'appearance') {
    $('settings-appearance').hidden = section !== 'appearance';
    $('settings-tutor').hidden = section !== 'tutor';
    $('settings-lessons').hidden = section !== 'lessons';
    for (const button of settingsNav) {
      button.setAttribute('aria-pressed', String(button.dataset.settingsPane === section));
    }
    if (!dialog.open) dialog.showModal();
    if (section === 'tutor') loadTutorSettings();
  }
  for (const button of settingsNav) {
    button.addEventListener('click', () => openSettings(button.dataset.settingsPane));
  }
  $('tutor-settings-open').addEventListener('click', () => openSettings('tutor'));
  async function saveSettings(test) {
    if (settingsBusy || !settingsLoaded || !$('tutor-settings-form').reportValidity()) return;
    settingsBusy = true; settingsControls();
    $('tutor-settings-status').textContent = 'Saving…';
    const body = { endpoint: $('tutor-endpoint').value.trim(), model: $('tutor-model').value.trim(),
      reasoning: $('tutor-reasoning').value, max_output_tokens: Number($('tutor-limit').value),
      api_key: $('tutor-key').value.trim(), remove_key: $('tutor-key-remove').checked };
    $('tutor-key').value = '';
    try {
      settings = await api('/api/tutor/settings', body);
      $('tutor-key-state').textContent = settings.has_key ? 'Key configured. Stored keys are encrypted for your Windows account.' : 'No saved key.';
      $('tutor-settings-status').textContent = 'Settings saved.';
      $('tutor-status').textContent = settings.has_key ? settings.model + ' · ready when you are' : 'Add an API key to chat. Offline hints are available below.';
      if (test) {
        $('tutor-settings-status').textContent = 'Testing connection…';
        const result = await api('/api/tutor/test', { test: true });
        $('tutor-settings-status').textContent = result.message;
      }
    } catch (error) { $('tutor-settings-status').textContent = error.message; }
    finally {
      settingsBusy = false;
      settingsControls();
      controls();
      if (dialog.open && !$('settings-tutor').hidden) loadTutorSettings();
    }
  }
  $('tutor-settings-form').addEventListener('submit', event => { event.preventDefault(); saveSettings(false); });
  $('tutor-test').addEventListener('click', () => saveSettings(true));
  $('tutor-settings-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    $('tutor-key').value = '';
    settingsLoaded = false;
    settingsControls();
  });
  settingsPanel?.($('settings-lessons'), openSettings);
  return {
    selectMission,
    openSettings,
    applyAppearance: appearance.apply,
    isPending: () => pending || settingsBusy || appearance.isSaving(),
    discuss() {
      mode = 'compare';
      $('tutor-question').value = 'Why does the reference solution take a different approach from my passing code?';
      document.body.dataset.pane = 'lesson';
      document.querySelectorAll('[data-pane-button]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.paneButton === 'lesson')));
      panel.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      $('tutor-question').focus();
      $('tutor-status').textContent = 'Comparison included. Edit the question or press Send.';
    },
  };
}
