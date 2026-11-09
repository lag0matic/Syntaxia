from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
import shutil

from course_files import course_content, read_json
from lesson_updates import LessonUpdates, digest
from server import connect, initialize

ROOT = Path(__file__).resolve().parents[1]


class LessonUpdateTests(TestCase):
    def test_daily_check_manual_override_and_safe_install(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            content = root / 'content'
            shutil.copytree(ROOT / 'content', content)
            catalog = content / 'catalog.json'
            database = root / 'data' / 'workshop.sqlite3'
            initialize(database)
            with connect(database) as db:
                db.execute('INSERT INTO drafts VALUES (?, ?, ?, ?)', ('py-01-message', '# draft', 1, 'today'))
            updates = LessonUpdates(catalog, database, connect)
            self.assertTrue(updates.supported('python-workshop'))
            self.assertFalse(updates.supported('custom-course'))

            files = {name: (content / name).read_bytes() for name in course_content(catalog)}
            chapter = read_json(content / 'python-orientation.json')
            chapter['title'] = 'Updated introduction'
            files['python-orientation.json'] = json.dumps(chapter).encode()
            manifest = {'course': 'python-workshop', 'files': {name: digest(data) for name, data in files.items()}}

            def fetch(path, limit):
                return json.dumps(manifest).encode() if path == 'lesson-release.json' else files[path.removeprefix('content/')]

            with patch('lesson_updates.download', side_effect=fetch) as network:
                self.assertTrue(updates.check()['available'])
                restarted = LessonUpdates(catalog, database, connect)
                self.assertTrue(restarted.check()['available'])
                self.assertEqual(network.call_count, 1)
                self.assertTrue(restarted.check(manual=True)['available'])
                self.assertEqual(network.call_count, 2)

                good = files['python-orientation.json']
                files['python-orientation.json'] = b'bad download'
                with self.assertRaisesRegex(ValueError, 'changed during download'):
                    restarted.install()
                self.assertNotEqual(read_json(content / 'python-orientation.json')['title'], chapter['title'])
                files['python-orientation.json'] = good
                self.assertTrue(restarted.install()['installed'])
                self.assertEqual(read_json(content / 'python-orientation.json')['title'], chapter['title'])
                self.assertFalse(restarted.check(manual=True)['available'])

            with connect(database) as db:
                self.assertEqual(db.execute('SELECT code FROM drafts').fetchone()['code'], '# draft')
            self.assertEqual(len(list((root / 'data' / 'lesson-backups').glob('*/content/catalog.json'))), 1)

    def test_rejects_unexpected_paths_and_caches_failed_automatic_checks(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / 'data' / 'workshop.sqlite3'
            initialize(database)
            updates = LessonUpdates(root / 'content' / 'catalog.json', database, connect)
            bad = {'course': 'python-workshop', 'files': {'catalog.json': '0' * 64, '../data/workshop.sqlite3': '0' * 64}}
            with patch('lesson_updates.download', return_value=json.dumps(bad).encode()) as network:
                with self.assertRaisesRegex(ValueError, 'Unexpected lesson update filename'):
                    updates.check()
                self.assertTrue(updates.check()['failed'])
                self.assertEqual(network.call_count, 1)

