import json
import unittest
from pathlib import Path
from server import catalog

ROOT = Path(__file__).resolve().parents[1]

class GrimoireTests(unittest.TestCase):
    def test_articles_have_valid_links_and_lesson_anchors(self):
        entries = json.loads((ROOT/'content/grimoire.json').read_text())['entries']
        ids = {e['id'] for e in entries}
        missions = {m['id'] for m in catalog()['missions']}
        self.assertEqual(len(ids), len(entries))
        self.assertGreaterEqual(len(entries), 16)
        for entry in entries:
            with self.subTest(entry=entry['id']):
                self.assertIn(entry['mission'], missions)
                self.assertTrue(set(entry['related']) <= ids)
                self.assertTrue(entry['text'] and entry['code'] and entry['pitfall'])
