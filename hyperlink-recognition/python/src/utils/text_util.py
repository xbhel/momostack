import html
import re
from typing import Final

from utils.io_util import load_schema_json

_WHITESPACE_REGEX: Final = re.compile(r"\s+", re.UNICODE)
_ASCII_MAPPING_TABLE: Final = load_schema_json("AsciiMapping.json")


def to_ascii(text: str) -> str:
    """
    Normalize various Unicode and typographic quotes, brackets, and
    punctuation to their ASCII equivalents using the loaded mapping table.
    """
    trans_table = {ord(k): str(v) for k, v in _ASCII_MAPPING_TABLE.items()}
    return text.translate(trans_table)


def remove_all_whitespaces(text: str) -> str:
    return _WHITESPACE_REGEX.sub("", text)


def fullwidth_to_halfwidth(text: str) -> str:
    """
    Convert full-width ASCII forms (FF01-FF5E) to half-width equivalents, and
    normalize common space-like characters to a regular ASCII space.
    """
    # Map full-width ASCII to half-width
    translate_table = {c: c - 0xFEE0 for c in range(0xFF01, 0xFF5F)}
    # Map common Unicode space-like characters to ASCII space
    fullwidth_spaces = ("\u3000", "\u00a0", "\u2007", "\u202f")
    translate_table.update({ord(c): ord(' ') for c in fullwidth_spaces})
    return text.translate(translate_table)


def unescape_html_entities(text: str, max_unescape_times: int = 3) -> str:
    """
    Recursively unescape HTML entities until the string stabilizes, with a
    small iteration cap to avoid pathological inputs causing excessive loops.
    """
    for _ in range(max_unescape_times):
        new_text = html.unescape(text)
        if new_text == text:
            break
        text = new_text
    return text
