import html
import re
from collections import deque
from collections.abc import Iterable
from typing import Final

from linkgen.utils import coll_util, io_util

_WHITESPACE_REGEX: Final = re.compile(r"\s+", re.UNICODE)
_ASCII_MAPPING_TABLE: dict[str, str] = io_util.load_resource_json("AsciiMapping.json")
_ASCII_TRANS_TABLE: Final = {ord(k): v for k, v in _ASCII_MAPPING_TABLE.items()}
_ASCII_TO_VARIANTS: Final = coll_util.reverse_dict(_ASCII_MAPPING_TABLE)


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


def replace_all_whitespaces(text: str, replacement: str) -> str:
    """
    Replace all Unicode whitespace characters with the given replacement string.
    """
    return _WHITESPACE_REGEX.sub(replacement, text)


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


def strip_equivalents(
    text: str, symbol: str, variants: Iterable[str] | None = None
) -> str:
    equivalents = get_equivalents(symbol)
    if variants:
        equivalents.update(variants)
    return text.strip("".join(equivalents))


def get_equivalents(symbol: str) -> set[str]:
    equivalents = {symbol}
    if symbols := _ASCII_TO_VARIANTS.get(symbol):
        equivalents.update(symbols)
    return equivalents


def split_by_equivalents(text: str, delimiter: str) -> list[str]:
    equivalents = get_equivalents(delimiter)
    trans_table = {ord(x): delimiter for x in equivalents}
    text = text.translate(trans_table)
    return text.split(delimiter)


def has_any_equivalents(
    text: str, symbol: str, start: int = 0, end: int | None = None
) -> int:
    if end is None:
        end = len(text)
    if start > end:
        return False
    for s in get_equivalents(symbol):
        index = text.find(s, start, end)
        if index != -1:
            return True
    return False


def is_whitespace(s: str) -> bool:
    if s.isspace():
        return True
    return s in _ASCII_TO_VARIANTS.get(" ", {})


def is_digit(s: str) -> bool:
    return s.isdigit()


def is_symbol_balanced(
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


def adjust_start_end(
    length: int, start: int, end: int | None = None
) -> tuple[int, int]:
    """
    equivalent:
        adjust_start_end(10, -1, -10) = slice(-1, -10, -1).indices(10) = (9, 0)
        adjust_start_end(10, 0, 10) = slice(1, 10, 1).indices(10) = (0, 10)
    """
    if end is None:
        end = length
    elif end < 0:
        end = end + length
    else:
        end = min(end, length)

    if start < 0:
        start = length + start

    return start, end


def is_numeric(s: str) -> bool:
    return s.isdigit()


def find_last_numeric_suffix(
    text: str, start: int = 0, end: int | None = None
) -> tuple[str, int]:
    start, end = adjust_start_end(len(text), start, end)

    if start >= end:
        return "", -1

    idx = end - 1
    num_chars: list[str] = []
    while idx >= start:
        c = text[idx]
        if not is_numeric(c) and num_chars:
            break
        num_chars.append(c)
        idx -= 1

    if not num_chars:
        return "", -1

    return "".join(reversed(num_chars)), idx + 1
