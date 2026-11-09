# Syntaxia desktop (Rust / Tauri)

Double-click **Syntaxia.exe**, or the **Syntaxia** desktop shortcut. Keep Syntaxia Service.exe beside it. The Rust shell owns the window and menus; the packaged Python service owns local lessons, progress and tutoring. Both launch together; no Python installation is needed to use the packaged app.

Build with `.desktop-venv/Scripts/python.exe build-rust.py`. The older build-desktop.py is the legacy pywebview build. Lessons, grimoire and data remain external. The existing workshop.course.json and data paths have deliberately retained their names for compatibility. The Tauri application identifier is also unchanged, so renaming does not switch application storage. Artwork A remains the launcher icon and B the runtime window icon.

Use **Settings > Appearance** to choose a palette and set the lesson and editor text sizes. Expand **Individual colors** to override the interface accent, inline Python, or editor syntax colors. Appearance preferences are stored alongside progress for the open course. **Settings > Tutor** is where you enter an API key and test the connection.

**Journey** shows illustrated chapter badges, XP, completed projects, recent lessons, and the next lesson. It uses your existing course progress.

**Settings > Lessons** checks the public GitHub repository for course updates. Syntaxia checks automatically once per local calendar day while open and asks before installing. Lesson updates preserve saved progress, drafts, and tutor settings.\n\nOlder operational notes follow; the Rust/Tauri startup description above supersedes their desktop implementation details.

# Syntaxia

A personal Python classroom for David. Two chapters are available: the seven-mission console review and a 16-mission Functions and returned values chapter. Completing the demo unlocks the first functions lesson. Refresh after a content update, then use Next mission on the demo's final lesson or select the new chapter in the sidebar.

## Start learning

1. Double-click **Syntaxia.exe** in this folder.
2. Continue your lesson in the desktop window. Read the explanation and requirements, write code, then use Run, Test, and Submit.
3. Close the window when finished. It saves your draft and current lesson, and stops its background server. Stop running code before closing.

The Windows desktop app includes Python, the editor, and the exercise runtime. You do not need Python or Node installed to use the EXE. It uses Microsoft Edge WebView2 Runtime, already available on this PC. No browser tab or terminal window needs to remain open. One desktop window per progress database is allowed.

Keep these items together in a writable folder:

```text
Syntaxia.exe       application (replace only for app features/fixes)
workshop.course.json      course descriptor
content/                  catalog and editable chapter JSON files
data/                     your saved work; keep when updating anything else
```

**Course → Reload lessons** picks up lesson edits. **Open lesson folder** opens the content location. You can also drag another `.course.json` file onto the EXE, or choose **Course → Open another course…**. Each course descriptor selects its own progress database. Double-click the EXE itself; a Windows association for course files has not been installed.

The older browser mode remains available through `start-workshop.cmd` and http://127.0.0.1:8765. That mode requires Python 3.10+ and an open server process. Avoid editing the same mission in desktop and browser simultaneously; conflicting saves are rejected.

The first build is already included in `dist/`, including the Python runtime and editor. Ordinary use needs no internet, account, subscription, or AI API key. A fresh development build needs Node.js and an initial dependency download.

## Tutor chat

The Tutor panel appears below the lesson. Open **Settings**, enter your OpenAI API key, and choose **Save & test connection**. The defaults are OpenAI's base URL, gpt-6-luna, and low reasoning. Model, endpoint, reasoning and output-token budget are editable. API use draws from your provider credits; lessons and offline hints work without it.

Ask in natural language, or choose **Give me a hint**. Enter sends and Shift+Enter adds a line. Replies are instructed to be concise and hint-first. To request a full solution explicitly, say **Show me the full solution**. After passing, **Explain these differences** opens a prefilled comparison question; press Send when ready. No automatic reviews or background API requests occur.

Each lesson keeps its own chat history. Sending shares the current lesson, editor code, the latest run results and whether they apply to the current code, and recent conversation with your configured provider. Recent editor snapshots are kept with the chat so the tutor can distinguish earlier code from later edits. The key is encrypted for your Windows account, remains on the host, and is excluded from progress exports. Moving to another PC/account requires re-entering it. Tutor access is local to this computer.

The existing progress export covers code/completions, not chat. Copy the data folder with the app closed to retain chat history too.

## Learning controls

- In the editor, **Tab** accepts the highlighted autocomplete suggestion when its menu is open. Otherwise it indents four spaces; **Shift+Tab** unindents. **Ctrl+Space** opens suggestions explicitly.
- **Run** executes the editor contents with the answers in Program input. Enter one answer per line before running. A blank first line represents an empty first answer when followed by other answers.
- **Test** runs the example checks. **Submit** runs all checks and records completion when they pass.
- Regular missions award 10 XP once; the chapter project awards 30 XP once. Total chapter reward: 90 XP and the Console builder badge.
- Hints are free. Failed attempts do not lose points. Each completed mission unlocks the next.
- After passing Submit, the editor area shows **Your passing code** beside a **Reference solution**, with explanations underneath. Both comparison panes are read-only. **Back to editing** returns to your untouched working draft; **Compare solutions** reopens the comparison. Completed lessons also show it when revisited, including lessons passed before this feature was added. The learner pane uses the most recent passing submission, not an unfinished draft. On small screens the two solutions stack for readability.
- **Free practice** disables Submit while keeping Run, Test, and saved edits available. Completed submissions remain preserved separately.
- **Reset** saves a snapshot before restoring starter code. **Restore reset backup** retrieves the most recent pre-reset snapshot.
- **Download .py** saves your current program. **Back up progress** exports drafts, completions, and snapshots as JSON.
- On narrow screens, use **Lesson** and **Code & results** to switch views. On wide screens the panes scroll independently.
- The editor saves after a brief pause. Check **Saved on this host** before closing. If saving fails, download your code before reloading. Conflicting edits in different tabs are rejected rather than silently overwritten.

## Your data

The host stores progress in `data/workshop.sqlite3`; lesson packages live separately in `content/`. Editing or adding a chapter does not replace the database. The database and reset/submission snapshots contain your source code.

For a complete transferable desktop backup, close the app and copy the EXE, `workshop.course.json`, `content/`, and `data/` together. Build tools and `node_modules` are not needed. The in-app JSON export is an additional readable backup; automatic JSON import is not implemented yet.

## Moving to the Windows 11 server

The same app can run on your private server later. Copy this folder, including `dist/` and `data/`, and install Python if necessary. Node is not needed merely to run the built app.

Default startup binds only to this PC. To deliberately enable LAN access, run:

```powershell
py -3 server.py --host 0.0.0.0 --allowed-host YOUR_SERVER_LAN_IP
```

Replace the placeholder with the server's actual LAN address, then open `http://YOUR_SERVER_LAN_IP:8765` from another machine. Additional `--allowed-host` flags allow a hostname too. Permit port 8765 only on the private network if Windows Firewall requires it. No firewall rules have been changed by this build.

This first version has one shared learner and no login. Everyone who can reach that LAN address can view/edit the same progress. It is intended for your trusted local network, not public internet exposure. LAN deployment has not been tested on the separate server yet.

## How execution works

The Python host serves the interface and saves data. It does **not** execute learner programs. Pyodide 0.27.7 runs Python in a fresh browser Web Worker for each action. Stop and the five-second execution limit terminate that worker. Output is capped at 20,000 characters. The Python files and editor are served locally; no CDN requests are required.

This separation protects the host from accidental learner file operations, but is not a hardened adversarial code sandbox. Browser Python has a virtual filesystem that is discarded after each action. It cannot directly use the host's normal files or installed Python packages. Native extensions and arbitrary pip packages are outside this first chapter. Memory is governed by the browser, not a hard application quota.

Grading is for personal learning, not certification: behavior is tested in the browser and completion is recorded by the server. A determined user can alter client-side results. Tests do not prove that every instruction about coding style or choice of construct was followed; code review remains part of tutoring.

## Development and verification

```powershell
npm ci
npm run build
python -m unittest discover -s tests -p test_*.py
node tests/browser.mjs
```

Browser checks use installed Microsoft Edge and a temporary database on an automatically assigned local port. They do not complete missions in the real learner database. Screenshots go to `qa/`. Reference solutions are test fixtures outside the served directory; they are not shown in lessons.

`src/app.js` is bundled into `dist/app.js`. HTML and CSS are authored directly in `dist/`. `build.mjs` also copies the worker, grading harness, and bundled runtime. Changing Python server code requires a server restart; changing lesson packages needs a browser reload. `package-lock.json` fixes the dependency versions.

Read `../PROJECT.md` and `STATUS.md` before continuing work. For content authoring, see `CONTENT.md`.

### Rebuilding the desktop launcher

Only app changes require these steps. Lesson edits do not.

```powershell
python -m venv .desktop-venv
.\.desktop-venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
npm ci
npm run build
.\.desktop-venv\Scripts\python.exe build-rust.py
```

The build creates `Syntaxia.exe` beside the course file. Close the running app before replacing it. The EXE bundles `dist/` and host code, never lesson content or learner data. The interface still uses web technology internally in its own desktop window; it binds a temporary loopback port automatically and shuts down on exit. Desktop mode is local to this PC. Other languages and native package projects still require future runner support.
