import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from course_files import CourseError, open_course, load_catalog
from desktop import CourseLock


class ExternalCourseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / 'content', self.root / 'content')
        self.file = self.root / 'workshop.course.json'
        shutil.copy2(ROOT / 'workshop.course.json', self.file)

    def tearDown(self):
        self.temp.cleanup()

    def test_external_course_paths_and_validation(self):
        course = open_course(self.file)
        self.assertEqual(course.database, self.root / 'data/workshop.sqlite3')
        self.assertEqual(len(load_catalog(course.catalog)['missions']), 89)
        descriptor = json.loads(self.file.read_text())
        for key in ('catalog', 'progress'):
            self.file.write_text(json.dumps({**descriptor, key: '../outside.json'}))
            with self.assertRaises(CourseError):
                open_course(self.file)

    def test_rewrite_remove_restore_and_invalid_dependencies(self):
        course = open_course(self.file)
        chapter_path = self.root / 'content/python-review.json'
        chapter = json.loads(chapter_path.read_text(encoding='utf-8'))
        chapter['missions'][0]['title'] = 'Updated explanation'
        chapter_path.write_text(json.dumps(chapter))
        self.assertEqual(next(m for m in load_catalog(course.catalog)['missions'] if m['id'] == 'py-01-message')['title'], 'Updated explanation')
        manifest = json.loads(course.catalog.read_text())
        course.catalog.write_text(json.dumps({**manifest, 'chapters': ['python-review.json']}))
        self.assertEqual(len(load_catalog(course.catalog)['missions']), 7)
        course.catalog.write_text(json.dumps({**manifest, 'chapters': ['python-functions.json']}))
        with self.assertRaisesRegex(CourseError, 'prerequisites'):
            load_catalog(course.catalog)
        course.catalog.write_text(json.dumps(manifest))
        self.assertEqual(len(load_catalog(course.catalog)['missions']), 89)
        chapter['missions'][1]['id'] = chapter['missions'][0]['id']
        chapter_path.write_text(json.dumps(chapter))
        with self.assertRaisesRegex(CourseError, 'duplicate mission'):
            load_catalog(course.catalog)

    def test_only_one_desktop_per_database_and_reopen(self):
        database = self.root / 'data/progress.sqlite3'
        first = CourseLock(database)
        try:
            with self.assertRaises(RuntimeError):
                CourseLock(database)
        finally:
            first.close()
        CourseLock(database).close()


if __name__ == '__main__':
    unittest.main()
