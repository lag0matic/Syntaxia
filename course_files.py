"""Versioned, data-only course files. No lesson Python runs on the host."""
import json
import re
from dataclasses import dataclass
from pathlib import Path


class CourseError(ValueError):
    pass


def read_json(path):
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as error:
        raise CourseError(f'{path.name}, line {error.lineno}: {error.msg}') from error
    except (OSError, UnicodeError) as error:
        raise CourseError(f'Cannot read {path}: {error}') from error


def relative_path(root, value, label):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise CourseError(f'{label} must be a relative path inside the course folder.')
    target = (root / value).resolve()
    if not target.is_relative_to(root.resolve()):
        raise CourseError(f'{label} must stay inside the course folder.')
    return target


@dataclass(frozen=True)
class CourseFiles:
    descriptor: Path
    catalog: Path
    database: Path


def open_course(path):
    path = Path(path).resolve()
    document = read_json(path)
    if not isinstance(document, dict) or document.get('format') != 'python-workshop-course' or document.get('version') != 1:
        raise CourseError('Expected a python-workshop-course file with version 1.')
    catalog = relative_path(path.parent, document.get('catalog'), 'catalog')
    database = relative_path(path.parent, document.get('progress'), 'progress')
    if database.suffix != '.sqlite3' or database == catalog:
        raise CourseError('progress must name a separate .sqlite3 database file.')
    load_catalog(catalog)
    return CourseFiles(path, catalog, database)


def require(condition, message):
    if not condition:
        raise CourseError(message)


def load_catalog(path):
    path = Path(path).resolve()
    manifest = read_json(path)
    require(isinstance(manifest, dict), f'{path.name}: expected a JSON object.')
    require(manifest.get('format_version', 1) == 1, f'{path.name}: unsupported format_version.')
    require(isinstance(manifest.get('id'), str) and isinstance(manifest.get('title'), str), f'{path.name}: id and title are required.')
    require(isinstance(manifest.get('chapters'), list) and manifest['chapters'], f'{path.name}: chapters must be a nonempty list of filenames.')
    chapters, missions, seen, chapter_ids = [], [], set(), set()
    for filename in manifest['chapters']:
        chapter_path = relative_path(path.parent, filename, 'chapter filename')
        require(chapter_path.parent == path.parent, 'Chapter files must live directly beside catalog.json.')
        chapter = read_json(chapter_path)
        label = str(filename)
        require(isinstance(chapter, dict), f'{label}: expected a JSON object.')
        for key in ('id', 'title', 'language', 'badge'):
            require(isinstance(chapter.get(key), str) and chapter[key], f'{label}: {key} must be nonempty text.')
        require(chapter['id'] not in chapter_ids, f'{label}: duplicate chapter ID {chapter["id"]}.')
        chapter_ids.add(chapter['id'])
        require(chapter['language'] == 'python', f'{label}: this launcher supports Python lessons only.')
        require(isinstance(chapter.get('missions'), list) and chapter['missions'], f'{label}: missions must be a nonempty list.')
        chapter_missions = chapter.pop('missions')
        chapter['mission_ids'] = []
        for mission in chapter_missions:
            require(isinstance(mission, dict), f'{label}: each mission must be an object.')
            for key in ('id', 'title', 'concepts', 'brief', 'starter', 'example', 'input'):
                require(isinstance(mission.get(key), str), f'{label}: mission {key} must be text.')
            mid = mission['id']
            require(bool(mid) and all(c.isalnum() or c in '-_' for c in mid), f'{label}: invalid mission ID {mid!r}.')
            require(mid not in seen, f'{label}: duplicate mission ID {mid}. Keep existing IDs stable.')
            for key in ('version', 'xp'):
                require(type(mission.get(key)) is int and mission[key] > 0, f'{mid}: {key} must be a positive integer.')
            prerequisites = mission.get('prerequisites', [])
            require(isinstance(prerequisites, list) and all(isinstance(p, str) for p in prerequisites), f'{mid}: prerequisites must be a list of IDs.')
            require(set(prerequisites) <= seen, f'{mid}: prerequisites must refer to earlier missions. Check removed or reordered lessons.')
            for key in ('requirements', 'hints'):
                require(isinstance(mission.get(key), list) and all(isinstance(s, str) for s in mission[key]), f'{mid}: {key} must be a list of text.')
            require(isinstance(mission.get('lesson'), list) and mission['lesson'], f'{mid}: lesson must contain explanation sections.')
            for section in mission['lesson']:
                require(isinstance(section, dict) and isinstance(section.get('heading'), str) and isinstance(section.get('text'), str), f'{mid}: lesson sections need heading and text.')
                require('code' not in section or isinstance(section['code'], str), f'{mid}: example code must be text.')
            require(isinstance(mission.get('tests'), list) and mission['tests'], f'{mid}: tests must be a nonempty list.')
            for case in mission['tests']:
                require(isinstance(case, dict) and isinstance(case.get('label'), str) and type(case.get('public')) is bool, f'{mid}: tests need a label and public boolean.')
                require('function' in case or isinstance(case.get('stdout'), str), f'{mid}: each test needs function or stdout.')
                if 'function' in case:
                    require(isinstance(case['function'], str) and 'expected' in case, f'{mid}: function tests need a name and expected value.')
                    require(isinstance(case.get('args', []), list) and isinstance(case.get('kwargs', {}), dict), f'{mid}: invalid test arguments.')
                require(isinstance(case.get('stdin', []), list) and all(isinstance(s, str) for s in case.get('stdin', [])), f'{mid}: stdin must be a list of text lines.')
                require('unchanged_args' not in case or type(case['unchanged_args']) is bool, f'{mid}: unchanged_args must be boolean.')
                require('new_result' not in case or type(case['new_result']) is bool, f'{mid}: new_result must be boolean.')
                require('args_after' not in case or isinstance(case['args_after'], list), f'{mid}: args_after must be a list.')
                require('call_stdout' not in case or isinstance(case['call_stdout'], str), f'{mid}: call_stdout must be text.')
            require(any(c['public'] for c in mission['tests']), f'{mid}: include at least one public test.')
            if 'reference' in mission:
                ref = mission['reference']
                require(isinstance(ref, dict) and isinstance(ref.get('code'), str) and isinstance(ref.get('notes'), list) and all(isinstance(s, str) for s in ref['notes']), f'{mid}: reference needs code and text notes.')
            seen.add(mid)
            chapter['mission_ids'].append(mid)
            missions.append({**mission, 'prerequisites': prerequisites, 'chapter': chapter['id'], 'language': chapter['language']})
        chapters.append(chapter)
    return {**manifest, 'chapters': chapters, 'missions': missions}


def badge_path(catalog, chapter_id):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', chapter_id):
        return None
    root = Path(catalog).resolve().parent
    badge = root / 'badges' / f'{chapter_id}.png'
    return badge if badge.resolve().parent == root / 'badges' else None


def course_content(catalog):
    """Files needed to publish one complete course, relative to its catalog folder."""
    root = Path(catalog).resolve().parent
    manifest = read_json(catalog)
    chapters = load_catalog(catalog)['chapters']
    files = [Path(catalog).name, *manifest['chapters']]
    if (root / 'grimoire.json').is_file():
        files.append('grimoire.json')
    for chapter in chapters:
        badge = badge_path(catalog, chapter['id'])
        if badge and badge.is_file():
            files.append(badge.relative_to(root).as_posix())
    return files
