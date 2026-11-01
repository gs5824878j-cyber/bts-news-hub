"""Offline feed tests; no upstream requests or tracked output writes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('fetch_news', Path(__file__).resolve().parents[1] / 'fetch_news.py')
news = importlib.util.module_from_spec(spec)
spec.loader.exec_module(news)

def article(member='ALL'):
    return {'m': member, 'd': '2026-10-31', 's': 'fixture', 't': 'fixture title', 'x': 'fixture', 'u': 'https://example.invalid/', '_ts': 1}

class FeedProtectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'news.json'
        self.output.write_text('["previous"]')
        for p in [patch.object(news, 'OUTPUT', self.output), patch.object(news.time, 'sleep')]:
            p.start()
            self.addCleanup(p.stop)

    def test_empty_response_preserves_previous_data(self):
        with patch.object(news, 'fetch_feed', return_value=[]):
            with self.assertRaises(RuntimeError): news.main()
        self.assertEqual(self.output.read_text(), '["previous"]')

    def test_partial_failure_preserves_previous_data(self):
        def fetch(label, query):
            if label == 'RM': raise OSError('synthetic upstream error')
            return [article(label)]
        with patch.object(news, 'fetch_feed', side_effect=fetch):
            with self.assertRaisesRegex(RuntimeError, 'RM'): news.main()
        self.assertEqual(self.output.read_text(), '["previous"]')

    def test_complete_response_deduplicates_and_removes_internal_fields(self):
        with patch.object(news, 'fetch_feed', side_effect=lambda label, query: [article(label)]): news.main()
        result = json.loads(self.output.read_text())
        self.assertEqual(len(result), 1)
        self.assertNotEqual(result[0]['m'], 'ALL')
        self.assertNotIn('_ts', result[0])

if __name__ == '__main__':
    unittest.main()
