"""Write every command's text streams as UTF-8, whatever the console locale.

A command's JSON and text reports are UTF-8 by contract. On a host whose locale
is not UTF-8, such as Windows with a Japanese or Western code page, a piped
stream would otherwise use that code page. Japanese text then reaches an agent
garbled, and a character outside the code page stops the command after it has
already saved its work.

Every command calls `configure()` before it does anything else. A module that
another script imports does not call it, so importing never changes a stream.
"""
from __future__ import annotations

import sys


def configure() -> None:
    """Reconfigure standard input, output and error to UTF-8.

    Input stays strict, because a project file that is not UTF-8 is a defect the
    reader must hear about. Output escapes a lone surrogate, the one thing UTF-8
    cannot encode, rather than fail after the work is done.
    """
    for stream, errors in ((sys.stdin, "strict"), (sys.stdout, "backslashreplace"),
                           (sys.stderr, "backslashreplace")):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors=errors)
