import threading
import unittest
from unittest.mock import Mock
from desktop import await_editor


class DesktopCloseTests(unittest.TestCase):
    def test_saved_mission_and_close_option(self):
        window = Mock()
        def evaluate(script, callback):
            self.assertIn('"closing": true', script)
            callback({'ok': True, 'mission': 'lesson'})
        window.evaluate_js.side_effect = evaluate
        self.assertEqual(await_editor(window, closing=True), {'ok': True, 'mission': 'lesson'})

    def test_save_failure_stays_blocked(self):
        window = Mock()
        window.evaluate_js.side_effect = lambda script, callback: callback({'ok': False, 'message': 'Save failed'})
        with self.assertRaisesRegex(RuntimeError, 'Save failed'):
            await_editor(window)

    def test_native_bridge_failure_is_reported(self):
        window = Mock()
        window.evaluate_js.side_effect = RuntimeError('Main window failed to start')
        with self.assertRaisesRegex(RuntimeError, 'connection is unavailable'):
            await_editor(window)

    def test_blocked_native_call_has_deadline(self):
        release = threading.Event()
        window = Mock()
        def evaluate(script, callback):
            release.wait(2)
            callback({'ok': True})
        window.evaluate_js.side_effect = evaluate
        try:
            with self.assertRaisesRegex(RuntimeError, 'did not respond'):
                await_editor(window, timeout=0.02)
        finally:
            release.set()

    def test_missing_promise_callback_has_deadline(self):
        with self.assertRaisesRegex(RuntimeError, 'did not respond'):
            await_editor(Mock(), timeout=0.02)
