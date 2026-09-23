"""Render a self-contained SVG source to a raster, and verify a declared raster derivation.

The renderer is resvg through the `resvg-py` distribution, whose wheel carries
its native code, so pip alone installs it on every platform. It draws images a
document embeds as data, and it reads no file or URL the document names.
"""
from __future__ import annotations
import io
from importlib.metadata import version
import execution_contract as c

RENDERER_ID = 'resvg'
DISTRIBUTION = 'resvg-py'


def renderer_release() -> str:
    return version(DISTRIBUTION)


def render_svg(source: bytes, width: int, height: int) -> bytes:
    """Draw a checked SVG source at the given pixel size, as PNG bytes."""
    from svg_safety import require_embedded_svg
    require_embedded_svg(source)
    try:
        text = source.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError('an SVG reference source must be UTF-8') from exc
    import resvg_py
    return bytes(resvg_py.svg_to_bytes(svg_string=text, width=width, height=height))


def verify_raster(source: bytes, transport: bytes, derivation: dict) -> None:
    from PIL import Image
    if derivation['mode'] != 'svg-rasterization' or c.digest(source) != derivation['source_sha256']:
        raise ValueError('unsupported or mismatched raster derivation')
    from svg_safety import require_embedded_svg
    require_embedded_svg(source)
    if derivation['renderer_id'] != RENDERER_ID or derivation['renderer_release'] != renderer_release():
        raise ValueError('the declared SVG renderer is not available')
    dimensions = derivation['output_dimensions']
    rendered = render_svg(source, dimensions['width'], dimensions['height'])
    try:
        with Image.open(io.BytesIO(rendered)) as expected, Image.open(io.BytesIO(transport)) as actual:
            if expected.size != actual.size or expected.convert('RGBA').tobytes() != actual.convert('RGBA').tobytes():
                raise ValueError('raster pixels do not match the selected SVG derivation')
    except Image.DecompressionBombError as exc:
        raise ValueError('a reference raster exceeds the decompression-bomb limit of the installed Pillow: ' + str(exc)) from exc
