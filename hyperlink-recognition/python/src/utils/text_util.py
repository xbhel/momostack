import html
import re
import unicodedata
from typing import Final

_WHITESPACE_REGEX: Final = re.compile(r"\s+")


def remove_all_whitespaces(text: str) -> str:
    """
    Remove all Unicode whitespace characters and additional invisible/separator
    characters.
    """
    text = unicodedata.normalize('NFC', text)
    # Remove extra, non-standard whitespace-like characters
    extra_whitespaces = (
        "\ufeff",  # ZERO WIDTH NO-BREAK SPACE (BOM)
        "\u202a",  # LEFT-TO-RIGHT EMBEDDING
        "\u0000",  # NULL
        "\u3164",  # HANGUL FILLER
        "\u2800",  # BRAILLE PATTERN BLANK
        "\u180e",  # MONGOLIAN VOWEL SEPARATOR (old whitespace)
    )
    translate_table = {ord(c): '' for c in extra_whitespaces}
    text = text.translate(translate_table)
    return _WHITESPACE_REGEX.sub("", text)


def fullwidth_to_halfwidth(text: str) -> str:
    """
    Convert full-width ASCII forms (FF01-FF5E) to half-width equivalents, and
    normalize common space-like characters to a regular ASCII space.
    """
    fullwidth_spaces = ("\u3000", "\u00a0", "\u2007", "\u202f")
    translate_table = {c: c - 0xFEE0 for c in range(0xFF01, 0xFF5F)}
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
            return text
        text = new_text
    return text


def normalize_quotes_and_brackets(text: str) -> str:
    """
    Normalize various Unicode and typographic quotes and brackets to their ASCII
    equivalents.
    """
    mappings = {
        "{": "\ufe5b\u2774",
        "}": "\ufe5c\u2775",
        "<": "\u3008\u300a\u2329",
        ">": "\u3009\u300b\u232a",
        "(": '[\u3010\u3014\u3016\u3018\u301a\ufe5d\u2772\ufe59\u207d\u208d\u2768\ufd3e',  # noqa: E501
        ")": "]\u3011\u3015\u3017\u3019\u301b\ufe5e\u2773\ufe5a\u207e\u208e\u2769\ufd3f",  # noqa: E501
        "'": "\"\u201c\u201d\u201e\u201f\xab\xbb\u301d\u301e\u301f\u300c\u300d\u300e\u300f\u2018\u201a\u201b",  # noqa: E501
    }
    translate_table = {ord(c): k for k, v in mappings.items() for c in v}
    return text.translate(translate_table)
