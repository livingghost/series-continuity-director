#!/usr/bin/env python3
"""Read complete route documents and bind authored applications to issued evidence."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Any, TextIO

import execution_contract as c
import execution_routes

ROOT = Path(__file__).resolve().parents[1]


def _hex(value: Any, length: int, label: str) -> str:
    if not isinstance(value, str) or len(value) != length or any(x not in '0123456789abcdef' for x in value):
        raise ValueError(f'{label}: expected {length} lowercase hexadecimal characters')
    return value


def _normalized(value: str) -> str:
    return ' '.join(value.split())


def prose_blocks(document: str) -> list[str]:
    """Parse paragraph containers, excluding headings, tables, code and metadata.

    The parser preserves source spelling. Block markers describe Markdown
    syntax; no vocabulary classifies the subject or meaning of a paragraph.
    """
    result: list[str] = []
    paragraph: list[str] = []
    fence: tuple[str, int] | None = None
    table = False
    frontmatter = False
    html = False
    def flush() -> None:
        if paragraph:
            result.append(_normalized('\n'.join(paragraph)))
            paragraph.clear()
    for index, raw in enumerate(document.splitlines()):
        line = raw.strip()
        if index == 0 and line == '---':
            frontmatter = True
            continue
        if frontmatter:
            if line in {'---', '...'}:
                frontmatter = False
            continue
        probe = raw.lstrip(' ')
        indent = len(raw) - len(probe)
        # A block quote can contain a heading, fenced block or paragraph.
        while probe.startswith('>'):
            probe = probe[1:].lstrip(' ')
        if fence is not None:
            char, count = fence
            close = probe.rstrip()
            if len(close) >= count and all(x == char for x in close):
                fence = None
            continue
        if indent <= 3 and probe and probe[0] in {'`', '~'}:
            count = len(probe) - len(probe.lstrip(probe[0]))
            if count >= 3:
                flush(); table = False; fence = (probe[0], count)
                continue
        if not line:
            flush(); table = False; html = False
            continue
        if html:
            continue
        if probe.startswith('<') and not probe.startswith('<http'):
            flush(); html = True
            continue
        if raw.startswith('    ') or raw.startswith('\t'):
            flush()
            continue
        heading_marks = len(probe) - len(probe.lstrip('#'))
        if 1 <= heading_marks <= 6 and (len(probe) == heading_marks or probe[heading_marks].isspace()):
            flush(); table = False
            continue
        # Setext headings own their preceding paragraph. A delimiter row owns
        # the preceding table header and following table rows.
        if line and set(line) <= {'=', '-'}:
            paragraph.clear(); table = False
            continue
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        delimiter = '|' in line and bool(cells) and all(
            len(cell.strip(':')) >= 3 and set(cell.strip(':')) == {'-'} for cell in cells)
        if delimiter:
            paragraph.clear(); table = True
            continue
        if table:
            if '|' in line:
                continue
            table = False
        if len(line.replace(' ', '')) >= 3 and set(line.replace(' ', '')) in ({'*'}, {'_'}, {'-'}):
            flush()
            continue
        if probe.startswith('[') and ']:' in probe:
            flush()
            continue
        paragraph.append(raw)
    flush()
    return result


def ledger_candidates(*, project: Path | None = None, package_root: Path | None = None) -> list[Path]:
    if project is None:
        raise ValueError('the project root is required for its reading ledger')
    return [project.absolute() / 'work/reads.jsonl']


def _ledger_folder(ledger: Path) -> Path:
    """Create the ledger's own folder inside an existing project and return it."""
    folder = ledger.absolute().parent
    if not folder.parent.is_dir():
        raise ValueError(f'project root is not an existing directory: {folder.parent}')
    folder.mkdir(exist_ok=True)
    return folder


def ledger_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = c.read(path)
    if raw and not raw.endswith(b'\n'):
        raise ValueError(f'incomplete reading ledger: {path}')
    rows = []
    fields = {'at', 'route', 'features', 'key_sha256', 'documents', 'cwd'}
    for line in raw.splitlines():
        if not line.strip():
            raise ValueError(f'empty reading ledger row: {path}')
        row = c.decode(line)
        c.exact(row, fields, 'reading ledger row')
        c.sha(row['key_sha256'])
        c.text(row['at'], 'reading timestamp'); c.text(row['cwd'], 'reading cwd')
        _validate_manifest(row)
        rows.append(row)
    return rows


def _validate_manifest(value: dict[str, Any]) -> None:
    c.text(value.get('route'), 'reading route')
    features = value.get('features')
    if not isinstance(features, list) or any(not isinstance(x, str) or not x for x in features):
        raise ValueError('reading features must be explicit strings')
    if features != sorted(set(features)):
        raise ValueError('reading features must be normalized and unique')
    documents = value.get('documents')
    if not isinstance(documents, list) or not documents:
        raise ValueError('reading documents must be a nonempty array')
    seen = set()
    for item in documents:
        c.exact(item, {'path', 'sha256'}, 'reading document')
        c.local(ROOT, item['path'], exists=False); c.sha(item['sha256'])
        if item['path'] in seen:
            raise ValueError('duplicate reading document')
        seen.add(item['path'])


def capture(route: str, features: list[str] | None = None, *, root: Path = ROOT) -> tuple[dict, list[tuple[dict, bytes]]]:
    resolved = execution_routes.resolve(route, features, root=root)
    bodies = []
    for entry in resolved['reads']:
        raw = c.read(c.local(root, entry['path']))
        raw.decode('utf-8')
        if c.digest(raw) != entry['sha256']:
            raise ValueError('document changed while reading: ' + entry['path'])
        bodies.append(({'kind': 'document', **entry}, raw))
    manifest = {'route': resolved['route'], 'features': resolved['features'], 'documents': resolved['reads']}
    return manifest, bodies


def _issue(manifest: dict, ledger: Path, *, key: str | None = None, at: str | None = None, cwd: str | None = None) -> dict:
    """Append under the caller's lock. Fixed values support synthetic fixtures."""
    key = _hex(key or secrets.token_hex(16), 32, 'reading key')
    row = {**manifest, 'at': at or datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'cwd': cwd if cwd is not None else str(Path.cwd()), 'key_sha256': c.digest(key.encode('ascii'))}
    existing = ledger_rows(ledger)
    for old in existing:
        if old['key_sha256'] == row['key_sha256'] and any(old[k] != row[k] for k in manifest):
            raise ValueError('reading key already belongs to different documents or route')
    if row in existing:
        return {'reading_key': key, 'row': row}
    c.atomic(ledger, b''.join(c.encoded(x) for x in existing) + c.encoded(row), replace=ledger.exists())
    return {'reading_key': key, 'row': row}


def issue(route: str, features: list[str] | None = None, *, root: Path = ROOT,
          project: Path | None = None, ledger: Path | None = None, stream: TextIO | None = None,
          key: str | None = None, at: str | None = None, cwd: str | None = None) -> dict:
    """Output all bytes before issuing evidence. Fixed key/time are fixture inputs."""
    stream = sys.stdout if stream is None else stream
    target = ledger if ledger is not None else ledger_candidates(project=project)[0]
    manifest, bodies = capture(route, features, root=root)
    for meta, raw in bodies:
        stream.write('--- ' + json.dumps(meta, ensure_ascii=False) + ' ---\n')
        stream.write(raw.decode('utf-8'))
        stream.write('\n')
    stream.flush()
    with c.lock(_ledger_folder(target)):
        current, _ = capture(route, features, root=root)
        if manifest != current:
            raise ValueError('reading sources changed; read the current documents')
        issued = _issue(manifest, target, key=key, at=at, cwd=cwd)
    stream.write('reading-key: ' + route + ' ' + issued['reading_key'] + '\n')
    stream.flush()
    return issued


def _find_row(record: dict, ledgers: list[Path]) -> dict:
    key_hash = c.digest(_hex(record.get('reading_key'), 32, 'reading key').encode('ascii'))
    matching = []
    for path in dict.fromkeys(ledgers):
        for row in ledger_rows(path):
            if row['key_sha256'] == key_hash:
                matching.append(row)
    if not matching:
        raise ValueError('reading key has no issuance row in the selected ledgers')
    fields = {'route', 'features', 'documents'}
    if any(any(row[field] != record[field] for field in fields) for row in matching):
        raise ValueError('reading issuance differs from the supplied route, features or document versions')
    return matching[0]


def validate_record_content(record: Any) -> None:
    """Check the recorded contract without granting a current execution permission."""
    c.exact(record, {'route', 'features', 'reading_key', 'documents', 'applied'}, 'route reading')
    _validate_manifest(record)
    _hex(record['reading_key'], 32, 'reading key')
    available = {item['path'] for item in record['documents']}
    if not isinstance(record['applied'], list):
        raise ValueError('reading applications must be an array')
    for item in record['applied']:
        c.exact(item, {'path', 'quote', 'why'}, 'document application')
        c.text(item['quote'], 'quotation')
        c.text(item['why'], 'application reason')
        if item['path'] not in available:
            raise ValueError('quotation document is absent from the recorded edition')


def require_route_reading(record: Any, *, root: Path = ROOT, ledgers: list[Path] | None = None,
                          project: Path | None = None, package_root: Path | None = None,
                          routes: set[str] | None = None, features: list[str] | None = None) -> dict:
    validate_record_content(record)
    if routes is not None and record['route'] not in routes:
        raise ValueError('reading route must be one of: ' + ', '.join(sorted(routes)))
    if features is not None:
        expected_features = execution_routes.resolve(record['route'], features, root=root)['features']
        if expected_features != record['features']:
            raise ValueError('reading features do not match the execution features')
    current, bodies = capture(record['route'], record['features'], root=root)
    for field in current:
        if record[field] != current[field]:
            raise ValueError('reading ' + field + ' differs from the current sources; read again')
    row = _find_row(record, ledgers if ledgers is not None else ledger_candidates(project=project, package_root=package_root))
    applications = record['applied']
    if not isinstance(applications, list):
        raise ValueError('reading applications must be an array')
    required = {x['path'] for x in record['documents']} - set(c.load(c.local(root, execution_routes.MANIFEST))['always_read'])
    available = {meta['path']: raw.decode('utf-8') for meta, raw in bodies if meta['kind'] == 'document'}
    covered = set()
    for item in applications:
        c.exact(item, {'path', 'quote', 'why'}, 'document application')
        c.text(item['why'], 'application reason')
        quote = _normalized(c.text(item['quote'], 'quote'))
        if item['path'] not in available:
            raise ValueError('quote refers to a document outside this route')
        if len(quote.split()) < 12 or not any(quote in block for block in prose_blocks(available[item['path']])):
            raise ValueError('quote must contain at least twelve words of paragraph text: ' + item['path'])
        covered.add(item['path'])
    if required - covered:
        raise ValueError('missing application for: ' + ', '.join(sorted(required - covered)))
    return row


def resolve_issuance(key: str, *, project: Path | None = None,
                     ledgers: list[Path] | None = None) -> dict:
    """Resolve a supplied key to one consistent locally issued document edition."""
    digest = c.digest(_hex(key, 32, 'reading key').encode('ascii'))
    matches = [row for path in dict.fromkeys(ledgers if ledgers is not None else ledger_candidates(project=project))
               for row in ledger_rows(path) if row['key_sha256'] == digest]
    if not matches:
        raise ValueError('reading key has no issuance row in the selected ledgers')
    fields = {'route', 'features', 'documents'}
    if any(any(row[field] != matches[0][field] for field in fields) for row in matches[1:]):
        raise ValueError('reading key has conflicting issuance records')
    return {'reading_key': key, 'row': matches[0]}


def check_snapshot_issuance(snapshot: str, issued: dict, *, project: Path | None = None) -> None:
    """Check a supplied delivery selector without making retention a key condition."""
    _hex(snapshot, 64, 'reading snapshot')
    paths = [path.parent / 'reading-snapshots' / snapshot / 'snapshot.json'
             for path in ledger_candidates(project=project)]
    existing = [path for path in dict.fromkeys(paths) if path.is_file()]
    if not existing:
        # A completed delivery snapshot may be discarded. The issuance row
        # remains the authoritative key witness.
        return
    for path in existing:
        value = c.load(path)
        if c.content_id(value) != snapshot:
            raise ValueError('reading snapshot address mismatch')
        if any(issued['row'][key] != item for key, item in value['manifest'].items()):
            raise ValueError('selected delivery snapshot belongs to another reading')


def build_record(issued: dict, applications: dict, *, root: Path = ROOT,
                 project: Path | None = None, ledgers: list[Path] | None = None) -> dict:
    c.exact(issued, {'reading_key', 'row'}, 'issued reading')
    row = issued['row']
    result = {key: row[key] for key in ('documents', 'features', 'route')}
    result.update(reading_key=issued['reading_key'], applied=applications['applied'])
    require_route_reading(result, root=root, project=project, ledgers=ledgers)
    return result



def copy_issuance(record: dict, destination: Path, *, root: Path = ROOT, project: Path | None = None,
                  ledgers: list[Path] | None = None, package_root: Path | None = None) -> dict:
    """Copy a verified issuance row without issuing a key or an application."""
    row = require_route_reading(record, root=root, project=project, ledgers=ledgers, package_root=package_root)
    with c.lock(_ledger_folder(destination)):
        rows = ledger_rows(destination)
        matching = [old for old in rows if old['key_sha256'] == row['key_sha256']]
        fields = {'route', 'features', 'documents'}
        if any(any(old[k] != row[k] for k in fields) for old in matching):
            raise ValueError('destination ledger has a conflicting issuance')
        if not matching:
            c.atomic(destination, b''.join(c.encoded(old) for old in rows) + c.encoded(row), replace=destination.exists())
    return row

def _snapshot_dir(ledger: Path, snapshot: str) -> Path:
    return c.local(ledger.parent, 'reading-snapshots/' + _hex(snapshot, 64, 'reading snapshot'))


def _cursor(ledger: Path, cursor: str) -> tuple[Path, dict, dict]:
    parts = cursor.split(':')
    if len(parts) != 2:
        raise ValueError('reading cursor must identify a snapshot and a delivered page')
    folder = _snapshot_dir(ledger, parts[0])
    snapshot = c.load(c.local(folder, 'snapshot.json'))
    if c.content_id(snapshot) != parts[0]:
        raise ValueError('reading snapshot address mismatch')
    receipt = c.load(c.local(folder, 'pages/' + _hex(parts[1], 64, 'reading page') + '.json'))
    if c.content_id(receipt) != parts[1] or receipt['snapshot'] != parts[0]:
        raise ValueError('reading page address mismatch')
    return folder, snapshot, receipt


def _position(snapshot: dict, offset: int) -> tuple[int, int]:
    for index, meta in enumerate(snapshot['bodies']):
        if offset < meta['size']:
            return index, offset
        offset -= meta['size']
    if offset:
        raise ValueError('reading cursor exceeds the snapshot')
    return len(snapshot['bodies']), 0


def read_page(*, route: str | None = None, features: list[str] | None = None,
              cursor: str | None = None, replay: bool = False, page_bytes: int = 16384,
              root: Path = ROOT, project: Path | None = None, ledger: Path | None = None,
              stream: TextIO | None = None) -> dict:
    """Deliver an immutable page, then record its exact byte range under a lock."""
    if isinstance(page_bytes, bool) or not isinstance(page_bytes, int) or page_bytes < 4:
        raise ValueError('page-bytes must be an integer of at least four')
    stream = sys.stdout if stream is None else stream
    ledger = ledger if ledger is not None else ledger_candidates(project=project)[0]
    # A new reading creates the ledger folder. A continuation needs the existing one.
    with c.lock(_ledger_folder(ledger) if cursor is None else ledger.parent):
        if cursor is None:
            if route is None:
                raise ValueError('a route is required to start reading')
            manifest, bodies = capture(route, features, root=root)
            snapshot = {'manifest': manifest, 'root': str(root.absolute()),
                        'nonce': secrets.token_hex(16), 'bodies': [dict(meta, size=len(raw)) for meta, raw in bodies]}
            sid = c.content_id(snapshot)
            folder = c.local(ledger.parent, 'reading-snapshots/' + sid, exists=False)
            folder.mkdir(parents=True)
            c.atomic(folder / 'snapshot.json', c.encoded(snapshot))
            for _, raw in bodies:
                c.object_store(folder, raw)
            start = 0
        else:
            if route is not None or features:
                raise ValueError('a cursor fixes its route and features')
            folder, snapshot, page = _cursor(ledger, cursor)
            sid = c.content_id(snapshot)
            if str(root.absolute()) != snapshot['root']:
                raise ValueError('reading cursor belongs to a different skill root')
            start = page['start'] if replay else page['end']
        total = sum(x['size'] for x in snapshot['bodies'])
        if cursor is not None and start == total and not replay:
            raise ValueError('reading is complete; replay the final page to receive a new key')
        index, offset = _position(snapshot, start)
        budget = page_bytes
        end = start
        ranges = []
        pending = {'snapshot': sid, 'start': start, 'end': start, 'ranges': []}
        pending_id = c.content_id(pending)
        pending_path = folder / 'pages' / (pending_id + '.json')
        if not pending_path.exists():
            c.atomic(pending_path, c.encoded(pending))
        stream.write('reading-start: ' + sid + ':' + pending_id + '\n')
        stream.flush()
        while index < len(snapshot['bodies']) and budget:
            meta = snapshot['bodies'][index]
            raw = c.object_read(folder, meta['sha256'])
            stop = min(len(raw), offset + budget)
            while stop > offset and stop < len(raw) and raw[stop] & 0xC0 == 0x80:
                stop -= 1
            if stop == offset and offset < len(raw):
                break
            segment = raw[offset:stop]
            header = {'snapshot': sid, 'kind': meta['kind'], 'path': meta['path'],
                      'sha256': meta['sha256'], 'start': offset, 'end': stop, 'total': len(raw)}
            stream.write('--- ' + json.dumps(header, ensure_ascii=False) + ' ---\n')
            stream.write(segment.decode('utf-8')); stream.write('\n')
            ranges.append(header)
            end += len(segment); budget -= len(segment)
            if stop == len(raw):
                index += 1; offset = 0
            else:
                offset = stop
        stream.flush()
        page = {'snapshot': sid, 'start': start, 'end': end, 'ranges': ranges}
        page_id = c.content_id(page)
        page_path = folder / 'pages' / (page_id + '.json')
        if page_path.exists():
            if c.load(page_path) != page:
                raise ValueError('reading page collision')
        else:
            c.atomic(page_path, c.encoded(page))
        result = {'snapshot': sid, 'cursor': sid + ':' + page_id, 'delivered': ranges,
                  'remaining_bytes': total - end}
        if end == total:
            # Completion depends on a contiguous cover of committed deliveries.
            covered = sorted((p['start'], p['end']) for p in (c.load(x) for x in (folder / 'pages').glob('*.json')))
            reach = 0
            for low, high in covered:
                if low > reach:
                    raise ValueError('undelivered range in reading snapshot')
                reach = max(reach, high)
            if reach != total:
                raise ValueError('reading snapshot is incomplete')
            current, _ = capture(snapshot['manifest']['route'], snapshot['manifest']['features'], root=root)
            if current != snapshot['manifest']:
                raise ValueError('sources changed during reading; start a new read')
            result['issued'] = _issue(current, ledger)
    stream.write('reading-cursor: ' + result['cursor'] + '\n')
    if 'issued' in result:
        stream.write('reading-key: ' + snapshot['manifest']['route'] + ' ' + result['issued']['reading_key'] + '\n')
    stream.flush()
    return result


def add_read_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('route', nargs='?')
    parser.add_argument('--feature', action='append', default=[])
    parser.add_argument('--root', type=Path, help='Project or studio root for the reading ledger')
    parser.add_argument('--page-bytes', type=int)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--continue', dest='cursor')
    group.add_argument('--replay', dest='replay')


def read_command(args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict:
    if args.cursor or args.replay or args.page_bytes is not None:
        return read_page(route=args.route, features=args.feature, cursor=args.cursor or args.replay,
                         replay=bool(args.replay), page_bytes=16384 if args.page_bytes is None else args.page_bytes,
                         project=args.root)
    if args.route is None:
        raise ValueError('read requires a route or a continuation cursor')
    return issue(args.route, args.feature, project=args.root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record', type=Path)
    parser.add_argument('--root', type=Path)
    args = parser.parse_args()
    try:
        row = require_route_reading(c.load(args.record), project=args.root, package_root=args.record.parent)
        print(json.dumps({'ok': True, 'route': row['route'], 'evidence': 'issuance and exact quotation'}, indent=2))
        return 0
    except c.EXPECTED_ERRORS as exc:
        print(json.dumps(c.failure(exc))); return 1


if __name__ == '__main__':
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
