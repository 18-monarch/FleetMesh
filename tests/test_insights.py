"""Guard against misleading evidence summaries and missing observations."""
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from insights import summarize_run

class ReviewTests(unittest.TestCase):
    def test_known_record_matches_source_and_uses_submission_time(self):
        record = json.loads((ROOT/'evidence/demonstration.json').read_text())['record']
        result = summarize_run(record)
        self.assertEqual(result['completed'], 7)
        self.assertEqual(result['seconds'], record['snapshot']['time'])
        self.assertEqual(result['saved_frames'], 201)
        self.assertTrue(all(check['status'] == 'observed' for check in result['checks']))
        urgent = next(job for job in result['missions'] if job['id'] == 'J007')
        original = next(job for job in record['snapshot']['jobs'] if job['id'] == 'J007')
        self.assertEqual(urgent['delivery_seconds'], round(original['delivered_at'] - original['created'], 2))
        self.assertNotEqual(urgent['delivery_seconds'], original['delivered_at'])

    def test_conflicting_observations_are_flagged_without_mutation(self):
        record = {'id': 'test', 'snapshot': {'time': 2, 'collisions': 1,
                  'robots': [{'id': 0, 'pid': 6}, {'id': 1, 'pid': 7}]},
                  'frames': [{'time': 1, 'robots': [
                      {'id': 0, 'held': ['N00'], 'active': 'J001'},
                      {'id': 1, 'held': ['N00'], 'active': 'J001'}]}]}
        original = copy.deepcopy(record)
        result = summarize_run(record)
        self.assertEqual([check['status'] for check in result['checks'][:3]], ['review'] * 3)
        self.assertIn('1 conflicts', result['checks'][1]['detail'])
        self.assertEqual(record, original)

    def test_empty_or_unsampled_run_does_not_claim_pass(self):
        result = summarize_run({'id': 'empty', 'snapshot': {'time': 0, 'collisions': 0}})
        self.assertEqual(result['outcome'], 'Run incomplete')
        self.assertIsNone(result['collisions'])
        self.assertTrue(all(check['status'] == 'not_checked' for check in result['checks']))
        result = summarize_run({'id': 'unsampled', 'snapshot': {'time': 1, 'collisions': 0, 'robots': [{'id': 0}]}})
        self.assertEqual(result['checks'][1]['status'], 'not_checked')

if __name__ == '__main__':
    unittest.main()
