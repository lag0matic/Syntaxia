import { color } from '@codemirror/theme-one-dark';

const defaults = { theme: 'amethyst', reading_size: 16, editor_size: 15, colors: {} };
const palettes = {
  amethyst: { accent: '#c39af2', inline: '#e2b9ff' },
  forest: { accent: '#a5db9f', inline: '#c0e6bc' },
  ember: { accent: '#ffb17e', inline: '#ffc8a5' },
  slate: { accent: '#98c7fa', inline: '#b7d8fc' },
};
const colorOptions = [
  ['accent', 'Interface accent'],
  ['inline', 'Inline Python'],
  ['keyword', 'Editor keywords', color.violet],
  ['string', 'Editor strings', color.sage],
  ['number', 'Editor numbers', color.chalky],
  ['comment', 'Editor comments', color.stone],
];

export function createAppearance(panel, api) {
  panel.innerHTML = `
    <form id="appearance-form">
      <label for="appearance-theme">Color palette</label>
      <select id="appearance-theme" name="theme">
        <option value="amethyst">Amethyst</option>
        <option value="forest">Forest</option>
        <option value="ember">Ember</option>
        <option value="slate">Slate</option>
      </select>
      <label for="appearance-reading">Reading text size</label>
      <select id="appearance-reading" name="reading_size">
        <option value="14">Small</option>
        <option value="16">Standard</option>
        <option value="18">Large</option>
        <option value="20">Extra large</option>
      </select>
      <label for="appearance-editor">Editor text size</label>
      <select id="appearance-editor" name="editor_size">
        <option value="13">Small</option>
        <option value="15">Standard</option>
        <option value="17">Large</option>
        <option value="19">Extra large</option>
      </select>
      <details id="appearance-colors">
        <summary>Individual colors</summary>
        <p class="settings-help">Choose a color to override the palette. Use default restores that color.</p>
        ${colorOptions.map(([name, label]) => `
          <div class="appearance-color">
            <label for="color-${name}">${label}</label>
            <input id="color-${name}" type="color">
            <button type="button" id="reset-${name}" aria-label="Use default for ${label.toLowerCase()}">Use default</button>
          </div>`).join('')}
      </details>
      <p id="appearance-status" role="status"></p>
      <div class="settings-actions">
        <button id="appearance-reset" type="button">Restore defaults</button>
        <button type="submit" class="primary">Save appearance</button>
      </div>
    </form>`;
  const form = panel.querySelector('form');
  const status = panel.querySelector('#appearance-status');
  const theme = form.elements.namedItem('theme');
  const root = document.documentElement;
  const rows = colorOptions.map(([name, label, defaultColor]) => ({
    name, defaultColor,
    input: panel.querySelector('#color-' + name),
    reset: panel.querySelector('#reset-' + name),
  }));
  let saving = false;
  let overrides = {};

  function renderColors() {
    for (const { name, defaultColor, input, reset } of rows) {
      input.value = overrides[name] ?? palettes[theme.value][name] ?? defaultColor;
      input.disabled = saving;
      reset.disabled = saving || !overrides[name];
    }
  }

  for (const { name, input, reset } of rows) {
    input.addEventListener('input', () => {
      overrides[name] = input.value;
      reset.disabled = false;
    });
    reset.addEventListener('click', () => {
      delete overrides[name];
      renderColors();
    });
  }
  theme.addEventListener('change', renderColors);

  function apply(saved = defaults) {
    const { colors = {}, ...preferences } = saved;
    root.dataset.theme = preferences.theme;
    root.style.setProperty('--reading-size', preferences.reading_size + 'px');
    root.style.setProperty('--editor-size', preferences.editor_size + 'px');
    for (const [name, value] of Object.entries(preferences)) {
      form.elements.namedItem(name).value = String(value);
    }
    overrides = { ...colors };
    for (const { name } of rows) {
      if (colors[name]) root.style.setProperty('--custom-' + name, colors[name]);
      else root.style.removeProperty('--custom-' + name);
    }
    renderColors();
  }

  async function save(preferences) {
    if (saving) return;
    saving = true;
    for (const field of form.elements) field.disabled = true;
    status.textContent = 'Saving…';
    try {
      apply(await api('/api/appearance', preferences));
      status.textContent = 'Appearance saved.';
    } catch (error) {
      status.textContent = error.message;
    } finally {
      saving = false;
      for (const field of form.elements) field.disabled = false;
      renderColors();
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    const fields = new FormData(form);
    save({
      theme: fields.get('theme'),
      reading_size: Number(fields.get('reading_size')),
      editor_size: Number(fields.get('editor_size')),
      colors: { ...overrides },
    });
  });
  panel.querySelector('#appearance-reset').addEventListener('click', () => save(defaults));
  return { apply, isSaving: () => saving };
}

