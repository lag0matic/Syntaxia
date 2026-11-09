## Chapter badge artwork and lesson updates

Every new chapter gets a Journey icon. Create a transparent square PNG at
`content/badges/<chapter-id>.png` using the chapter JSON's stable `id`. Use the
existing Grimoire and badges as style references. Match their painted fantasy
inventory style with brass, violet and warm parchment. Keep the silhouette
distinct at 54 px. Check that Journey shows it on an earned and an unfinished
chapter before publishing.

After changing lessons, Grimoire entries or badge artwork, run
`python lesson_updates.py` from the project folder. It rebuilds
`lesson-release.json` and requires artwork for every published chapter.
Commit the manifest and the content together to `main`. Syntaxia checks the
public manifest once per local calendar day while open. The Settings check
can be used any time. Installing a lesson update keeps the prior content
under `data/lesson-backups` and preserves the learner database.

## Inline syntax and optional orientation - 2026-11-08

Wrap every literal Python identifier, keyword, call, operator, value and expression in prose in single backticks, for example `and` and `low <= value <= high`. This applies to lesson headings/text, concepts, goals, requirements, hints, reference notes and grimoire prose. Ordinary English conjunctions remain unmarked. Keep standalone snippets, starter/reference source, program input and expected output in their existing plain code fields. The renderer supports code spans only, not full Markdown or HTML. Never alter test data or XP when applying visual markup.

The optional orientation chapter/mission has orientation: true. It appears first for new learners without becoming a prerequisite for previously installed material. Main chapter numbering ignores it. Up next skips unfinished orientation after the learner has a main-course completion. Add first-use grimoire anchors as early as a concept is genuinely taught; later articles can link back to those basics.
## Collection test contracts - 2026-11-08

Function cases now accept optional unchanged_args: true to check that positional and keyword inputs have equal values after the call; args_after: [...] to specify expected positional input values after intentional mutation; and new_result: true to reject returning the same direct input object when a fresh result is required. new_result concerns outer-object identity, not recursive independence. Put these requirements in the visible assignment contract. All function arguments are deep-copied per test case so fixtures are not changed by learner code. Existing cases need no changes. Use these flags for observable behavior rather than constraining one syntax. Include empty inputs, duplicates, exact boundaries and relevant nested mutation tests. See tests/test_collection_contracts.py and the lists/dictionaries packages for examples.
## Grimoire authoring agreement - 2026-11-08

David confirmed the intended behavior: author and check grimoire entries alongside each new chapter, then reveal them automatically when their associated lessons are completed. Do not generate reference articles live from learner submissions or AI conversations. A new chapter is not ready until its newly introduced concepts have useful reference coverage, examples, common pitfalls, search aliases and relevant concept links. Reuse existing articles where concepts are revisited instead of duplicating them. Verify lesson anchors and links; opening the grimoire remains free, offline and independent of API access. It is a quick memory aid, not a mastery requirement or penalty for forgetting. Earlier completed lessons keep their unlocked references.
## Grimoire content - 2026-11-08

Optional content/grimoire.json sits beside the course catalog (also for custom external courses). Shape: version: 1, entries: an array. Each article has stable id, title, mission (a valid lesson ID that must be completed before display), text (array of paragraphs), code (plain example string), pitfall (plain string), related (array of other article IDs), aliases (array of search words). Examples explain concepts without giving away uncompleted exercise solutions. UI renders plain text safely and linked related-concept buttons. Add/update articles in the JSON without rebuilding the EXE; reopen Grimoire to fetch current content. Run tests/test_grimoire.py to check references. Keep old IDs stable and repair links when removing an article. Missing/unreadable grimoire files return an empty entries list. The grimoire does not send reference browsing to the AI provider or edit learner code.
## Assignment style update - 2026-11-08

David requests a clear goal and optional approach guidance, as illustrated by the newer Boot.dev screenshots. For future lessons, requirements define behavior, signatures, edge cases and constraints; avoid implementation recipes there. Keep required rules visible. Put step ordering, suggested intermediate names and algorithm nudges in hints, already collapsed under Offline hints. Minimal signatures/pass are preferred for independent tasks; targeted repair missions remain useful but should not dominate chapters. Do not merely hide the whole requirements list. Use original examples and evaluate behavioral contracts without claiming tests assess understanding or enforce untested technique choices. Begin previously studied subjects with a small independent checkpoint and adjust practice depth manually until real branching support exists. See CURRICULUM.md's latest assignment-design section. Existing completed content and progress are preserved; this is an authoring-policy update, not a runtime change.
# Adding chapters without losing progress

## Desktop course format (version 1)

The launcher reads `workshop.course.json` beside the EXE, or a descriptor supplied by drag-and-drop or the Course menu:

```json
{
  "format": "python-workshop-course",
  "version": 1,
  "catalog": "content/catalog.json",
  "progress": "data/workshop.sqlite3"
}
```

Paths are relative to the descriptor and must remain inside its folder. The catalog uses `format_version: 1`. Chapters are separate JSON files beside the catalog. These are data files: lessons do not execute host code. `course_files.py` validates structure, IDs, supported language and prerequisite order before loading.

To add lessons, write a chapter file and register it in the catalog. To rewrite a lesson, edit its JSON while retaining its ID. To remove a chapter, remove its catalog entry and repair any prerequisites that point to it. Saved work remains in the database even when its lesson is absent; restoring the same ID makes that work available again. Existing completions remain earned when content is revised. Never reuse an old ID for an unrelated exercise.

Choose **Course → Reload lessons**, or restart the desktop app, after editing. Invalid files produce a readable error; menu reload keeps the current lesson open. No EXE rebuild is required for lessons, tests, hints, reference solutions, chapter order, or badges. New runtime capabilities and language support require an app update.

The course manifest is `content/catalog.json`. Each entry in its `chapters` array is a JSON filename in that same folder, loaded in order. Add a new package and append its filename; the frontend automatically renders the additional chapter and calculates its progress. There is no frontend rebuild for content-only changes.

Copy the *structure* of `python-review.json`, not its IDs or solutions. Preserve old mission IDs forever: drafts, completions, and snapshots are keyed by those IDs. Adding content never requires deleting or recreating the database. The server rejects duplicate mission IDs and prerequisites that do not refer to earlier missions.

## Teaching pace (David's feedback, 2026-09-17)

The initial seven-mission chapter is a broad review, not the template for future chapter pacing. Stay with one central topic across multiple related exercises. Progress from recognition/tracing to small code changes, independent writing, debugging, edge cases, and a practical application. Revisit earlier concepts in later chapters without introducing several new concepts in one mission. Split lists, dictionaries, and sets into separate teaching units where needed.

Boot.dev screenshots supplied by David illustrate the desired topic grouping and amount of practice (for example, 16 variable exercises, 17 functions, 15 loops, 24 lists). Use them as pacing references, not content to reproduce or mandatory counts. Write original exercises tied to David's interests. Keep projects as milestones after sufficient practice. Adjust depth based on demonstrated understanding and feedback.

## Chapter fields

- `id`: stable unique chapter ID.
- `title`: human-readable title.
- `language`: currently `python`. Future languages require implementing and registering a real runner in `src/app.js`; changing this field alone is insufficient.
- `version`: positive content version.
- `badge`: earned when all chapter missions are complete.
- `missions`: ordered mission objects.

## Mission fields

- `id`, `version`, `title`, `xp`, and `prerequisites` (array of earlier mission IDs).
- `concepts`: short list of the actual concepts covered.
- `lesson`: objects with `heading`, `text`, and optional illustrative `code`. Use a related example, not the exercise solution.
- `brief`, `requirements` (array of explicit statements), and `example` (plain text).
- `starter`: executable Python text or comments with scaffolding; avoid giving the answer away.
- `input`: newline-separated sample answers for manual Run.
- `hints`: ordered gentle-to-specific nudges; no complete solution.
- `tests`: behavioral cases. Set `public: true` for Test examples; all cases run on Submit. Extra cases must follow the stated requirements, never introduce surprise requirements.
- Optional `boss: true` for a chapter project.
- `reference`: an object with `code` (a clear, idiomatic passing solution) and `notes` (an array explaining the choices, alternatives, and relevant tradeoffs). References are withheld from bootstrap and retrieved only after completion. Use concepts already taught; do not equate fewer lines or a specific construct with universal speed superiority. Verify reference code against every mission test.

Each test has `label`, `public`, and `hint`. Script tests have `stdin` (array of strings), `stdout` (expected output), and optionally `variables` (expected top-level values). Function tests have `function`, `args`, and `expected`; optional `stdin` supplies answers consumed by top-level script code before the function is called. Each case starts with fresh program globals. Output comparison normalizes CRLF and final newlines, but otherwise compares exactly. Function cases compare returned values, not printed output.

Function cases can also supply `kwargs` (a dictionary of named arguments) and `call_stdout` (expected output produced by that function call alone). An empty `call_stdout` requires the helper not to print, while allowing top-level sample calls to print during Run. Use these to distinguish returned results from screen output and to verify default/keyword argument behavior. The functions chapter uses both features.

Keep precise output formatting only where it teaches a useful, explicit contract. Expand the harness for future structured-data tasks rather than forcing everything into text comparisons.

## Publishing a lesson locally

1. Back up progress before changing the course.
2. Write the lesson package and register it in the manifest.
3. Add reference solutions to the non-served test fixtures. Verify all cases pass and unfinished starters do not.
4. Check every concept needed by the exercise has been introduced.
5. Run the curriculum/backend tests and relevant browser checks.
6. Reload the browser; verify existing completion is retained and the new chapter appears.
7. Update STATUS.md with what is available and the next teaching objective.

Changing a mission's version does not revoke earlier completion. Existing completion records retain their submitted version and original source. A major rewrite should use a new ID; do not reuse an old ID for a different assignment.

The first version's automatic rewards cover completion only. Explanation quality, optional extensions, and code quality need human/tutor assessment; do not pretend a passing output check assesses these.





