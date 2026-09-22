"""Check imported source bytes, derived images and actual submission delivery."""
from __future__ import annotations
import io
from pathlib import Path
from typing import Any
import execution_contract as c


def path_in_project(root: Path, value: str, *, base: Path | None = None) -> Path:
    path = Path(c.text(value, 'carrier path'))
    if not path.is_absolute():
        path = (base or root) / path
    try:
        relative = path.absolute().relative_to(root.absolute()).as_posix()
    except ValueError as exc:
        raise ValueError('import the reference carrier into the project before activation') from exc
    return c.local(root, relative)


def checked_bytes(root: Path, value: dict, *, base: Path | None = None) -> bytes:
    path = path_in_project(root, value['resolved_path'], base=base)
    raw = c.read(path)
    if c.digest(raw) != c.sha(value['sha256']):
        raise ValueError('reference carrier bytes changed: ' + value['resolved_path'])
    return raw


def delivered(package: dict, *, root: Path, package_dir: Path, inputs: list[dict]) -> list[dict]:
    from PIL import Image
    mode = package['transport_mode']; refs = package['selected_references']
    if not refs:
        return []
    if mode not in {'multi-image', 'single-board'}:
        raise ValueError('identity images require an image delivery mode')
    rows = []; sources = []
    for ref in refs:
        source = checked_bytes(root, ref['source'], base=package_dir)
        transport = checked_bytes(root, ref['transport'], base=package_dir)
        derivation = ref['transport']['derivation']
        if derivation['mode'] == 'direct':
            if source != transport:
                raise ValueError('direct reference transport changed the source bytes')
        else:
            from reference_raster import verify_raster
            verify_raster(source, transport, derivation)
        with Image.open(io.BytesIO(transport)) as image:
            image.load(); sources.append(image.convert('RGB'))
    try:
        media = []
        for index, item in enumerate(inputs):
            raw = c.read(path_in_project(root, item['path']))
            media.append({'sha256': c.digest(raw), 'input_index': index, 'path': item['path'],
                          'request_key': item.get('request_key'), 'role': item.get('role')})
        board = package['single_board']
        if mode == 'single-board':
            if not isinstance(board, dict) or len(board['panels']) != len(refs):
                raise ValueError('single-board delivery needs every selected panel')
            board_raw = checked_bytes(root, board, base=package_dir)
            with Image.open(io.BytesIO(board_raw)) as image:
                image.load(); canvas = image.convert('RGB')
            targets = [x for x in media if x['sha256'] == board['sha256']]
            if len(targets) != 1:
                raise ValueError('the reference board must identify exactly one actual input')
            try:
                boxes = []
                for i, (panel, ref, source) in enumerate(zip(board['panels'], refs, sources, strict=True)):
                    if panel['source_sha256'] != ref['source']['sha256'] or panel['transport_sha256'] != ref['transport']['sha256'] or panel['semantic_role'] != ref['role']:
                        raise ValueError('board panel and ordered reference disagree')
                    b = panel['box']; x,y,w,h = (b[k] for k in ('x','y','width','height'))
                    if min(x,y) < 0 or min(w,h) < 1 or x+w > canvas.width or y+h > canvas.height:
                        raise ValueError('board region is outside the image')
                    if any(x < bx+bw and x+w > bx and y < by+bh and y+h > by for bx,by,bw,bh in boxes):
                        raise ValueError('reference board regions overlap')
                    boxes.append((x,y,w,h))
                    expected = source.copy(); expected.thumbnail((w,h), Image.Resampling.LANCZOS)
                    with expected:
                        if expected.size != (w,h) or canvas.crop((x,y,x+w,y+h)).tobytes() != expected.tobytes():
                            raise ValueError('board region pixels do not derive from the selected transport')
                    rows.append({'reference_number': i+1, **targets[0], 'region_pixels': dict(b)})
            finally:
                canvas.close()
        else:
            if board is not None:
                raise ValueError('multi-image delivery cannot carry a board')
            used = set(); previous = -1
            for i, ref in enumerate(refs):
                targets = [x for x in media if x['sha256'] == ref['transport']['sha256'] and x['input_index'] not in used]
                if len(targets) != 1:
                    raise ValueError('prepared image must identify one actual input')
                target = targets[0]
                if target['input_index'] <= previous:
                    raise ValueError('submission image order differs from the prepared references')
                previous = target['input_index']; used.add(previous)
                rows.append({'reference_number': i+1, **target, 'region_pixels': None})
        return rows
    finally:
        for image in sources:
            image.close()
