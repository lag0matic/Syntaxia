export function createLessonUpdates(panel, api, openSettings, saveBeforeReload) {
  panel.innerHTML = [
    '<p>Check GitHub for new lessons. Syntaxia checks once per day while it is open and asks before installing.</p>',
    '<p id="lesson-update-status" role="status"></p>',
    '<div class="lesson-update-actions">',
    '<button id="check-lessons" type="button">Check for new lessons</button>',
    '<button id="install-lessons" class="primary" type="button" hidden>Install lesson update</button>',
    '</div>',
  ].join('');
  const status = panel.querySelector('#lesson-update-status');
  const checkButton = panel.querySelector('#check-lessons');
  const installButton = panel.querySelector('#install-lessons');
  const notice = document.querySelector('#lesson-update-notice');
  const viewButton = notice.querySelector('button');
  let pending = false;
  let supported = true;

  function setAvailable(available) {
    notice.hidden = !available;
    installButton.hidden = !available;
  }

  async function check(manual = false) {
    if (pending || !supported) return;
    pending = true;
    checkButton.disabled = installButton.disabled = true;
    if (manual) status.textContent = 'Checking GitHub…';
    try {
      const result = await api('/api/lessons/check', { manual });
      supported = result.supported;
      setAvailable(result.available);
      status.textContent = !supported
        ? 'Lesson updates are available for the bundled Syntaxia course.'
        : result.available
          ? 'A lesson update is available. Installing keeps your saved work.'
          : result.failed
            ? 'The last check could not finish. Check again to retry.'
            : 'Your lessons are up to date.';
    } catch (error) {
      status.textContent = error.message;
    } finally {
      pending = false;
      checkButton.disabled = !supported;
      installButton.disabled = false;
    }
  }

  async function install() {
    if (pending || installButton.hidden) return;
    pending = true;
    checkButton.disabled = installButton.disabled = true;
    try {
      await saveBeforeReload();
      status.textContent = 'Downloading and validating the lesson update…';
      const result = await api('/api/lessons/install', {});
      if (!result.installed) throw new Error('The course could not be updated.');
      setAvailable(false);
      status.textContent = 'Lessons installed. Reloading…';
      await saveBeforeReload();
      location.reload();
    } catch (error) {
      status.textContent = error.message;
    } finally {
      pending = false;
      checkButton.disabled = installButton.disabled = false;
    }
  }

  checkButton.addEventListener('click', () => check(true));
  installButton.addEventListener('click', install);
  viewButton.addEventListener('click', () => openSettings('lessons'));
  return {
    start() {
      check();
      setInterval(() => check(), 15 * 60_000);
    },
  };
}

