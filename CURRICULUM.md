## Readable Python prose, beginner tutorial and portable release - 2026-11-08

Syntaxia now renders explicitly backticked code spans in lavender monospace in lesson prose, assignment rules, hints, comparison notes, and grimoire articles. Plain text stays literal (no HTML interpretation). Updated all nine existing chapters and reference pages, including the and/chained-comparison example; ordinary conjunctions remain prose. Disabled programming ligatures so <= and >= retain the characters learners must type. Existing mission IDs, XP, prerequisites, examples, starters, reference code and tests verified unchanged against the pre-format content backup. Assignment wording verified unchanged apart from inserted formatting. Future authors should explicitly mark all actual code with backticks.

Added a one-mission optional Start here tutorial (py-orientation-first-run). Fresh learners start here and learn print, strings, comments, reading output, and Run/Test/Submit. First Page badge/10 XP; existing main chapter numbers and badges are unchanged. Returning learners with main-course progress are not sent back to the tutorial. It remains available from course navigation. Installed course now has ten groups including tutorial, 89 missions. Added ten grimoire articles and moved first-use anchors earlier (input, arithmetic, comparisons, indentation, functions, return, or, tracebacks); 57 total. The tutorial unlocks three beginner references. Grimoire clears old entries while refreshing to show newly unlocked articles reliably. Tutor wording is learner-neutral for sharing; hints-first behavior and saved settings unchanged.

Portable release: D:/tutorme/releases/Syntaxia-Windows-x64-20261108.zip (21.5 MB), intended for a shared drive. Extract all and launch Syntaxia/Syntaxia.exe. It contains the x64 Rust launcher, bundled local service and offline Python runtime, public course/grimoire content, README and available third-party notices. No progress, drafts, tutor conversations, key/settings, backups or test folders. WebView2 is required and normally present on Windows 11. No separately installed Python is needed. The optional tutor uses the recipient's own key. No upload or message sent. Repeatable builder: .desktop-venv/Scripts/python.exe package-portable.py after updating the packaged service. The archive was extracted to a clean test folder with Python removed from subprocess PATH, launcher checked, service booted with zero progress/key, offline WASM assets checked, and service shut down cleanly. A temporary test SQLite connection was explicitly closed before cleanup. This does not claim testing on the recipient's PC.

Verification: 26 Python methods pass. tests/beginner-browser.mjs passed fresh tutorial Run/Test/Submit, early grimoire unlocks through review, returning-user tutorial skip, preserved prior badge, distinct inline code colors, literal HTML safety and narrow layout. Screenshots reviewed. Rebuilt Syntaxia Service.exe (Rust launcher unchanged) and installed it; reopen Syntaxia to see the improvements. Previous service and content under data/backups/before-inline-code-*. No real learner progress or tutor settings were changed. Remaining work was done in D:/tutorme; temporary authoring files in D:/Voron were removed.
## Four-chapter learning block installed - 2026-11-08

David completed all 46 prior lessons and requested a longer uninterrupted learning stretch. Installed four original focused chapters after py-session-03-tool:

- Chapter 6, Decisions and Boolean logic: 10 missions, 120 XP, Branch Weaver. Checkpoint, and/or/not, thresholds, grouped policies, guarded returns, normalized commands, interval overlap, dispatcher decision boss.
- Chapter 7, Loops and accumulated state: 10 missions, 120 XP, Loop Wrangler. Repeated state, ranges, conditional counting, while/termination, overshoot, first divisor, break/continue, grids, bounded simulation, repeatable session-console boss.
- Chapter 8, Lists and sequences: 12 missions, 140 XP, Queue Keeper. Indexes/empty input, negative indexes, slices, append/pop, filters, enumerate, membership, sorting, copying/aliasing, comprehensions, clean queue report boss.
- Chapter 9, Dictionaries and records: 10 missions, 120 XP, Record Keeper. Records, get/defaults, mutation, presence, values/items, frequencies, record search, optional pop, structured inventory summary boss.

42 new missions / 500 XP; total nine chapters / 88 missions. New packages are content/python-decisions.json, python-repetition.json, python-lists.json and python-dictionaries.json. Stable sequential IDs use py-decisions-*, py-repetition-*, py-lists-* and py-dictionaries-*. Existing IDs/earned completion remain unchanged. All have minimal starter code, visible contracts and edge cases, three collapsed hints, behavioral cases and post-pass references with alternatives. Practice aims such as using a loop or comprehension are distinguished from automatically enforced behavior; valid alternatives pass. No repeated Your approach boilerplate. These are authoring-budget adaptations to David's prior experience rather than mandatory Boot.dev exercise counts.

Added 30 checked grimoire articles for the new concepts, for 47 total. They unlock at associated lesson completion, include related links/search aliases/pitfalls/examples, and remain offline. Existing entries cover revisited concepts. Reference content is external JSON; no live AI generation or API calls are involved.

Collection grading now supports unchanged_args (deep comparison of positional and keyword input values before/after), args_after (exact expected positional values after the call), and new_result (result cannot be the same object as a direct input argument). Every function case receives detached deep-copied inputs so a mutation cannot corrupt test fixtures or later runs. Tests assess requested mutation/non-mutation and fresh outer copies, not preferred syntax or automatic code quality. New objects can still share nested objects when the assignment permits shallow copying. src/runner.py and packaged dist/runner.py match. course_files.py validates new optional flags.

Verification: 26 Python methods pass, including every reference/test across 88 missions, unfinished-starter failure, grimoire article IDs/links/anchors, required mutation/no-op rejection, nested input preservation, fresh result versus alias, repeated fixture isolation and valid ordinary-loop alternatives. tests/learning-block-browser.mjs passed all 42 missions through actual Pyodide Test/Submit, boss Run, prerequisite/failure gating, all chapter boundaries, live comparisons, reload persistence, 500 XP, four badges, progressively unlocked reference pages, 47 final grimoire entries and narrow layout with no page errors. An intentionally incorrect in-place sort was rejected; the initial UI test expected only one of its two valid failure diagnostics, and that assertion was corrected before a full passing rerun. Updated the older session browser test to derive its next-mission expectation now that content follows it. Desktop save/close-preparation hooks pass. Chapter and reference screenshots reviewed.

Packaged and installed updated Syntaxia Service.exe; the Rust launcher did not need rebuilding. Archive runner bytes exactly match verified source; Syntaxia --check-report passes Rust/Tauri, nine chapters/88 missions. Before-learning-block SQLite and executable backups are in data/backups/. Actual 46 completions, drafts and snapshots match the backup; no real lesson was completed by QA. No key/settings reads or provider calls. Reopen Syntaxia to load the new service, then Up next leads to Choose the right status. Future core topics: sets/tuples, errors/validation, files and environments, testing/type hints, then objects/Pygame according to the broader plan. Continue authoring grimoire coverage alongside each new chapter.
## Session project, grimoire and accurate navigation - 2026-11-08

David completed all 43 previous missions. Installed Chapter 5, Project: session summary tool (content/python-session-project.json), with three milestones: summary_line report helper, collect_minutes input accumulator, and a full console program joining them. Prerequisite is py-num-12-boss; new IDs py-session-01-report, py-session-02-collect, py-session-03-tool. Total 50 XP and Session Scribe badge. Count is five chapters/46 missions. Open-ended assignments, collapsed tips and post-pass comparisons remain. The final program can be downloaded with Download .py; it is a console utility, not a native graphical runner, saved log or interactive menu. Numeric inputs are assumed valid. Lists, persistence, menus and robust validation remain future instruction. Next core block: Decisions and Boolean logic, adjusting to feedback.

Up next now derives from the first unlocked unfinished mission, names its chapter and provides a button. All installed missions completed shows All caught up, without promising nonexistent content. The old static loops/functions advertisement is removed.

Added header Grimoire button and a searchable reference dialog. Seventeen original short articles cover names, strings, input/conversion, arithmetic, division, remainder, formatting, comparisons, conditions, loops, accumulation, functions, arguments/defaults, return/None, scope, debugging and indentation/pass. Only articles anchored to a completed lesson appear. Each has examples, a pitfall, linked related concepts and Revisit lesson. Search includes aliases/operators; Back navigates article history; Close/Escape return to the editor without changing drafts. No AI/API-provider request is made to read the grimoire. External content/grimoire.json is read from beside the selected course catalog through /api/grimoire, so expanding reference text does not require rebuilding the EXE. Custom courses without that file get an empty grimoire. This implementation uses related-concept buttons rather than a general Markdown/wiki renderer.

Verification: 22 Python tests pass, including every reference against all cases, unfinished starters failing, and grimoire IDs/related links/lesson anchors. tests/session-browser.mjs passed all three milestones through actual Pyodide Run/Test/Submit with isolated prior completions, prior-boss navigation, prerequisite/failure gating, comparison/reload persistence, 50 XP and badge, 46 exported completions, dynamic next/all-caught-up states, search/no-results, article links/Back, hidden hints, draft preservation and narrow layout/Escape, without page errors. Desktop close/save regression hooks pass. Desktop/mobile grimoire screenshots reviewed. Rebuilt frontend and executable; packaged --check-report confirms five chapters/46 missions. Actual 43 learner completions, drafts and snapshots match before-grimoire backup. No user key/settings reads or actual provider calls. Prior EXE and SQLite backed up under data/backups/*before-grimoire*.
## Assignment design and extended path - 2026-11-08

David completed Scope, tracing and debugging and found it somewhat easy. He supplied ten Boot.dev screenshots, including an assignment with minimal starter code and optional collapsed Tips. Treat these as reference material for structure, not instructions to copy exercises or a mandatory career path.

This update supersedes the assumption that every planned foundation mission needs completing in a fixed sequence. Begin previously studied subjects with a short independent checkpoint. Offer targeted practice for gaps and let demonstrated fluency shorten repetition. Do not auto-award unseen lessons or assume the app already supports adaptive branching. New material still gets a concise explanation and a related example before independent work.

### Default lesson contract

1. Lesson: explain the concept with a related example that is not the exercise algorithm with renamed variables.
2. Assignment: state the result to produce in ordinary language. Specify required function signatures, inputs/returns, exact formatting only when relevant, edge cases and constraints. These define correctness and must remain visible.
3. Examples: show a representative input/output pair and a boundary case when useful. Do not embed a step-by-step solution in the examples.
4. Starter: usually a function signature and pass, or a short comment. Supply scaffolding only when it removes unrelated setup. Repairs and tracing remain useful exercise types but must not dominate an entire chapter for this learner.
5. Tips: optional, collapsed by default, from a conceptual nudge through an approach outline. Put algorithm choices, intermediate variable suggestions and step ordering here rather than in Assignment. Avoid dumping complete code. Opening tips costs nothing.
6. Tutor: hints first, no unsolicited full solution; full solutions only on explicit request. Post-pass reference comparison remains available.

Clear specifications are not excessive help. Never hide an assessed condition in Tips: empty input behavior, whether inputs may be modified, rounding rules, and a required technique or prohibited built-in belong in Assignment. Behavioral grading should accept reasonable alternatives; if a technique cannot be checked, disclose that it is a practice constraint rather than claiming automatic enforcement. Efficient is not synonymous with short.

The current application already has collapsed Offline hints with individually expandable hints. Use that existing hints field as the initial optional Tips mechanism. No new content field or desktop UI change was implemented for this planning update. Assignment requirements must become outcome/contract statements during future authoring; merely hiding today's entire requirements list would hide important rules. Do not silently rewrite completed missions, submitted code or reference history.

Example of the intended difficulty (original, not an installed mission): implement split_duration(total_seconds) for a non-negative integer, returning text in the form M minutes, S seconds; seconds must be between 0 and 59. Examples: 125 -> 2 minutes, 5 seconds; 0 -> 0 minutes, 0 seconds. Teach integer division/remainder in the lesson. Optional tips may identify quotient/remainder and suggest naming the two results; the assignment should not prescribe every statement. This is a diagnostic only after the operators have been introduced or prior familiarity checked.

### Broader learning path

The earlier chapter table is a flexible authoring budget, not 180 compulsory remedial tasks. Preserve grouped practice while increasing independent implementation and variation.

| Stage | Subjects | Application checkpoint |
| --- | --- | --- |
| Python foundations | Computing, comparisons/decisions, loops, lists, dictionaries, sets/tuples, errors, type hints; scope/functions already covered | Small independent console program |
| Development tools and saved data | Interpreter/virtual environment, modules, local debugging, Git, files/JSON, automated tests | Useful multi-file text analyzer or persistent inventory |
| Object-oriented Python and graphics | Objects, methods, composition, events, game loop, coordinates/time and collisions | Guided Pygame prototype followed by the small independent game capstone |
| Deeper Python and computer science | Pure functions and side effects, higher-order functions, practical recursion, data structures, algorithmic complexity | A text-processing/static-site tool; an API assistant is an optional alternative after API basics |
| Application and backend branch | HTTP clients and servers, SQL/SQLite, APIs, concurrency, security, packaging/deployment | A useful service connected to one of David's interests |
| Optional systems/language branch | C and memory management, JavaScript/TypeScript, Docker, pub/sub and other languages when a project needs them | A focused cross-language or deployment project |

The screenshots show a wider developer path, not just the beginner Python course. Core Python, Git, OOP, functional programming and algorithms fit the long-term direction. A repeat Linux course and a programming-job course are not requirements for David's hobby/collaboration goals. C memory management, JavaScript/TypeScript and backend deployment are optional branches rather than prerequisites for a Pygame game. Keep alternating instruction with finished, original applications. Choose later projects together; do not assume Boot.dev's named projects are commitments.

Current installed content: four chapters/43 missions. David completed the first 31. Numbers and comparisons is now authored and installed as Chapter 4, with 12 independently implemented assignments (one targeted repair), collapsed optional hints, 140 XP and the Number Navigator badge. Next authoring block: Decisions and Boolean logic. See STATUS.md for verification; later project mode remains planned.
# Python Workshop: continuation to a Pygame capstone

Updated 2026-11-08. This is the active curriculum from David's completion of the seven review missions and sixteen functions missions, as reported by David. The earlier subject plan is retained in CURRICULUM-2026-09-20.md for reference. Existing lesson IDs, submissions, XP and badges remain intact. Completion of this planning work does not install new chapters or award progress.

## Destination and teaching approach

Build an original small desktop game that David can run, explain, debug and extend. Proposed theme: Signal Runner, a top-down arcade game where a player collects signal beacons while avoiding moving interference. The theme can change before development; the small feature budget should not.

Use the structure in David's five Boot.dev outline screenshots: concentrated practice within a topic, checkpoints, then guided projects that apply what was learned. The screenshots are references for organization, not source lesson content. Their wider sequence includes tooling, OOP, a game, functional programming, algorithms and larger applications. We adapt that order to this learner rather than following the TypeScript backend track. No repeat Linux administration course is needed.

Each chapter stays with one topic. Start with reading and predicting, then modifying, independent implementation, debugging, and a small application. Use multiple variations before adding another concept. Revisit earlier skills in short recall tasks. Include optional explanations of why Python behaves that way. Tests check behavioral contracts; comparisons discuss clarity and tradeoffs without assuming shorter means faster. Hints first; complete answers only on request. No streaks, deadlines, hint costs or retry penalties.

Plan about 10-25 minutes for ordinary missions, with projects split into several sittings. Counts below are adjustable authoring budgets, not promises of installed content or a mastery score. Display numbering continues after the two completed chapters.

## The next route

| Chapter | Focus | Budget | Evidence / outcome |
| --- | --- | ---: | --- |
| 3 | Scope, tracing and debugging | 8 | Follow a value across calls and repair the calculation toolkit |
| 4 | Numbers and comparisons | 12 | Understand division/remainders, numeric formatting and boundary comparisons |
| 5 | Decisions and Boolean logic | 12 | A clear status classifier, including exact boundaries |
| 6 | Loops and accumulated state | 18 | A console guessing game with rounds and replay |
| 7 | Lists and sequences | 20 | A queue and score report with filtering and ordering |
| 8 | Dictionaries and records | 14 | A small equipment inventory with lookup and updates |
| 9 | Sets and tuples | 8 | Duplicate checks, coordinate pairs and unpacking |
| 10 | Errors and robust input | 12 | Recover from expected failures without hiding programming bugs |
| 11 | Local development, modules and Git | 10 labs | Run and debug a multi-file console application outside the workshop |
| 12 | Files, paths and JSON | 12 | Inventory with persistent storage and recovery |
| 13 | Tests, type hints and refactoring | 14 | Repeatable checks and clearly stated function contracts |
| 14 | Objects and composition | 14 | Model a few independent moving entities without a class hierarchy |
| 15 | Pygame fundamentals | 16 labs | A playable one-screen collect-and-dodge prototype |
| 16 | Independent game capstone | 10 milestones | A finished small game with instructions and tested core logic |

About 180 further missions/labs/milestones. We author and validate one chapter at a time; the full path is a direction, not a barrier to getting the next exercises. Strings, assignment and input receive targeted refreshers when needed rather than restarting the completed review.

## Chapter detail and prerequisites

### 3. Scope, tracing and debugging: the next chapter

1. Trace a caller's argument into a parameter and the result back out.
2. Reuse a local name in two functions and explain why the values stay separate.
3. Repair a local variable referenced outside its function.
4. Replace an accidental dependency on an outside name with a parameter.
5. Trace a chain of three small functions using intermediate values.
6. Read a short traceback and locate the relevant line; distinguish that from a wrong result.
7. Find the first incorrect intermediate value in a supplied trace, then repair the cause.
8. Boss: repair a multi-function session calculation toolkit and explain its data flow.

Avoid globals, closures, decorators and mutable defaults. Output-contract exercises can use the existing runner; prediction/explanation activities remain conversation prompts until there is a real assessment format for them. Do not fake automatic grading of explanations.

### 4-6. Computation, decisions and repetition

Computing: numeric conversion, operator precedence, units, / versus //, remainder, decimal display and rounding. Use valid numeric inputs until validation is taught. Brief string/f-string refreshers support messages; advanced formatting is unnecessary.

Comparisons and decisions: equality, ordering, if/else/elif, inclusive boundaries, and/or/not, grouped conditions, guard clauses and explicit returns. Practice several branch variations before combining conditions. Build a status classifier from fictional readings.

Loops: six missions on for/range and excluded endpoints; four on totals and counters; three on while and stopping; three on break/continue and debugging; two project milestones. Compare range with a manual counter for readability and error opportunities. Build a guessing game with supplied or seeded targets for repeatable tests; explicitly teach random before requiring it. Console interactive replay is a finite supplied-input script in the workshop, then becomes truly interactive during local labs.

### 7-10. Data and expected failures

Lists: construction, len/indexes/slices, append/pop/remove, empty input, direct iteration, enumerate, search/filter, sorted versus sort, aliasing/copying, one comprehension after the equivalent loop. Teach safe changes to a collection before using them in game entity lists.

Dictionaries: fields, updates, missing keys, get, membership, keys/values/items, pair unpacking, counting and lists of records. Build the inventory first in memory.

Sets first: uniqueness, membership, union/intersection/difference. Tuples afterward: coordinate pairs, unpacking and returning multiple related results. Do not alternate collection types every exercise.

Errors: syntax/runtime/logic differences; traceback reading; narrow ValueError handling; small try blocks; validation loops; cancellation; raising a useful exception; why blanket exception handling conceals defects. Add robust input to a previous console project.

### 11-13. Develop an actual application

Environment labs: identify the Python interpreter; open a project folder in VS Code; run a saved file; set a breakpoint and inspect locals; split modules; understand import-time execution and the main guard; create a project .venv; install a needed dependency through that interpreter; record dependencies; make and inspect Git commits; restore a deliberately broken practice edit. Teach the reason behind each command. Git is local first; a GitHub account is unnecessary.

Use native Windows for the initial graphical project. David's CachyOS laptop is a valid later target; WSL is optional and does not need to be introduced for this game. Each OS gets its own environment; transfer source and dependency declarations, not .venv folders. Select supported Python/Pygame versions and verify installation at the actual setup session.

Files: working directory versus paths, pathlib, UTF-8, with, overwrite/append, JSON roundtrip, missing/malformed data and safe replacement/backups. Work in a dedicated practice directory with sample data. Extend the inventory into a useful saved-data application before starting graphics.

Tests: assertions, normal and boundary cases, bug reproduction, separating logic from input/output, standard-library unittest, temporary-file checks, and refactoring with checks intact. Then simple annotations, collection types and optional results. Explain that hints do not enforce types at runtime. The durable inventory is the guided project between foundations and OOP.

### 14. Objects after functions and records

Instances, attributes, constructors, instance methods, self, independent state, composition, and choosing functions versus classes. Refactor a small record-based entity into a class only after its behavior is understood. Show how accidental shared state causes a bug. Prefer a player containing its state over deep inheritance. Dataclasses, inheritance and functional-programming depth can wait.

### 15. Pygame as a focused course

Sequence: environment smoke test; window and clean shutdown; event queue; drawing and coordinate system; continuous versus discrete input; game loop; elapsed-time movement; screen boundaries; Rect collisions; one collectible; score display; multiple objects; deterministic spawning for checks; start/play/game-over states; restart; prototype integration.

Start with colored shapes so asset creation cannot block learning. Explain events, update and drawing separately. Discuss time units and frame-rate-independent movement with visible experiments. Teach event handling before adding menu controls. Sound is optional and introduced only after a working silent game.

### 16. Capstone: Signal Runner (working title)

1. Write the rules, controls and acceptance checklist; choose one screen and one game mode.
2. Design a small folder layout and separate game rules from drawing/input.
3. Implement player motion and boundaries, with a short walkthrough.
4. Add collectibles and scoring.
5. Add one hazard type and clear collision behavior.
6. Add start, playing and game-over states plus restart.
7. Save a high score with missing/corrupt-file recovery.
8. Check core rules automatically; perform a manual graphics/input checklist.
9. Diagnose a seeded bug, improve a small section and make one independent feature change.
10. Deliver source, dependency list, launch instructions and a code walkthrough; optionally package a Windows executable afterward.

Definition of done: launches from a fresh project environment; controls are documented; input remains responsive; rounds can restart without relaunching; scoring follows the rules; quitting closes cleanly; broken high-score data is handled; core logic has meaningful tests. David can trace one input through update to display and explain where to change a rule.

Keep multiplayer, networking, a physics engine, procedural worlds, level editors, complex animation and live hardware integration outside the first capstone. Extensions are rewards after a finished base game.

## How external work fits the workshop

Current capability: the workshop editor runs Python in Pyodide. It does not inspect VS Code, read an external project, or run native Pygame. The tutor currently gets the active workshop lesson, editor text, visible results and recent conversation. A key/model connection test has passed, as reported by David; external project access remains unimplemented.

First bridge: keep instructions and tutor on one side, VS Code and the application's own window on the other. Save real source files, run/debug with the selected project interpreter, and paste relevant code/tracebacks into tutor chat when needed. This is enough to start local labs; it is not automatic file access. Larger multi-file questions may need this main chat until project context support exists.

Proposed workshop project mode (future implementation):

- Explicitly select a project folder and associate it with a project lesson; never infer a folder from the active desktop window.
- Provide Open folder / Open in VS Code, Run game and Run checks actions. Run only the selected project's configured interpreter and entry point, with a visible stop control and output capture. Local execution is a new capability beyond the current worker runner and needs its own implementation and validation.
- Offer Refresh project context. Read saved files from the selected folder, show the actual file list and size limits, then require Send to send that snapshot with the question. Do not continuously watch or transmit edits. Unsaved editor buffers are unavailable; remind the learner to save first.
- Include only approved source files and relevant test output. Exclude keys, .env, tutor settings, progress databases, .git, .venv, build output and large/binary assets. Resolve paths inside the chosen folder, including symlink checks. Do not collect unrelated desktop windows or credentials.
- Let the tutor discuss the snapshot and clearly identify stale or missing context. It cannot verify visual playability from source alone. No automatic file edits, execution or API calls by the tutor.
- Grade testable logic with local checks and graphics/feel with an honest manual checklist. Keep manual completion distinct from automatically verified behavior. Project milestones, passing snapshots and XP need explicit data support; do not pretend current single-file Submit handles projects.

Do not move Pygame into the browser editor just to keep one window. The transition to ordinary development tools is a learning objective, introduced on a simpler console project before the game. The workshop remains the lesson/progress/tutoring companion.

## Rewards, review and later branches

Keep 10 XP per validated ordinary coding mission, 30 per chapter boss, once only. Hints, retries and time away remain free. Define project milestone rewards when their completion mechanism is implemented. Proposed badges: Value Detective, Loop Wrangler, Collection Keeper, Local Developer and Game Builder. Do not grant badges just for reading this plan.

A checkpoint asks for a fresh working example, an explanation/trace, and a small repair or change. Add focused practice when understanding is shaky; shorten repetitive work when the learner demonstrates fluency without awarding unseen completions. Reuse radio, VR, printers and games as familiar themes, with ordinary examples too.

After the game: functional programming, practical algorithms/data structures, HTTP/API tools, SQLite, async/event-driven work, packaging and a guided reading/change task in one of David's existing applications. Other languages become separate tracks with their own execution/tooling support. Choose the next branch by curiosity and project needs.

## Authoring and implementation order

1. Author and verify Chapter 3 as the next installed block, then Chapter 4; keep existing IDs and data.
2. Add focused chapters in the order above, adjusting from David's feedback.
3. Implement the external-project bridge before Chapter 11 needs it, or use the explicit manual workflow while developing it. Do not delay foundation lessons on this integration.
4. Validate reference solutions, unfinished starters, boundary tests, prerequisite unlocks and persistence using isolated test data. Never complete real learner missions during QA.

Implementation update 2026-11-08: review, functions, and the eight-mission Scope, tracing and debugging chapter are installed (31 missions total). Chapter 3 is complete as authored content; learner completion is tracked separately. Numbers and comparisons is the next block to author. Later chapters and project mode remain planned.

Sources for later setup: https://www.pygame.org/wiki/GettingStarted ; https://www.pygame.org/docs/ ; https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/ . Verify current package/interpreter compatibility during setup.






