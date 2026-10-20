#!/usr/bin/env python3
"""Parlamenti XML feltérképező és D1-kompatibilis, idempotens SQL-importáló.

A valós Országgyűlés API XML-sémáját hozzáférési token nélkül nem tudjuk
élőben ellenőrizni. Emiatt a mezők egy explicit --mapping JSON fájlból jönnek.
Az inspect mód segít az első hiteles XML válasz áttekintésében.
Csak a helyi demó-fixture-höz szállítunk előre jóváhagyott mappinget.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_BYTES = 12 * 1024 * 1024


def local_name(name: str) -> str:
    return name.rsplit('}', 1)[-1].lower()


def load_xml(path: Path) -> ET.Element:
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError('A válasz túl nagy (12 MB limit).')
    lowered = data.lower()
    if b'<!doctype' in lowered or b'<!entity' in lowered:
        raise ValueError('DOCTYPE/ENTITY tiltva (XML biztonság).')
    return ET.fromstring(data)


def element_checksum(item: ET.Element) -> str:
    """Stabil hash: a kizárólag XML-formázásból eredő szóközök nem számítanak.

    Valódi szöveges tartalmat változatlanul hagy. A sémaérzékeny releváns
    változások megítélése továbbra is külön ellenőrzést igényel.
    """
    normalized = copy.deepcopy(item)
    for node in normalized.iter():
        if node.text is not None and not node.text.strip():
            node.text = None
        if node.tail is not None and not node.tail.strip():
            node.tail = None
    canonical = ET.canonicalize(ET.tostring(normalized, encoding='unicode'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def find_items(root: ET.Element, tag: str) -> list[ET.Element]:
    return [elem for elem in root.iter() if local_name(elem.tag) == tag.lower()]


def field(item: ET.Element, definition: dict, prefix: str) -> str | None:
    attr = definition.get(f'{prefix}_attr')
    if attr:
        for key, value in item.attrib.items():
            if local_name(key) == attr.lower():
                return value.strip() or None
    child_tag = definition.get(f'{prefix}_child')
    if child_tag:
        for child in item.iter():
            if child is not item and local_name(child.tag) == child_tag.lower():
                value = ' '.join(''.join(child.itertext()).split())
                if value:
                    return value
    return None


def sql_quote(value: str | None) -> str:
    if value is None:
        return 'NULL'
    return "'" + value.replace("'", "''") + "'"


def slugify(text: str, key: str) -> str:
    normalized = unicodedata.normalize('NFKD', text)
    clean = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    clean = re.sub(r'[^a-z0-9]+', '-', clean.lower()).strip('-')[:60]
    suffix = hashlib.sha256(key.encode('utf-8')).hexdigest()[:8]
    return f'{clean or "iromany"}-{suffix}'


def safe_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme == 'https' and parsed.hostname and (
        parsed.hostname == 'parlament.hu' or parsed.hostname.endswith('.parlament.hu')
    ):
        return value
    return None


def inspect(path: Path, tag: str) -> None:
    root = load_xml(path)
    items = find_items(root, tag)
    print('Gyökérelem:', local_name(root.tag))
    print(f'Talált <{tag}> elemek:', len(items))
    for index, item in enumerate(items[:2], 1):
        print(f'--- {index}. példa ---')
        print('Attribútumok:', json.dumps(item.attrib, ensure_ascii=False))
        print('Elemnevek:', ', '.join(sorted({local_name(c.tag) for c in item.iter() if c is not item})[:35]))
        print('Részlet:', ET.tostring(item, encoding='unicode')[:550])


def render_sql(path: Path, mapping: dict, kind: str) -> tuple[str, int]:
    root = load_xml(path)
    items = find_items(root, mapping.get('item_tag', 'iromany'))
    if not items:
        raise ValueError('Nem találtunk megadott típusú rekordot az XML-ben.')
    if kind == 'official' and mapping.get('fixture_only'):
        raise ValueError('Demó mapping nem használható hivatalos importhoz.')
    seen: set[str] = set()
    lines = ['-- Generált D1 import: azonos rekord/tartalom esetén nem duplikál.', 'BEGIN TRANSACTION;']
    count = 0
    for item in items:
        ident = field(item, mapping, 'id')
        title = field(item, mapping, 'title')
        if not ident or not title:
            raise ValueError('Hiányzik az azonosító vagy a cím; előbb ellenőrizd a mapping fájlt!')
        if ident in seen:
            raise ValueError(f'Duplikált azonosító egy XML-ben: {ident}')
        seen.add(ident)
        official_id = f'{kind}:{ident}'
        reference = field(item, mapping, 'reference')
        status = field(item, mapping, 'status') or 'unknown'
        submitted = field(item, mapping, 'submitted')
        url = safe_url(field(item, mapping, 'url'))
        checksum = element_checksum(item)
        display = title[:240]
        if kind == 'demo':
            display = f'[DEMÓ] {display}'
        slug = slugify(title, official_id)
        q = sql_quote
        lines.append(
            'INSERT INTO proposals (external_id, reference_code, slug, official_title, '
            'display_title, category, lifecycle_status, record_kind, submitted_at, '
            'official_url, source_checksum) VALUES ('
            f'{q(official_id)}, {q(reference)}, {q(slug)}, {q(title)}, '
            f'{q(display)}, {q("Egyéb")}, {q(status)}, {q(kind)}, '
            f'{q(submitted)}, {q(url)}, {q(checksum)}) '
            'ON CONFLICT(external_id) DO UPDATE SET '
            'reference_code=excluded.reference_code, '
            'official_title=excluded.official_title, '
            'display_title=excluded.display_title, '
            'lifecycle_status=excluded.lifecycle_status, '
            'submitted_at=excluded.submitted_at, '
            'official_url=excluded.official_url, '
            'source_checksum=excluded.source_checksum, '
            'updated_at=CURRENT_TIMESTAMP '
            'WHERE proposals.source_checksum IS NOT excluded.source_checksum;'
        )
        lines.append(
            'INSERT OR IGNORE INTO proposal_versions '
            '(proposal_id, version_label, source_checksum, document_url) '
            f'SELECT id, {q("XML import")}, {q(checksum)}, {q(url)} '
            f'FROM proposals WHERE external_id={q(official_id)};'
        )
        count += 1
    lines.append('COMMIT;')
    return '\n'.join(lines) + '\n', count


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl):
            raise ValueError('Nem engedélyezett átirányítás.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_real(base_url: str, token: str, output: Path) -> None:
    if not safe_url(base_url):
        raise ValueError('Csak HTTPS parlament.hu API-URL engedélyezett.')
    url = urllib.parse.urlparse(base_url)
    params = urllib.parse.parse_qsl(url.query, keep_blank_values=True)
    if any(key == 'access_token' for key, _ in params):
        raise ValueError('A token ne legyen az URL-ben; add meg a környezeti változóban.')
    params.append(('access_token', token))
    full_url = urllib.parse.urlunparse(url._replace(query=urllib.parse.urlencode(params)))
    opener = urllib.request.build_opener(RestrictedRedirect())
    req = urllib.request.Request(full_url, headers={'User-Agent': 'KozosDontes-MVP/0.1 (civic research)'})
    with opener.open(req, timeout=30) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('12 MB-nál nagyobb válasz.')
    lowered = data.lower()
    if b'<!doctype' in lowered or b'<!entity' in lowered:
        raise ValueError('Nem biztonságos XML. Nincs elmentve.')
    ET.fromstring(data)  # Nem HTML/CAPTCHA vagy hibaszöveg?
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    print(f'Letöltés sikeres: {output}. Tokent soha ne committolj!')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    view = sub.add_parser('inspect', help='XML elemnevek és attribútumok feltérképezése')
    view.add_argument('xml', type=Path)
    view.add_argument('--item-tag', default='iromany')
    imp = sub.add_parser('import', help='Idempotens D1 SQL generálás')
    imp.add_argument('xml', type=Path)
    imp.add_argument('--mapping', type=Path, required=True)
    imp.add_argument('--kind', choices=['demo', 'official'], default='demo')
    imp.add_argument('--output', type=Path, required=True)
    fetch = sub.add_parser('fetch', help='Valódi API XML mentése (token a környezeti változóban)')
    fetch.add_argument('--url', default=os.environ.get('PARLIAMENT_LIST_URL'))
    fetch.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'inspect':
            inspect(args.xml, args.item_tag)
        elif args.command == 'import':
            mapping = json.loads(args.mapping.read_text(encoding='utf-8'))
            sql, count = render_sql(args.xml, mapping, args.kind)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(sql, encoding='utf-8')
            print(f'{count} tétel; SQL fájl: {args.output}')
        elif args.command == 'fetch':
            token = os.environ.get('PARLIAMENT_ACCESS_TOKEN')
            if not args.url or not token:
                raise ValueError('PARLIAMENT_LIST_URL és PARLIAMENT_ACCESS_TOKEN szükséges.')
            fetch_real(args.url, token, args.output)
        return 0
    except (ValueError, ET.ParseError, OSError, KeyError) as exc:
        message = str(exc)
        token = os.environ.get('PARLIAMENT_ACCESS_TOKEN')
        if token:
            message = message.replace(token, '[REDACTED_TOKEN]')
        print(f'Import hiba: {message}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
