#!/usr/bin/env python3
"""Inspect actual media and validate locators without assigning aesthetic quality."""
from __future__ import annotations
import io
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
import execution_contract as c
from io_budget import environment_seconds


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError(f'{label}: finite number required')
    return float(value)


def probe(path: Path) -> dict[str, Any]:
    executable = shutil.which('ffprobe')
    if not executable:
        raise ValueError('ffprobe is required to inspect timed media')
    run = subprocess.run([executable, '-v', 'error', '-protocol_whitelist', 'file,pipe', '-show_format', '-show_streams', '-of', 'json', str(path)],
                         capture_output=True, timeout=environment_seconds("PRODUCTION_MEDIA_TIMEOUT_SECONDS"), check=False)
    if run.returncode:
        raise ValueError('media probe failed: ' + run.stderr.decode('utf-8', 'replace'))
    result = c.decode(run.stdout)
    durations = []
    for x in [result.get('format', {}), *result.get('streams', [])]:
        try:
            duration = float(x.get('duration', 'nan'))
        except (ValueError, TypeError):
            continue
        if math.isfinite(duration) and duration >= 0:
            durations.append(duration)
    streams = []
    for s in result.get('streams', []):
        if s.get('codec_type') in {'video', 'audio'}:
            entry = {k: s[k] for k in ('index', 'codec_type', 'codec_name', 'width', 'height',
                       'avg_frame_rate', 'nb_frames', 'sample_rate', 'channels', 'duration', 'start_time') if k in s}
            streams.append(entry)
    if not streams:
        raise ValueError('no inspectable audio or video stream')
    return {'kind': 'video' if any(s['codec_type'] == 'video' for s in streams) else 'audio',
            'duration': max(durations) if durations else None, 'streams': streams}


def inspect(path: Path, raw: bytes | None = None) -> dict[str, Any]:
    raw = c.read(path) if raw is None else raw
    try:
        from PIL import Image
        with Image.open(io.BytesIO(raw)) as image:
            width, height = image.size
            frames = getattr(image, 'n_frames', 1)
            fmt = image.format
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
        if frames == 1:
            return {'kind': 'image', 'width': width, 'height': height, 'format': fmt}
        # Multi-frame images are not silently certified as video with known timing.
    except (ImportError, OSError, ValueError, SyntaxError):
        pass
    except Exception as exc:
        # Pillow keeps its decompression-bomb limit; an image above it stays unmeasured.
        if not isinstance(exc, Image.DecompressionBombError):
            raise
        return {'kind': 'unmeasured', 'reason': 'the image exceeds the decompression-bomb limit of the installed Pillow: ' + str(exc)}
    try:
        text = raw.decode('utf-8')
        if '\x00' not in text:
            return {'kind': 'text', 'lines': len(text.splitlines()), 'bytes': len(raw)}
    except UnicodeError:
        pass
    try:
        # Inspect the exact supplied bytes, not a path that could have changed.
        with tempfile.TemporaryDirectory(prefix="media-probe-") as temporary:
            snapshot = Path(temporary) / ("input" + path.suffix)
            snapshot.write_bytes(raw)
            return probe(snapshot)
    except (ValueError, subprocess.TimeoutExpired, OSError) as exc:
        return {'kind': 'unmeasured', 'reason': str(exc)}


def validate_locator(locator: Any, raw: bytes, media: dict[str, Any]) -> set[str]:
    if not isinstance(locator, dict):
        raise ValueError('observation locator must be an object')
    kind = locator.get('kind')
    supported = {'any'}
    if kind == 'whole':
        c.exact(locator, {'kind'}, 'whole locator')
    elif kind == 'description':
        c.exact(locator, {'kind', 'text'}, 'descriptive locator')
        c.text(locator['text'], 'locator description')
    elif kind in {'lines', 'bytes'}:
        c.exact(locator, {'kind', 'start', 'end'}, 'range locator')
        limit = len(raw) if kind == 'bytes' else len(raw.decode('utf-8').splitlines())
        if type(locator['start']) is not int or type(locator['end']) is not int or not 1 <= locator['start'] <= locator['end'] <= limit:
            raise ValueError('observation range is outside the actual artifact')
        if kind == 'lines' and media.get('kind') == 'text':
            supported.add('text')
    elif kind == 'region':
        c.exact(locator, {'kind', 'unit', 'x', 'y', 'width', 'height'}, 'image region')
        if locator['unit'] != 'normalized' or media.get('kind') != 'image':
            raise ValueError('region locator requires a measured still image and normalized coordinates')
        x, y, width, height = [number(locator[k], k) for k in ('x', 'y', 'width', 'height')]
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise ValueError('image region is outside the actual image')
        supported.add('image')
    elif kind == 'time':
        c.exact(locator, {'kind', 'unit', 'start', 'end', 'stream'}, 'media interval')
        start, end = number(locator['start'], 'start'), number(locator['end'], 'end')
        if locator['unit'] != 'seconds' or type(locator['stream']) is not int:
            raise ValueError('time evidence must select an actual stream index in seconds')
        streams = [stream for stream in media.get('streams', []) if stream.get('index') == locator['stream']]
        if len(streams) != 1:
            raise ValueError('the observation names an absent or ambiguous stream')
        stream = streams[0]
        try:
            duration = float(stream['duration'])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError('the selected stream has no measured duration') from exc
        if not math.isfinite(duration) or not 0 <= start < end <= duration:
            raise ValueError('observation exceeds the measured duration of its stream')
        if stream['codec_type'] == 'video':
            from fractions import Fraction
            try:
                frame_rate = Fraction(stream.get('avg_frame_rate', '0/1'))
            except (ValueError, ZeroDivisionError) as exc:
                raise ValueError('video evidence needs a measured positive frame rate') from exc
            if frame_rate <= 0 or Fraction(str(end - start)) * frame_rate < 1:
                raise ValueError('video evidence needs an interval spanning distinct frames')
            supported.add('video')
        elif stream['codec_type'] == 'audio':
            supported.add('audio')
    else:
        raise ValueError('unknown observation locator')
    if kind in {'whole', 'description'} and media.get('kind') in {'image', 'text'}:
        supported.add(media['kind'])
    return supported


def supports(media: dict[str, Any], evidence: str) -> bool:
    if evidence == 'any':
        return True
    if evidence == 'audio':
        return any(s['codec_type'] == 'audio' for s in media.get('streams', []))
    if evidence == 'video':
        return media.get('kind') == 'video' and (media.get('duration') or 0) > 0
    return evidence == media.get('kind')
