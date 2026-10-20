#!/usr/bin/env python3
"""Óvatos XML változásjelentés és D1 import SQL előállító.

Csak helyi XML fájlokat olvas; nincs API-hívás vagy automatikus D1 írás.
Az SQL a korábbi, tesztelt parliament_import.render_sql() függvényt használja.
A régi XML hiánya nem minősül törlésnek. Azonos, nem változó sorok
idempotensek maradnak a D1-ben.
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from parliament_import import element_checksum, field, find_items, load_xml, render_sql, sql_quote


def records(path: Path, mapping: dict) -> dict[str, dict[str, str]]:
    root = load_xml(path)
    items = find_items(root, mapping.get('item_tag', 'iromany'))
    if not items:
        raise ValueError(f'Nem találtam rekordokat ebben: {path}')
    result = {}
    for item in items:
        ident = field(item, mapping, 'id')
        title = field(item, mapping, 'title')
        if not ident or not title:
            raise ValueError('Hiányzik az azonosító vagy a cím.')
        if ident in result:
            raise ValueError(f'Duplikált rekordazonosító: {ident}')
        result[ident] = {
            'title': title,
            'sha256': element_checksum(item),
        }
    return result


def compare(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> dict:
    created = sorted(after.keys() - before.keys())
    missing = sorted(before.keys() - after.keys())
    changed = sorted(k for k in before.keys() & after.keys() if before[k]['sha256'] != after[k]['sha256'])
    unchanged = sorted(k for k in before.keys() & after.keys() if before[k]['sha256'] == after[k]['sha256'])
    return {
        'created': [{'id': k, **after[k]} for k in created],
        'changed': [{'id': k, 'old_sha256': before[k]['sha256'], **after[k]} for k in changed],
        'unchanged': [{'id': k, **after[k]} for k in unchanged],
        'missing_from_new_feed_not_deleted': [{'id': k, **before[k]} for k in missing],
        'counts': {'created': len(created), 'changed': len(changed), 'unchanged': len(unchanged), 'missing_not_deleted': len(missing)},
    }


def plan(before_xml: Path | None, after_xml: Path, mapping_path: Path, kind: str, source_name: str, allow_official: bool) -> tuple[dict, str]:
    mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
    if kind == 'official':
        if mapping.get('fixture_only'):
            raise ValueError('Demó mapping nem használható hivatalos adatokhoz.')
        if not allow_official or mapping.get('verified_for_official_api') is not True:
            raise ValueError('Hivatalos importhoz --allow-official és ellenőrzött mapping szükséges.')
    before = records(before_xml, mapping) if before_xml else {}
    after = records(after_xml, mapping)
    report = compare(before, after)
    report.update({
        'source_name': source_name,
        'record_kind': kind,
        'before_file': str(before_xml) if before_xml else None,
        'after_file': str(after_xml),
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'warning': 'Ez XML-pillanatképek összehasonlítása, nem az élő D1 adatbázis állapotvizsgálata. Nem végez törlést vagy távoli írást.',
    })
    sql, count = render_sql(after_xml, mapping, kind)
    # Az import és a sikeres szinkronnapló ugyanabban a tranzakcióban történik.
    # A processed_count a feldolgozott rekordok száma, NEM a változásoké.
    end = 'COMMIT;\n'
    if not sql.endswith(end):
        raise ValueError('Az importáló SQL tranzakciós szerkezete megváltozott.')
    log = (
        'INSERT INTO sync_runs (finished_at, source_name, status, processed_count) '
        f'VALUES (CURRENT_TIMESTAMP, {sql_quote(source_name)}, {sql_quote("complete")}, {count});\n'
    )
    return report, sql[:-len(end)] + log + end


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, help='Korábbi XML-pillanatkép; elhagyható az első importnál')
    parser.add_argument('--after', required=True, type=Path, help='Aktuális XML-pillanatkép')
    parser.add_argument('--mapping', required=True, type=Path)
    parser.add_argument('--kind', default='demo', choices=['demo', 'official'])
    parser.add_argument('--source-name', default='manual-xml-preview')
    parser.add_argument('--allow-official', action='store_true', help='Csak ellenőrzött API mapping esetén')
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--sql', required=True, type=Path)
    args = parser.parse_args()
    try:
        report, sql = plan(args.before, args.after, args.mapping, args.kind, args.source_name, args.allow_official)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.sql.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        args.sql.write_text(sql, encoding='utf-8')
        print('Változásjelentés:', json.dumps(report['counts'], ensure_ascii=False))
        print('SQL:', args.sql, '| riport:', args.report)
        print('NEM történt adatbázis-módosítás; a SQL alkalmazása külön, kézi lépés.')
        return 0
    except (ValueError, OSError, ET.ParseError, json.JSONDecodeError) as exc:
        print(f'Szinkron előkészítési hiba: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
