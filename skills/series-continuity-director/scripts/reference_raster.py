"""Verify the declared raster derivation of a self-contained SVG source."""
from __future__ import annotations
import io
from importlib.metadata import version
import execution_contract as c


def verify_raster(source: bytes, transport: bytes, derivation: dict) -> None:
    from PIL import Image
    if derivation['mode'] != 'svg-rasterization' or c.digest(source) != derivation['source_sha256']:
        raise ValueError('unsupported or mismatched raster derivation')
    from svg_safety import require_embedded_svg
    require_embedded_svg(source)
    if derivation['renderer_id'] != 'cairosvg' or derivation['renderer_release'] != version('CairoSVG'):
        raise ValueError('the declared SVG renderer is not available')
    dimensions = derivation['output_dimensions']
    import cairosvg
    rendered = cairosvg.svg2png(bytestring=source, output_width=dimensions['width'], output_height=dimensions['height'])
    try:
        with Image.open(io.BytesIO(rendered)) as expected, Image.open(io.BytesIO(transport)) as actual:
            if expected.size != actual.size or expected.convert('RGBA').tobytes() != actual.convert('RGBA').tobytes():
                raise ValueError('raster pixels do not match the selected SVG derivation')
    except Image.DecompressionBombError as exc:
        raise ValueError('a reference raster exceeds the decompression-bomb limit of the installed Pillow: ' + str(exc)) from exc
