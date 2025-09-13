import re
from collections.abc import Iterable

from recognition.extractor import KeywordExtractor
from utils import text_util

SUFFIX_PATTERN = re.compile(r"^(.+)\(.+\)$")
NESTED_TITLE_PATTERN = re.compile(r"^[^<>]+<[^<>]+>[^<>]*$")


class Normalizer:
    def normalize(self, text: str) -> str:
        text = text_util.unescape_html_entities(text)
        text = text_util.to_ascii(text)
        return text.strip()

    def __call__(self, text: str) -> str:
        return self.normalize(text)


class ChineseLawTitleNormalizer(Normalizer):
    """
    Normalize law titles by extracting their core term.

    The normalizer removes optional prefixes, suffixes, or other decorative
    elements from a law title and extracts the minimal expression that
    uniquely identifies the law. This canonical "core term" can be used
    as a stable key in high-performance lookup services for efficient
    retrieval and validation of legal references.

    Examples
    --------
    >>> normalizer = LawTitleNormalizer()
    >>> normalizer.normalize("中华人民共和国民法典（2020年）")
    "民法典"

    >>> normalizer.normalize(
    >>>  "最高人民法院关于适用《中华人民共和国公司法》若干问题的规定（一）")
    "公司法"

    Responsibilities
    ----------------
    - Input: raw law titles, possibly containing noise (prefixes, suffixes, editions).
    - Output: normalized "core term" suitable as a dictionary key or database index.
    - Usage: legal reference lookup, validation, deduplication.
    """  # noqa: RUF002

    def __init__(self, promulgators: Iterable[str]) -> None:
        self._promulgators_extractor = KeywordExtractor(
            promulgators, ignore_overlaps=True
        )

    def normalize(self, text: str) -> str:
        text = super().normalize(text)
        return text_util.remove_all_whitespaces(text)
