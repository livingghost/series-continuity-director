#!/usr/bin/env python3
"""Build the suite's bundled craft vocabulary from its cinematic lexicon."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = 'assets/resources/prompt-vocabulary.json'


def build(root: Path = ROOT) -> dict:
    categories = []
    current = None
    for line in (root / 'references/cinematic-lexicon.md').read_text(encoding='utf-8').splitlines():
        heading = re.match(r'^## ([1-5])\. (.+)$', line)
        if heading:
            current = {'id': 'cinematic-' + heading[1], 'name': heading[2], 'entries': []}
            categories.append(current)
        elif line.startswith('## '):
            current = None
        elif current is not None and line.startswith('|'):
            cells = [x.strip() for x in line.strip().strip('|').split('|')]
            if len(cells) >= 2 and cells[0] not in {'Term', '---'} and not set(cells[0]) <= {'-', ':'}:
                current['entries'].append({'term':cells[0], 'aliases':[], 'description':cells[1],
                    'source':'references/cinematic-lexicon.md#' + current['id'].split('-')[-1]})
    if len(categories) != 5 or any(not c['entries'] for c in categories):
        raise ValueError('cinematic lexicon has an incomplete vocabulary source')
    return {'scope':'Directing vocabulary; model dialect support is verified separately.', 'categories':categories}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');a=parser.parse_args()
    target=ROOT/OUTPUT;data=build();raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
    if a.check:
        ok=target.is_file() and target.read_bytes()==raw
    else:
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);ok=True
    print(json.dumps({'ok':ok,'entries':sum(len(v['entries']) for v in data['categories']),'output':OUTPUT,'check':a.check}));return int(not ok)
if __name__=='__main__':
    import stdio_utf8
    stdio_utf8.configure()
    raise SystemExit(main())
