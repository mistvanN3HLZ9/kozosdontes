import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from parliament_import import render_sql  # noqa: E402
from sync_preview import compare, plan, records  # noqa: E402


class SyncPreviewTests(unittest.TestCase):
    def setUp(self):
        self.v1 = ROOT / 'fixtures' / 'parliament_sample.xml'
        self.v2 = ROOT / 'fixtures' / 'parliament_sample_v2.xml'
        self.mapping = ROOT / 'config' / 'mapping.sample.json'
        self.map_data = json.loads(self.mapping.read_text(encoding='utf-8'))

    def test_detect_changes(self):
        result = compare(records(self.v1, self.map_data), records(self.v2, self.map_data))
        self.assertEqual(result['counts'], {'created': 1, 'changed': 1, 'unchanged': 1, 'missing_not_deleted': 0})
        self.assertEqual(result['created'][0]['id'], 'SYNTH-103')
        self.assertEqual(result['changed'][0]['id'], 'SYNTH-101')

    def test_whitespace_only_formatting_does_not_change_checksum(self):
        from parliament_import import element_checksum, load_xml, find_items
        root = load_xml(self.v1)
        item = find_items(root, 'iromany')[0]
        original = element_checksum(item)
        # A whitespace-only node-ok változtatása nem válthat ki hamis riasztást.
        item.text = '\n      '
        item[0].tail = '\n           '
        self.assertEqual(element_checksum(item), original)

    def test_missing_does_not_mean_deletion(self):
        result = compare(records(self.v2, self.map_data), records(self.v1, self.map_data))
        self.assertEqual(result['counts']['missing_not_deleted'], 1)
        self.assertEqual(result['missing_from_new_feed_not_deleted'][0]['id'], 'SYNTH-103')

    def test_blocks_unreviewed_official_mapping(self):
        with self.assertRaisesRegex(ValueError, 'Demó mapping'):
            plan(self.v1, self.v2, self.mapping, 'official', 'test', True)
        with tempfile.TemporaryDirectory() as directory:
            mapping = Path(directory) / 'mapping.json'
            data = dict(self.map_data, fixture_only=False)
            mapping.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'ellenőrzött mapping'):
                plan(self.v1, self.v2, mapping, 'official', 'test', True)

    def test_migration_triggers_idempotence_and_atomic_log(self):
        conn = sqlite3.connect(':memory:')
        conn.execute('PRAGMA foreign_keys = ON')
        conn.executescript((ROOT / 'migrations' / '0001_initial.sql').read_text(encoding='utf-8'))
        conn.executescript((ROOT / 'migrations' / '0002_sync_audit.sql').read_text(encoding='utf-8'))
        v1_sql, _ = render_sql(self.v1, self.map_data, 'demo')
        conn.executescript(v1_sql)
        report, v2_sql = plan(self.v1, self.v2, self.mapping, 'demo', 'fixture-iteration', False)
        conn.executescript(v2_sql)
        conn.executescript(v2_sql)
        self.assertEqual(report['counts']['changed'], 1)
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM proposals').fetchone()[0], 3)
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM proposal_versions').fetchone()[0], 4)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM proposal_sync_events WHERE event_type='created'").fetchone()[0], 3)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM proposal_sync_events WHERE event_type='changed'").fetchone()[0], 1)
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM sync_runs').fetchone()[0], 2)
        self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_invalid_xml_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / 'bad.xml'
            bad.write_text('<broken>', encoding='utf-8')
            with self.assertRaises(Exception):
                plan(self.v1, bad, self.mapping, 'demo', 'test', False)


if __name__ == '__main__':
    unittest.main()
