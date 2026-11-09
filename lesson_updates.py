"""Check and install content-only updates from the public Syntaxia repository."""
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from threading import Lock
from urllib.request import Request, urlopen

from course_files import course_content, load_catalog, read_json

REPOSITORY = 'https://raw.githubusercontent.com/lag0matic/Syntaxia/main/'
COURSE_ID = 'python-workshop'
MAX_FILE = 3 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def download(path, limit):
    request = Request(REPOSITORY + path, headers={'User-Agent': 'Syntaxia-Lessons'})
    with urlopen(request, timeout=10) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('A lesson update file is too large.')
    return data


def manifest_files(document):
    if not isinstance(document, dict) or document.get('course') != COURSE_ID:
        raise ValueError('The lesson update belongs to a different course.')
    files = document.get('files')
    if not isinstance(files, dict) or len(files) > 256 or 'catalog.json' not in files:
        raise ValueError('Invalid lesson update manifest.')
    for name, checksum in files.items():
        if not re.fullmatch(r'(?:[a-zA-Z0-9_-]+\.json|badges/[a-zA-Z0-9_-]+\.png)', name):
            raise ValueError('Unexpected lesson update filename.')
        if not isinstance(checksum, str) or not re.fullmatch(r'[a-f0-9]{64}', checksum):
            raise ValueError('Invalid lesson update checksum.')
    return files


class LessonUpdates:
    def __init__(self, catalog, database, connect):
        self.catalog = Path(catalog).resolve()
        self.database = Path(database).resolve()
        self.connect = connect
        self.lock = Lock()

    def supported(self, course_id):
        return (
            course_id == COURSE_ID
            and self.catalog.name == 'catalog.json'
            and self.catalog.parent == self.database.parent.parent / 'content'
            and self.database.name == 'workshop.sqlite3'
            and self.database.parent.name == 'data'
        )

    def state(self):
        with self.connect(self.database) as db:
            row = db.execute('SELECT checked, pending, successful FROM lesson_updates WHERE id = 1').fetchone()
        return (row['checked'], json.loads(row['pending']), bool(row['successful'])) if row else ('', None, False)

    def save(self, checked, pending, successful):
        with self.connect(self.database) as db:
            db.execute('INSERT OR REPLACE INTO lesson_updates VALUES (1, ?, ?, ?)',
                       (checked, json.dumps(pending), successful))

    def local_file(self, name):
        path = self.catalog.parent / name
        if not path.resolve().is_relative_to(self.catalog.parent):
            return None
        try:
            with path.open('rb') as file:
                return file.read(MAX_FILE + 1)
        except FileNotFoundError:
            return None

    def check(self, manual=False):
        with self.lock:
            today = date.today().isoformat()
            checked, pending, successful = self.state()
            if not manual and checked == today:
                return {'available': bool(pending), 'checked': checked, 'failed': not successful}
            self.save(today, pending, False)
            document = json.loads(download('lesson-release.json', 64 * 1024))
            files = manifest_files(document)
            pending = files if any(digest(self.local_file(name) or b'') != checksum
                                   for name, checksum in files.items()) else None
            self.save(today, pending, True)
            return {'available': bool(pending), 'checked': today}

    def install(self):
        with self.lock:
            checked, pending, successful = self.state()
            if not pending:
                raise ValueError('Check for new lessons before installing.')
            root = self.catalog.parent
            backup_dir = self.database.parent / 'lesson-backups'
            backup_dir.mkdir(exist_ok=True)
            with TemporaryDirectory(prefix='.lesson-update-', dir=root.parent) as temp:
                stage = Path(temp) / 'content'
                stage.mkdir()
                total = 0
                for name, checksum in pending.items():
                    data = self.local_file(name)
                    if data is None or digest(data) != checksum:
                        data = download('content/' + name, MAX_FILE)
                    if digest(data) != checksum:
                        raise ValueError('The lesson files changed during download. Check again and retry.')
                    total += len(data)
                    if total > MAX_TOTAL:
                        raise ValueError('The lesson update is too large.')
                    if name.endswith('.png') and not data.startswith(b'\x89PNG\r\n\x1a\n'):
                        raise ValueError('A lesson update badge is not a PNG.')
                    path = stage / name
                    path.parent.mkdir(exist_ok=True)
                    path.write_bytes(data)
                catalog = stage / 'catalog.json'
                if load_catalog(catalog)['id'] != COURSE_ID or set(course_content(catalog)) != set(pending):
                    raise ValueError('The downloaded lesson catalog is incomplete.')
                if 'grimoire.json' in pending:
                    grimoire = read_json(stage / 'grimoire.json')
                    if not isinstance(grimoire, dict) or not isinstance(grimoire.get('entries'), list):
                        raise ValueError('The downloaded Grimoire is invalid.')
                backup = Path(mkdtemp(prefix='content-', dir=backup_dir)) / 'content'
                root.rename(backup)
                try:
                    stage.rename(root)
                except OSError:
                    backup.rename(root)
                    raise
            self.save(checked, None, successful)
            return {'installed': True}


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    catalog = root / 'content' / 'catalog.json'
    chapters = load_catalog(catalog)['chapters']
    files = {name: digest((catalog.parent / name).read_bytes()) for name in course_content(catalog)}
    if any('badges/' + chapter['id'] + '.png' not in files for chapter in chapters):
        raise SystemExit('Every published chapter needs its badge artwork.')
    document = {'course': COURSE_ID, 'files': files}
    manifest_files(document)
    (root / 'lesson-release.json').write_text(json.dumps(document, indent=2, sort_keys=True) + '\n', encoding='utf-8')

