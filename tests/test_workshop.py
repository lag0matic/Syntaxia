import hashlib
import importlib.util
import json
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import catalog, make_server

spec = importlib.util.spec_from_file_location('runner', ROOT / 'src' / 'runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class CurriculumTests(unittest.TestCase):
    def test_functions_chapter_before_registration(self):
        chapter = json.loads((ROOT / 'content/python-functions.json').read_text(encoding='utf-8'))
        self.assertEqual(len(chapter['missions']), 16)
        for mission in chapter['missions']:
            results = [runner.execute_case(mission['reference']['code'], case) for case in mission['tests']]
            self.assertTrue(all(r['passed'] for r in results), (mission['id'], results))
            self.assertFalse(all(runner.execute_case(mission['starter'], case)['passed'] for case in mission['tests']), mission['id'])
            self.assertTrue(any(case['public'] for case in mission['tests']))
            self.assertEqual(len(mission['hints']), 3)

    def test_function_call_output_and_keywords(self):
        case = {'function': 'with_setup', 'args': [30], 'kwargs': {'setup': 0}, 'expected': 30, 'call_stdout': ''}
        self.assertTrue(runner.execute_case('def with_setup(minutes, setup=5):\n    return minutes + setup', case)['passed'])
        self.assertFalse(runner.execute_case('def with_setup(minutes, setup=5):\n    print(minutes + setup)', case)['passed'])
        self.assertFalse(runner.execute_case('def with_setup(minutes, setup=5):\n    print("noise")\n    return minutes + setup', case)['passed'])
        self.assertFalse(runner.execute_case('def with_setup(minutes):\n    return minutes', case)['passed'])

    def test_failed_checks_show_exact_sample_inputs(self):
        mission = next(m for m in catalog()['missions'] if m['id'] == 'py-decisions-08-choices')
        request = {
            'mode': 'submit',
            'code': "def is_direction(command): return 'east' in command or command.strip().lower() in ('north', 'south', 'west')",
            'tests': mission['tests'],
        }
        results = json.loads(runner.run_request(json.dumps(request)))['results']
        self.assertEqual(results[4]['sample_input'], "is_direction('east west')")
        self.assertTrue(results[0]['passed'])
        self.assertNotIn('sample_input', results[0])

        request['code'] = 'raise ValueError("check failed")'
        request['tests'] = [
            {'label': 'program input', 'stdin': ['  ', '', 'north']},
            {'label': 'function arguments', 'function': 'pick', 'args': [[True, None]], 'kwargs': {'default': ''}},
        ]
        results = json.loads(runner.run_request(json.dumps(request)))['results']
        self.assertIn('ValueError', results[0]['error'])
        self.assertEqual(results[0]['sample_input'].splitlines()[1:], ["'  '", "''", "'north'"])
        self.assertEqual(results[1]['sample_input'], "pick([True, None], **{'default': ''})")

    def test_all_reference_solutions_and_starters(self):
        solutions = json.loads((ROOT / 'tests' / 'solutions.json').read_text())
        seen = set()
        for mission in catalog()['missions']:
            self.assertNotIn(mission['id'], seen)
            self.assertTrue(set(mission['prerequisites']) <= seen)
            seen.add(mission['id'])
            for case in mission['tests']:
                with self.subTest(mission=mission['id'], case=case['label']):
                    self.assertTrue(runner.execute_case(solutions[mission['id']], case)['passed'])
                    self.assertTrue(runner.execute_case(mission['reference']['code'], case)['passed'])
            self.assertFalse(all(runner.execute_case(mission['starter'], case)['passed'] for case in mission['tests']))

    def test_errors_and_output_limit(self):
        for source, expected in [("print(input())", 'Not enough program input'), ('if True print(1)', 'SyntaxError'), ('while True: print("x" * 1000)', 'Output limit reached')]:
            result = runner.execute_case(source, {})
            self.assertFalse(result['passed'])
            self.assertIn(expected, result['error'])


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = make_server(port=0, database=Path(self.temp.name) / 'test.sqlite3')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def request(self, path, body=None, headers=None):
        supplied = {'X-Workshop-Token': self.server.token, **(headers or {})}
        request = Request(self.url + path, data=json.dumps(body).encode() if body is not None else None, headers=supplied)
        try:
            with urlopen(request) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def test_draft_conflict_reset_restore_and_completion(self):
        mid = 'py-01-message'
        self.assertEqual(self.request('/api/reference/' + mid)[0], 403)
        self.assertTrue(all('reference' not in m for m in self.request('/api/bootstrap')[1]['course']['missions']))
        status, saved = self.request('/api/save', {'mission': mid, 'code': 'my draft', 'revision': 0})
        self.assertEqual(status, 200)
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(self.request('/api/save', {'mission': mid, 'code': 'stale', 'revision': 0})[0], 409)
        status, reset = self.request('/api/reset', {'mission': mid, 'code': 'my draft', 'revision': 1})
        self.assertEqual(status, 200)
        status, restored = self.request('/api/restore', {'mission': mid, 'code': reset['code'], 'revision': 2})
        self.assertEqual(restored['code'], 'my draft')
        source = "tool_name = 'Session tracker'\nprint(f'Building: {tool_name}')"
        submission = {'mission': mid, 'code': source, 'revision': 3, 'passed': 1, 'version': 1, 'digest': hashlib.sha256(source.encode()).hexdigest()}
        self.assertEqual(self.request('/api/submit', {**submission, 'digest': 'incorrect'})[0], 400)
        status, first = self.request('/api/submit', submission)
        self.assertEqual(status, 200)
        second_source = source + '\n# revised passing submission'
        status, second = self.request('/api/submit', {**submission, 'revision': 4, 'code': second_source, 'digest': hashlib.sha256(second_source.encode()).hexdigest()})
        self.assertEqual(len(second['state']['completions']), 1)
        self.assertEqual(first['state']['completions'], second['state']['completions'])
        status, comparison = self.request('/api/reference/' + mid)
        self.assertEqual(status, 200)
        self.assertEqual(comparison['submitted_code'], second_source)
        self.assertTrue(comparison['reference']['notes'])
        self.request('/api/save', {'mission': mid, 'code': 'unfinished draft', 'revision': 5})
        self.assertEqual(self.request('/api/reference/' + mid)[1]['submitted_code'], second_source)
        export = self.request('/api/export')[1]
        self.assertEqual(len(export['snapshots']), 4)

    def test_request_guards_and_prerequisites(self):
        body = {'mission': 'py-02-arithmetic', 'code': 'x', 'revision': 0, 'passed': 1, 'version': 1, 'digest': hashlib.sha256(b'x').hexdigest()}
        self.assertEqual(self.request('/api/submit', body)[0], 400)
        self.assertEqual(self.request('/api/save', body, {'Origin': 'http://unrelated.example'})[0], 403)
        self.assertEqual(self.request('/api/save', body, {'X-Workshop-Token': 'wrong'})[0], 403)
        self.assertEqual(self.request('/api/bootstrap', headers={'Host': 'unrelated.example'})[0], 403)
        self.assertEqual(self.request('/api/save', {**body, 'code': 7})[0], 400)

    def test_new_chapter_preserves_saved_work(self):
        mid = 'py-01-message'
        self.request('/api/save', {'mission': mid, 'code': 'existing draft', 'revision': 0})
        content = Path(self.temp.name) / 'content'
        content.mkdir()
        original = json.loads((ROOT / 'content' / 'python-review.json').read_text())
        new_mission = {**original['missions'][0], 'id': 'py-next-01', 'prerequisites': ['py-07-session-tool']}
        new_chapter = {**original, 'id': 'python-next', 'title': 'Next chapter', 'missions': [new_mission]}
        (content / 'first.json').write_text(json.dumps(original))
        (content / 'next.json').write_text(json.dumps(new_chapter))
        (content / 'catalog.json').write_text(json.dumps({'id': 'test', 'title': 'Test', 'chapters': ['first.json', 'next.json']}))
        with patch('server.ROOT', Path(self.temp.name)):
            status, loaded = self.request('/api/bootstrap')
        self.assertEqual(status, 200)
        self.assertEqual(len(loaded['course']['chapters']), 2)
        self.assertEqual(len(loaded['course']['missions']), 8)
        self.assertEqual(loaded['state']['drafts'][mid]['code'], 'existing draft')


if __name__ == '__main__':
    unittest.main()
