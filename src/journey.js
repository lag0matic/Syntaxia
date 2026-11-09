export function createJourney({ getCourse, getCompletions, openLesson, nextMission }) {
  const page = document.querySelector('#journey');
  const button = document.querySelector('#open-journey');
  const workspace = document.querySelector('.workspace');
  const paneSwitch = document.querySelector('.pane-switch');
  const heading = page.querySelector('h1');
  const content = page.querySelector('#journey-content');
  const node = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  };
  const lessonButton = (mission, label = mission.title) => {
    const item = node('button', label, 'journey-lesson-link');
    item.type = 'button';
    item.addEventListener('click', () => openLesson(mission.id));
    return item;
  };

  function render() {
    const course = getCourse();
    const completions = getCompletions();
    const completed = course.missions.filter(mission => completions[mission.id]);
    const earned = course.chapters.filter(chapter =>
      chapter.mission_ids.every(id => completions[id]));
    const projects = completed.filter(mission => mission.boss);
    const xp = completed.reduce((sum, mission) => sum + mission.xp, 0);

    const summary = node('dl', undefined, 'journey-summary');
    for (const [label, value] of [
      ['Lessons complete', completed.length + ' / ' + course.missions.length],
      ['XP earned', xp.toLocaleString()],
      ['Chapter badges', earned.length],
      ['Projects complete', projects.length],
    ]) {
      const metric = node('div');
      metric.append(node('dt', label), node('dd', value));
      summary.append(metric);
    }

    const badges = node('section', undefined, 'journey-section');
    badges.append(node('h2', 'Chapter badges'));
    const list = node('ul', undefined, 'journey-list');
    for (const chapter of course.chapters) {
      const done = chapter.mission_ids.filter(id => completions[id]).length;
      const row = node('li', undefined, 'journey-badge');
      const name = node('div', undefined, 'journey-badge-name');
      const art = node('img', undefined, 'journey-badge-art');
      art.alt = '';
      art.width = art.height = 54;
      art.addEventListener('error', () => art.remove(), { once: true });
      art.src = '/api/badges/' + encodeURIComponent(chapter.id);
      const text = node('div');
      text.append(node('strong', chapter.badge), node('p', chapter.title));
      name.append(art, text);
      const progress = node('progress');
      progress.max = chapter.mission_ids.length;
      progress.value = done;
      progress.setAttribute('aria-label', chapter.title + ' progress');
      const earnedBadge = done === progress.max;
      row.classList.toggle('earned', earnedBadge);
      const label = earnedBadge ? 'Earned' : done + ' / ' + progress.max + ' lessons';
      row.append(name, progress, node('span', label, earnedBadge ? 'journey-earned' : 'journey-count'));
      list.append(row);
    }
    badges.append(list);

    const recent = [...completed].sort((a, b) => {
      const time = mission => Date.parse(completions[mission.id].completed) || 0;
      return time(b) - time(a);
    });
    const history = node('section', undefined, 'journey-section');
    history.append(node('h2', 'Recent lessons'));
    if (recent.length) {
      const rows = node('ul', undefined, 'journey-list');
      for (const mission of recent.slice(0, 8)) {
        const row = node('li', undefined, 'journey-history-row');
        const timestamp = completions[mission.id].completed;
        const date = new Date(timestamp);
        row.append(lessonButton(mission), node('span', Number.isNaN(date.getTime()) ? 'Completed' : date.toLocaleDateString(), 'journey-count'));
        rows.append(row);
      }
      history.append(rows);
    } else {
      history.append(node('p', 'Completed lessons will appear here.'));
    }
    const projectList = node('section', undefined, 'journey-section');
    projectList.append(node('h2', 'Completed projects'));
    if (projects.length) {
      const rows = node('ul', undefined, 'journey-list');
      for (const mission of projects) {
        const row = node('li');
        row.append(lessonButton(mission));
        rows.append(row);
      }
      projectList.append(rows);
    } else {
      projectList.append(node('p', 'Chapter projects will appear here as you finish them.'));
    }

    const upcoming = nextMission();
    const next = node('div', undefined, 'journey-next');
    if (upcoming) next.append(node('span', 'Up next'), lessonButton(upcoming));
    else next.append(node('span', 'You’re caught up with the main course.'));
    content.replaceChildren(summary, next, badges, projectList, history);
  }

  function hide({ focus = false } = {}) {
    if (page.hidden) return;
    page.hidden = true;
    workspace.hidden = false;
    paneSwitch.hidden = false;
    button.setAttribute('aria-pressed', 'false');
    if (focus) button.focus();
  }

  button.addEventListener('click', () => {
    if (!page.hidden) { hide({ focus: true }); return; }
    render();
    workspace.hidden = true;
    paneSwitch.hidden = true;
    page.hidden = false;
    page.scrollTop = 0;
    button.setAttribute('aria-pressed', 'true');
    heading.focus();
  });
  page.querySelector('#journey-back').addEventListener('click', () => hide({ focus: true }));
  return { hide, refresh: () => { if (!page.hidden) render(); } };
}

