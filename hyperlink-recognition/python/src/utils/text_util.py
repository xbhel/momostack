import html
import re
from collections import deque
from collections.abc import Iterable
from typing import Final

from utils.coll_util import reverse_dict
from utils.io_util import load_resource_json

_WHITESPACE_REGEX: Final = re.compile(r"\s+", re.UNICODE)
_ASCII_MAPPING_TABLE: Final[dict[str, str]] = load_resource_json("AsciiMapping.json")
_ASCII_TRANS_TABLE: Final = {ord(k): v for k, v in _ASCII_MAPPING_TABLE.items()}
_ASCII_TO_VARIANTS: Final = reverse_dict(_ASCII_MAPPING_TABLE)


def to_ascii(text: str) -> str:
    """
    Normalize various Unicode and typographic quotes, brackets, and
    punctuation to their ASCII equivalents using the loaded mapping table.
    """
    return text.translate(_ASCII_TRANS_TABLE)


def remove_all_whitespaces(text: str) -> str:
    """
    Remove all Unicode whitespace characters from the input string.

    This function replaces all sequences of whitespace (spaces, tabs, newlines,
    and other Unicode whitespace) with nothing, effectively concatenating all
    non-whitespace characters.
    """
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
    translate_table.update({ord(c): ord(" ") for c in fullwidth_spaces})
    return text.translate(translate_table)


def unescape_html_entities(text: str, max_unescape_times: int = 3) -> str:
    """
    Recursively unescape HTML entities until the string stabilizes, with a
    small iteration cap to avoid pathological inputs causing excessive loops.
    """
    if max_unescape_times <= 0:
        return html.unescape(text)

    for _ in range(max_unescape_times):
        new_text = html.unescape(text)
        if new_text == text:
            break
        text = new_text
    return text


def strip_equivalent_symbols(
    text: str, symbol: str, variants: Iterable[str] | None = None
) -> str:
    equivalents = {symbol}
    if variants:
        equivalents.update(variants)

    if symbols := _ASCII_TO_VARIANTS.get(symbol):
        equivalents.update(symbols)

    return text.strip("".join(equivalents))


def is_balanced_symbols(
    text: str,
    pair: tuple[str, str],
    start: int = 0,
    end: int | None = None,
) -> bool:
    n = len(text)
    if end is None:
        end = n

    start = max(0, min(start, n))
    end = max(0, min(end, n))

    if start >= end:
        return True

    left, right = pair
    # Special case: identical delimiters (e.g. quotes)
    if left == right:
        if len(left) == 1:
            return (text.count(left, start, end) % 2) == 0

        pattern = re.compile(re.escape(left))
        count = sum(1 for _ in pattern.finditer(text, start, end))
        return count % 2 == 0

    stack: deque[str] = deque()
    pattern = re.compile(f"{re.escape(left)}|{re.escape(right)}")

    for matcher in pattern.finditer(text, start, end):
        val = matcher.group()
        if val == left:
            stack.append(val)
        else:
            if not stack:
                return False
            stack.pop()

    return not stack
