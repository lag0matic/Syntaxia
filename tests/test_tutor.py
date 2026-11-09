import json
import os
import sqlite3
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server import make_server, connect
from tutor import Tutor, TutorError, DEFAULTS, explicit_solution, protect

class TutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'progress.sqlite3'
        self.server = make_server(port=0, database=self.db)
        self.tutor = self.server.tutor
        self.mission = next(m for m in self.server.course['missions'] if m['id'] == 'py-01-message')
        self.body = {'message': 'Can you give me a hint?', 'code': '# my attempt', 'results': 'A check failed.'}
        self.environment = patch.dict(os.environ, {'OPENAI_API_KEY': ''})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.server.server_close()
        self.temp.cleanup()

    def configure(self, **values):
        return self.tutor.save_settings({**DEFAULTS, 'api_key': 'fake-test-secret', **values})

    def test_encrypted_key_and_endpoint_change(self):
        public = self.configure()
        self.assertTrue(public['has_key'])
        saved = self.tutor.settings_file.read_text()
        self.assertNotIn('fake-test-secret', saved)
        self.assertNotIn('encrypted_key', public)
        self.assertEqual(self.tutor.key(self.tutor.settings()), 'fake-test-secret')
        self.configure(api_key='', model='another-model')
        self.assertEqual(self.tutor.key(self.tutor.settings()), 'fake-test-secret')
        self.configure(api_key='', endpoint='https://example.com/v1')
        self.assertFalse(self.tutor.public_settings()['has_key'])
        self.assertEqual(self.tutor.key(self.tutor.settings()), '')
        for endpoint in ['http://example.com/v1', 'https://user:key@example.com/v1', 'https://example.com/v1?key=x']:
            with self.assertRaises(TutorError):
                self.configure(endpoint=endpoint)

    def test_windows_encryption_roundtrip(self):
        protected = protect(b'test-only')
        self.assertNotIn(b'test-only', protected)
        self.assertEqual(protect(protected, decrypt=True), b'test-only')

    def test_solution_request_conservative(self):
        for text in ["I'm stuck", 'Why is yours different?', "Don't give me the full solution", 'Give me a hint', 'Show me the full solution? No, just a hint.']:
            self.assertFalse(explicit_solution(text), text)
        for text in ['Please show me the full solution', 'Give me the complete code', 'Just tell me the answer']:
            self.assertTrue(explicit_solution(text), text)

    def test_context_gating_history_and_no_progress_changes(self):
        self.configure()
        captured = []
        def fake(settings, key, payload):
            captured.append(payload)
            return 'Which value should the name refer to?', {'total_tokens': 30}
        with patch('tutor.call_api', side_effect=fake):
            result = self.tutor.chat(self.body, self.mission, self.db)
            self.assertEqual(len(result['messages']), 2)
            context = json.loads(captured[-1]['input'][0]['content'].split('\n', 1)[1])
            self.assertNotIn('reference', context)
            self.assertNotIn('tests', context)
            self.assertIn('FULL_SOLUTION_ALLOWED for THIS reply: False', captured[-1]['instructions'])
            self.tutor.chat({**self.body, 'message': 'Please show me the full solution'}, self.mission, self.db)
            context = json.loads(captured[-1]['input'][0]['content'].split('\n', 1)[1])
            self.assertIn('reference', context)
            self.tutor.chat(self.body, self.mission, self.db)
            self.assertIn('FULL_SOLUTION_ALLOWED for THIS reply: False', captured[-1]['instructions'])
            self.assertFalse(captured[-1]['store'])
        self.assertEqual(len(Tutor(self.db).history(self.mission['id'])), 6)
        self.assertEqual(self.tutor.history('another-lesson'), [])
        with connect(self.db) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM completions').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM drafts').fetchone()[0], 0)

    def test_follow_up_keeps_the_original_code_separate_from_the_fix(self):
        self.configure()
        broken = {**self.body, 'code': 'return number', 'results': 'Expected 9, got 4',
                  'results_match_code': True}
        fixed = {'message': 'The print was just for debugging.', 'code': 'return total',
                 'results': 'All checks passed.', 'results_match_code': True}
        with patch('tutor.call_api', return_value=('Try returning the accumulator.', {})) as request:
            self.tutor.chat(broken, self.mission, self.db)
            reopened = Tutor(self.db)
            result = reopened.chat(fixed, self.mission, self.db)
            payload = request.call_args.args[2]
        previous = payload['input'][1]['content'].splitlines()
        self.assertEqual(json.loads(previous[1])['code'], 'return number')
        self.assertEqual(previous[-1], broken['message'])
        current = json.loads(payload['input'][-2]['content'].split('\n', 1)[1])
        self.assertEqual(current, {'code': 'return total', 'run_or_test_results': 'All checks passed.',
                                   'results_apply_to_code': True})
        self.assertEqual(payload['input'][-1]['content'], fixed['message'])
        self.assertNotIn('reference', json.loads(payload['input'][0]['content'].split('\n', 1)[1]))
        self.assertEqual(set(result['messages'][0]), {'role', 'content'})

    def test_legacy_chat_history_remains_readable(self):
        old_path = Path(self.temp.name) / 'older.sqlite3'
        history_path = old_path.with_suffix('.tutor.sqlite3')
        db = sqlite3.connect(history_path)
        try:
            with db:
                db.execute('CREATE TABLE messages (id INTEGER PRIMARY KEY, mission TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, usage TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')
                db.execute('INSERT INTO messages(mission,role,content) VALUES(?,?,?)', (self.mission['id'], 'user', 'Earlier conversation'))
        finally:
            db.close()
        tutor = Tutor(old_path)
        history = [{'role': 'user', 'content': 'Earlier conversation'}]
        self.assertEqual(tutor.history(self.mission['id']), history)
        self.assertEqual(tutor.context_history(self.mission['id'], 'new snapshot'), history)

    def test_comparison_requires_completion_and_failures_do_not_save(self):
        self.configure()
        with patch('tutor.call_api', return_value=('Compare the naming choices.', {})) as request:
            with self.assertRaises(TutorError):
                self.tutor.chat({**self.body, 'mode': 'compare'}, self.mission, self.db)
            request.assert_not_called()
            with connect(self.db) as db:
                db.execute('INSERT INTO completions VALUES(?,?,?,?)', (self.mission['id'], '# passing code', 'today', 1))
            self.tutor.chat({**self.body, 'mode': 'compare'}, self.mission, self.db)
            context = json.loads(request.call_args.args[2]['input'][0]['content'].split('\n', 1)[1])
            self.assertEqual(context['passing_code'], '# passing code')
            self.assertIn('reference', context)
        before = self.tutor.history(self.mission['id'])
        with patch('tutor.call_api', side_effect=TutorError('offline')):
            with self.assertRaises(TutorError):
                self.tutor.chat(self.body, self.mission, self.db)
        self.assertEqual(before, self.tutor.history(self.mission['id']))
        self.assertTrue(self.tutor.lock.acquire(False))
        self.tutor.lock.release()

    def test_missing_key_and_locked_mission_make_no_call(self):
        with patch('tutor.call_api') as request:
            with self.assertRaises(TutorError):
                self.tutor.chat(self.body, self.mission, self.db)
            self.configure()
            with self.assertRaises(TutorError):
                self.tutor.chat(self.body, next(m for m in self.server.course['missions'] if m['id'] == 'py-02-arithmetic'), self.db)
            request.assert_not_called()

if __name__ == '__main__':
    unittest.main()

