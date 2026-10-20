import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from parliament_import import load_xml, render_sql, slugify, safe_url  # noqa: E402


class ImporterTests(unittest.TestCase):
    def setUp(self):
        self.xml = ROOT / 'fixtures' / 'parliament_sample.xml'
        self.mapping = json.loads((ROOT / 'config' / 'mapping.sample.json').read_text(encoding='utf8'))

    def test_extract_and_slug(self):
        sql, count = render_sql(self.xml, self.mapping, 'demo')
        self.assertEqual(count, 2)
        self.assertIn('Fiktív javaslat a közösségi kertekről', sql)
        self.assertIn('demo: SYNTH', sql.replace('demo:SYNTH', 'demo: SYNTH'))
        self.assertRegex(slugify('Őszirózsa', '42'), r'^oszirozsa-[0-9a-f]{8}$')

    def test_fixture_cannot_be_official(self):
        with self.assertRaisesRegex(ValueError, 'Demó mapping'):
            render_sql(self.xml, self.mapping, 'official')

    def test_url_guard(self):
        self.assertIsNone(safe_url('https://attacker.example/a'))
        self.assertIsNone(safe_url('http://parlament.hu/a'))
        self.assertEqual(safe_url('https://www.parlament.hu/some/path'), 'https://www.parlament.hu/some/path')

    def test_xml_doctype_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'malicious.xml'
            p.write_bytes(b'<!DOCTYPE a [<!ENTITY e SYSTEM "file:///etc/passwd">]><a>&e;</a>')
            with self.assertRaisesRegex(ValueError, 'DOCTYPE'):
                load_xml(p)

    def test_migrations_and_idempotent_import(self):
        sql, count = render_sql(self.xml, self.mapping, 'demo')
        self.assertEqual(count, 2)
        conn = sqlite3.connect(':memory:')
        conn.executescript((ROOT / 'migrations' / '0001_initial.sql').read_text(encoding='utf-8'))
        conn.executescript(sql)
        conn.executescript(sql)
        proposals = conn.execute('SELECT COUNT(*) FROM proposals').fetchone()[0]
        versions = conn.execute('SELECT COUNT(*) FROM proposal_versions').fetchone()[0]
        self.assertEqual((proposals, versions), (2, 2))
        conn.executescript((ROOT / 'fixtures' / 'demo.sql').read_text(encoding='utf-8'))
        self.assertEqual(conn.execute('SELECT COUNT(*) FROM proposals').fetchone()[0], 7)
        conn.execute('PRAGMA foreign_key_check')
        self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_db_vote_unique(self):
        conn = sqlite3.connect(':memory:')
        conn.executescript((ROOT / 'migrations' / '0001_initial.sql').read_text(encoding='utf-8'))
        conn.execute("INSERT INTO proposals(external_id,slug,official_title,display_title) VALUES('X','x','X','X')")
        conn.execute("INSERT INTO proposal_versions(proposal_id, version_label,source_checksum) VALUES(1,'v1','h')")
        conn.execute("INSERT INTO ballots(proposal_id,proposal_version_id,opens_at,closes_at) VALUES(1,1,'a','b')")
        conn.execute("INSERT INTO user_profiles(auth_uid) VALUES('uid')")
        conn.execute("INSERT INTO votes(ballot_id,user_uid,choice) VALUES(1,'uid','yes')")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO votes(ballot_id,user_uid,choice) VALUES(1,'uid','no')")


if __name__ == '__main__':
    unittest.main()
