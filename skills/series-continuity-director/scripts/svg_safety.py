"""Validate self-contained XML resources before local SVG rendering."""
from __future__ import annotations
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit


def require_embedded_svg(raw: bytes) -> None:
    from defusedxml.ElementTree import fromstring
    root = fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError('reference source must be an SVG document')
    for node in root.iter():
        if node.tag in {'{http://www.w3.org/2000/svg}script', '{http://www.w3.org/2000/svg}foreignObject'}:
            raise ValueError('active SVG content is not a reference carrier')
        for key, value in node.attrib.items():
            if key in {'href', '{http://www.w3.org/1999/xlink}href'}:
                parsed = urlsplit(value)
                if not (value.startswith('#') or parsed.scheme == 'data'):
                    raise ValueError('SVG reference resource must be embedded')
            if key == 'style':
                _style(value)
        if node.tag == '{http://www.w3.org/2000/svg}style':
            _style(node.text or '', stylesheet=True)


def _style(text: str, *, stylesheet: bool = False) -> None:
    import tinycss2
    values = tinycss2.parse_stylesheet(text, skip_comments=True, skip_whitespace=True) if stylesheet else tinycss2.parse_declaration_list(text, skip_comments=True, skip_whitespace=True)
    def visit(nodes):
        for token in nodes:
            if token.type == 'error':
                raise ValueError('invalid SVG style')
            if token.type == 'at-rule':
                raise ValueError('SVG style cannot load external stylesheets')
            if token.type == 'url' and not (token.value.startswith('#') or urlsplit(token.value).scheme == 'data'):
                raise ValueError('SVG style resource must be embedded')
            if token.type == 'function':
                if token.lower_name == 'url':
                    args = [x for x in token.arguments if x.type not in {'whitespace','comment'}]
                    if len(args) != 1 or args[0].type != 'string' or not (args[0].value.startswith('#') or urlsplit(args[0].value).scheme == 'data'):
                        raise ValueError('SVG style resource must be embedded')
                else:
                    visit(token.arguments)
            for attr in ('value', 'content', 'prelude'):
                children = getattr(token, attr, None)
                if isinstance(children, list): visit(children)
    visit(values)
