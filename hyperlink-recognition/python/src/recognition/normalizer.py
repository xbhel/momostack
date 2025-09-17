from collections.abc import Iterable
from typing import TYPE_CHECKING, Final, cast

from recognition.extractor import KeywordExtractor, PairedSymbolExtractor
from recognition.patterns import patterns
from utils import text_util

if TYPE_CHECKING:
    import re

_COMMA: Final = ","
_LEFT_BRACKET: Final = '('
_RIGHT_BRACKET: Final = ')'
_FORWARD_CHINESE: Final = "转发"
_NESTED_TITLE_PATTERN: Final = cast("re.Pattern[str]", patterns['nested_title'])


class Normalizer:
    """
    Base class for text normalization.

    This class provides basic text normalization functionality including
    HTML entity unescaping, ASCII conversion, and whitespace trimming.
    """

    def normalize(self, text: str) -> str:
        text = text_util.unescape_html_entities(text)
        text = text_util.to_ascii(text)
        return text.strip()

    def __call__(self, text: str) -> str:
        return self.normalize(text)


class ChineseLawTitleNormalizer(Normalizer):
    """
    Normalize Chinese law titles by extracting their core term.

    The normalizer removes optional prefixes, suffixes, or other decorative
    elements from a law title and extracts the minimal expression that
    uniquely identifies the law. This canonical "core term" can be used
    as a stable key in high-performance lookup services for efficient
    retrieval and validation of legal references.

    Args:
        promulgators: List of promulgator keywords to remove from law titles.

    Example::

        normalizer = ChineseLawTitleNormalizer(['中华人民共和国', '最高人民法院'])
        result = normalizer.normalize("中华人民共和国民法典(2020年)")
        # result: "民法典"

        result = normalizer.normalize(
            "最高人民法院关于适用《中华人民共和国公司法》若干问题的规定(一)")
        # result: "公司法"

    Note:
        - Input: raw law titles, possibly containing noise (prefixes, suffixes).
        - Output: normalized "core term" suitable as a dictionary key or database index.
        - Usage: legal reference lookup, validation, deduplication.
    """

    _bracket_extractor = PairedSymbolExtractor(
        (_LEFT_BRACKET, _RIGHT_BRACKET),
        include_symbols=True,
        strategy='outermost',
        allow_fallback_on_unclosed=True,
    )

    def __init__(self, promulgators: Iterable[str]) -> None:
        self._promulgator_extractor = KeywordExtractor(
            promulgators, ignore_overlaps=True
        )

    def normalize(self, text: str) -> str:
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty")

        text = super().normalize(text)
        text = text_util.remove_all_whitespaces(text)
        text = self._extract_nested_text(text)

        # remove prefixes
        text = self._remove_promulgators(text)
        # remove suffixes
        return self._remove_trailing_brackets(text)

    def _extract_nested_text(self, text: str) -> str:
        if text.find(_FORWARD_CHINESE) != -1:
            return text
        if matcher := _NESTED_TITLE_PATTERN.match(text):
            return matcher.group(1)
        return text

    def _remove_trailing_brackets(self, text: str) -> str:
        """Remove trailing brackets from the end of the text."""
        if not text.endswith(_RIGHT_BRACKET):
            return text

        end_index = len(text)
        brackets = self._bracket_extractor.extract(text)
        end_map = {x.end: x for x in brackets}

        # Remove brackets from the end, working backwards
        while bracket := end_map.get(end_index):
            end_index = bracket.start

        if end_index == 0:
            return text

        return text[:end_index]

    def _remove_promulgators(self, text: str) -> str:
        """
        Remove promulgator keywords and their associated descriptions
        enclosed in brackets from the text
        """
        promulgators = self._promulgator_extractor.extract(text)
        promulgators = sorted(promulgators, key=lambda x: x.start)
        if not promulgators:
            return text

        brackets = self._bracket_extractor.extract(text)
        start_map = {x.start: x for x in brackets}

        start_index = 0
        for item in promulgators:
            # Discontinuous promulgators
            if item.start > start_index:
                break
            # It is a part of the description of the previous promulgator
            if item.start < start_index:
                continue

            start_index = item.end
            # Move past any immediately following brackets
            while bracket := start_map.get(start_index):
                start_index = bracket.end
            # Skip trailing commas
            while start_index < len(text) and text[start_index] == _COMMA:
                start_index += 1

        if start_index == len(text):
            return text

        return text[start_index:]
