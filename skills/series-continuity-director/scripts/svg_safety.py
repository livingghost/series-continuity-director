"""Accept a self-contained static SVG document and refuse active or external content.

The check holds for every consumer of the document, not only one renderer:

- every element and attribute comes from a fixed allowlist of static SVG, or is
  inert: an editor's metadata namespace (Inkscape, Sodipodi, RDF, Dublin Core,
  Creative Commons), or a `data-*`, `aria-*` or `role` attribute, which no
  renderer loads or runs;
- no attribute is an event handler, and no attribute value names javascript:;
- every href and url() names a local #fragment, including inside style;
- an <image> may instead embed a data: URI holding a PNG, JPEG, GIF or WebP
  image, or an SVG document that passes this same check;
- the document declares no DTD, entity or processing instruction.
"""
from __future__ import annotations

import base64
import re
import xml.etree.ElementTree as ET
from urllib.parse import unquote_to_bytes

SVG = '{http://www.w3.org/2000/svg}'
XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
XML_NS = '{http://www.w3.org/XML/1998/namespace}'
# Namespaces whose elements and attributes an editor writes and a renderer ignores.
METADATA_NAMESPACES = frozenset({
    'http://www.inkscape.org/namespaces/inkscape',
    'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'http://purl.org/dc/elements/1.1/',
    'http://creativecommons.org/ns#',
    'http://web.resource.org/cc/',
})
INERT_ATTRIBUTE = re.compile(r'^(?:data-[a-z0-9._-]+|aria-[a-z]+|role)$')

ELEMENTS = frozenset({
    'svg', 'g', 'defs', 'symbol', 'use', 'title', 'desc', 'metadata', 'style',
    'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon',
    'text', 'tspan', 'textPath', 'image',
    'linearGradient', 'radialGradient', 'stop', 'pattern', 'clipPath', 'mask', 'marker',
    'filter', 'feBlend', 'feColorMatrix', 'feComponentTransfer', 'feFuncR', 'feFuncG',
    'feFuncB', 'feFuncA', 'feComposite', 'feConvolveMatrix', 'feDiffuseLighting',
    'feDisplacementMap', 'feDistantLight', 'feDropShadow', 'feFlood', 'feGaussianBlur',
    'feImage', 'feMerge', 'feMergeNode', 'feMorphology', 'feOffset', 'fePointLight',
    'feSpecularLighting', 'feSpotLight', 'feTile', 'feTurbulence',
})

ATTRIBUTES = frozenset({
    # Structure and geometry.
    'id', 'class', 'style', 'lang', 'href', 'transform', 'viewBox', 'preserveAspectRatio',
    'version', 'baseProfile', 'width', 'height', 'x', 'y', 'x1', 'y1', 'x2', 'y2',
    'cx', 'cy', 'r', 'rx', 'ry', 'fx', 'fy', 'fr', 'd', 'points', 'pathLength',
    # Presentation.
    'alignment-baseline', 'baseline-shift', 'clip', 'clip-path', 'clip-rule', 'color',
    'color-interpolation', 'color-interpolation-filters', 'color-rendering', 'direction',
    'display', 'dominant-baseline', 'fill', 'fill-opacity', 'fill-rule', 'filter',
    'flood-color', 'flood-opacity', 'font-family', 'font-size', 'font-size-adjust',
    'font-stretch', 'font-style', 'font-variant', 'font-weight', 'image-rendering',
    'isolation', 'letter-spacing', 'lighting-color', 'marker-start', 'marker-mid',
    'marker-end', 'mask', 'mix-blend-mode', 'opacity', 'overflow', 'paint-order',
    'shape-rendering', 'stop-color', 'stop-opacity', 'stroke', 'stroke-dasharray',
    'stroke-dashoffset', 'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit',
    'stroke-opacity', 'stroke-width', 'text-anchor', 'text-decoration', 'text-rendering',
    'transform-origin', 'unicode-bidi', 'vector-effect', 'visibility', 'word-spacing',
    'writing-mode',
    # Paint servers, clipping, masking and markers.
    'gradientUnits', 'gradientTransform', 'spreadMethod', 'offset', 'patternUnits',
    'patternContentUnits', 'patternTransform', 'clipPathUnits', 'maskUnits',
    'maskContentUnits', 'markerUnits', 'markerWidth', 'markerHeight', 'refX', 'refY', 'orient',
    # Text layout.
    'dx', 'dy', 'rotate', 'textLength', 'lengthAdjust', 'startOffset', 'method', 'spacing', 'side',
    # Filter primitives.
    'filterUnits', 'primitiveUnits', 'in', 'in2', 'result', 'mode', 'type', 'values',
    'tableValues', 'slope', 'intercept', 'amplitude', 'exponent', 'k1', 'k2', 'k3', 'k4',
    'operator', 'radius', 'scale', 'xChannelSelector', 'yChannelSelector', 'baseFrequency',
    'numOctaves', 'seed', 'stitchTiles', 'stdDeviation', 'edgeMode', 'kernelMatrix',
    'kernelUnitLength', 'order', 'divisor', 'bias', 'targetX', 'targetY', 'preserveAlpha',
    'surfaceScale', 'diffuseConstant', 'specularConstant', 'specularExponent', 'azimuth',
    'elevation', 'pointsAtX', 'pointsAtY', 'pointsAtZ', 'limitingConeAngle', 'z',
    # The style element.
    'media',
    # Namespaced attributes.
    XLINK_HREF, XML_NS + 'space', XML_NS + 'lang',
})

# Raster images an <image> may embed, identified by their leading bytes.
RASTER_SIGNATURES = {
    'image/png': (b'\x89PNG\r\n\x1a\n',),
    'image/jpeg': (b'\xff\xd8\xff',),
    'image/gif': (b'GIF87a', b'GIF89a'),
    'image/webp': (b'RIFF',),
}
# CSS functions that load a resource named by a string rather than by url().
RESOURCE_FUNCTIONS = frozenset({'image', 'image-set', '-webkit-image-set', 'src'})
REMOTE_URL = re.compile(r"url\(\s*(?:['\"]\s*)?(?![\s'\"#])", re.IGNORECASE)
CONTROL = re.compile(r'[\x00-\x20]+')


class _Builder(ET.TreeBuilder):
    def pi(self, target, data=None):
        raise ValueError('an SVG processing instruction is not a reference carrier')


def require_embedded_svg(raw: bytes) -> None:
    from defusedxml.ElementTree import DefusedXMLParser
    parser = DefusedXMLParser(target=_Builder(), forbid_dtd=True, forbid_entities=True, forbid_external=True)
    parser.feed(raw)
    root = parser.close()
    if root.tag != SVG + 'svg':
        raise ValueError('reference source must be an SVG document')
    for node in root.iter():
        if not isinstance(node.tag, str):
            raise ValueError(f'SVG node {node.tag!r} is not a static reference carrier')
        metadata = _namespace(node.tag) in METADATA_NAMESPACES
        if not metadata and (not node.tag.startswith(SVG) or node.tag[len(SVG):] not in ELEMENTS):
            raise ValueError(f'SVG element {node.tag!r} is not a static reference carrier')
        name = node.tag[len(SVG):]
        for key, value in node.attrib.items():
            local = key.rsplit('}', 1)[-1]
            if local.lower().startswith('on'):
                raise ValueError(f'SVG event handler {key!r} is not a reference carrier')
            if 'javascript:' in CONTROL.sub('', value).lower():
                raise ValueError('SVG attribute names a javascript: URL')
            if metadata or _namespace(key) in METADATA_NAMESPACES or INERT_ATTRIBUTE.match(key):
                continue
            if key not in ATTRIBUTES:
                raise ValueError(f'SVG attribute {key!r} is not a static reference carrier')
            if key in {'href', XLINK_HREF}:
                _href(name, value)
            elif key == 'style':
                _style(value)
            else:
                _css_value(value)
        if name == 'style':
            _style(node.text or '', stylesheet=True)


def _namespace(name: str) -> str:
    return name[1:].split('}', 1)[0] if name.startswith('{') else ''


def _href(element: str, value: str) -> None:
    text = value.strip()
    if text.startswith('#'):
        return
    if element == 'image' and text[:5].lower() == 'data:':
        _embedded_image(text)
        return
    raise ValueError('an SVG reference must be a local #fragment or an image embedded as data')


def _embedded_image(uri: str) -> None:
    """Check a data: image the way a browser and a sniffing renderer each read it."""
    header, comma, data = uri[5:].partition(',')
    if not comma:
        raise ValueError('an embedded SVG image is not a data: URI')
    payload = unquote_to_bytes(data)
    if header.lower().endswith(';base64'):
        if not header.endswith(';base64'):
            raise ValueError('an embedded SVG image spells its base64 marker ambiguously')
        payload = base64.decodebytes(payload)
        header = header[:-len(';base64')]
    declared = header.split(';', 1)[0].strip().lower()
    # A renderer may read any payload that looks like SVG or gzip as SVG, whatever its declared type.
    sniffed = not payload.startswith(RASTER_SIGNATURES['image/png']) and (
        payload.startswith((b'<svg ', b'<?xml', b'<!DOC', b'\x1f\x8b')) or b'<svg' in payload)
    if declared == 'image/svg+xml' or sniffed:
        if payload.startswith(b'\x1f\x8b'):
            raise ValueError('a compressed embedded SVG is not a reference carrier')
        # The nested document is shorter than its container, so the check ends.
        require_embedded_svg(payload)
        return
    signatures = RASTER_SIGNATURES.get(declared)
    if signatures is None or not payload.startswith(signatures):
        raise ValueError('an embedded SVG image must be PNG, JPEG, GIF, WebP or SVG with matching bytes')
    if declared == 'image/webp' and payload[8:12] != b'WEBP':
        raise ValueError('an embedded SVG image must be PNG, JPEG, GIF, WebP or SVG with matching bytes')


def _css_value(text: str) -> None:
    import tinycss2
    if REMOTE_URL.search(text):
        raise ValueError('an SVG url() must name a local #fragment')
    _tokens(tinycss2.parse_component_value_list(text, skip_comments=True), strict=False)


def _style(text: str, *, stylesheet: bool = False) -> None:
    import tinycss2
    if 'javascript:' in CONTROL.sub('', text).lower():
        raise ValueError('SVG style names a javascript: URL')
    if REMOTE_URL.search(text):
        raise ValueError('an SVG style url() must name a local #fragment')
    values = (tinycss2.parse_stylesheet(text, skip_comments=True, skip_whitespace=True) if stylesheet
              else tinycss2.parse_declaration_list(text, skip_comments=True, skip_whitespace=True))
    _tokens(values, strict=True)


def _tokens(nodes, *, strict: bool) -> None:
    for token in nodes:
        if token.type == 'error' and strict:
            raise ValueError('invalid SVG style')
        if token.type == 'at-rule':
            raise ValueError('SVG style cannot use at-rules such as @import')
        if token.type == 'url' and not token.value.startswith('#'):
            raise ValueError('an SVG url() must name a local #fragment')
        if token.type == 'function':
            if token.lower_name in RESOURCE_FUNCTIONS:
                raise ValueError(f'SVG style function {token.lower_name}() loads a resource')
            if token.lower_name == 'url':
                args = [x for x in token.arguments if x.type not in {'whitespace', 'comment'}]
                if len(args) != 1 or args[0].type != 'string' or not args[0].value.startswith('#'):
                    raise ValueError('an SVG url() must name a local #fragment')
        for attr in ('value', 'content', 'prelude', 'arguments'):
            children = getattr(token, attr, None)
            if isinstance(children, list):
                _tokens(children, strict=strict)
