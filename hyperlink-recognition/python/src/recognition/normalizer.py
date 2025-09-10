import re

from utils import text_util

TITLE_SUFFIX_PATTERN = re.compile(r"^(.+)\(.+\)$")


class Normalizer:
    def normalize(self, text: str) -> str:
        text = text_util.unescape_html_entities(text)
        text = text_util.fullwidth_to_halfwidth(text)
        text = text_util.remove_all_whitespaces(text)
        return text_util.normalize_quotes_and_brackets(text)

    def __call__(self, text: str) -> str:
        return self.normalize(text)

