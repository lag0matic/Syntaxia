import { appendInlineCode } from './inline-code.js';
export function createGrimoire({ api, getState, openLesson }) {
  const button = document.createElement('button');
  button.id = 'open-grimoire'; button.textContent = 'Grimoire';
  document.querySelector('header').insertBefore(button, document.querySelector('#export'));
  const dialog = document.createElement('dialog'); dialog.id = 'grimoire';
  dialog.setAttribute('aria-labelledby', 'grimoire-title');
  dialog.innerHTML = '<div class="grimoire-toolbar"><h2 id="grimoire-title">Grimoire</h2><button id="grimoire-back" type="button" disabled>Back</button><button id="grimoire-close" type="button">Close</button></div><label for="grimoire-search">Search your covered concepts</label><input id="grimoire-search" type="search" placeholder="Try return, remainder, or traceback"><p id="grimoire-status" role="status"></p><div class="grimoire-layout"><nav id="grimoire-index" aria-label="Concepts"></nav><article id="grimoire-article" tabindex="0"></article></div>';
  document.body.append(dialog);
  const $ = id => document.getElementById(id);
  let entries = [], active, history = [];
  const node = (tag, text) => { const e = document.createElement(tag); e.textContent = text; return e; };
  const prose = (tag, text) => appendInlineCode(document.createElement(tag), text);
  function show(id, push = true) {
    const entry = entries.find(e => e.id === id); if (!entry) return;
    if (push && active && active !== id) history.push(active);
    active = id; $('grimoire-back').disabled = !history.length;
    const article = $('grimoire-article'); article.replaceChildren(prose('h3', entry.title));
    for (const paragraph of entry.text) article.append(prose('p', paragraph));
    const pre = node('pre', entry.code); article.append(pre, node('h4', 'Watch for'), prose('p', entry.pitfall));
    const related = node('div', ''); related.className = 'grimoire-links';
    for (const link of entry.related) {
      const target = entries.find(e => e.id === link); if (!target) continue;
      const b = prose('button', target.title); b.type = 'button'; b.onclick = () => show(link); related.append(b);
    }
    if (related.childElementCount) article.append(node('h4', 'Related concepts'), related);
    const lesson = node('button', 'Revisit lesson'); lesson.type = 'button';
    lesson.onclick = async () => { try { await openLesson(entry.mission); dialog.close(); } catch (e) { $('grimoire-status').textContent = e.message; } };
    article.append(lesson); article.scrollTop = 0;
    for (const b of $('grimoire-index').querySelectorAll('button')) b.setAttribute('aria-current', b.dataset.id === id ? 'page' : 'false');
  }
  function search() {
    const query = $('grimoire-search').value.toLowerCase().trim();
    const matches = entries.filter(e => [e.title, ...e.aliases, ...e.text, e.code, e.pitfall].join(' ').replaceAll('`', '').toLowerCase().includes(query));
    $('grimoire-index').replaceChildren();
    for (const entry of matches) {
      const b = prose('button', entry.title); b.type = 'button'; b.dataset.id = entry.id;
      b.setAttribute('aria-current', entry.id === active ? 'page' : 'false'); b.onclick = () => show(entry.id);
      $('grimoire-index').append(b);
    }
    $('grimoire-status').textContent = matches.length ? `${matches.length} covered concepts` : entries.length ? 'No matching covered concepts. Try another word.' : 'No entries yet. Reference pages unlock as you complete lessons.';
    if (matches.length && !matches.some(e => e.id === active)) show(matches[0].id);
    if (!matches.length) { $('grimoire-article').replaceChildren(); active = undefined; }
  }
  $('grimoire-search').addEventListener('input', search);
  $('grimoire-close').onclick = () => dialog.close();
  $('grimoire-back').onclick = () => { const id = history.pop(); if (id) show(id, false); };
  button.onclick = async () => {
    $('grimoire-index').replaceChildren();
    $('grimoire-article').replaceChildren();
    $('grimoire-search').disabled = true;
    dialog.showModal(); $('grimoire-status').textContent = 'Loading your grimoire...';
    try {
      const data = await api('/api/grimoire');
      entries = data.entries.filter(e => getState().completions[e.mission]);
      history = []; active = undefined; $('grimoire-back').disabled = true;
      $('grimoire-search').disabled = false; $('grimoire-search').value = ''; search(); $('grimoire-search').focus();
    } catch (e) { $('grimoire-status').textContent = e.message; }
    finally { $('grimoire-search').disabled = false; }
  };
}
