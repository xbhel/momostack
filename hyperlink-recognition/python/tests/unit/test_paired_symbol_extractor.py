import unittest

from recognition.data_model import TextSpan
from recognition.extractor import PairedSymbolExtractor


def to_simple(spans: list[TextSpan]) -> list[tuple[str, int, int]]:
    return [(s.text, s.start, s.end) for s in spans]


class TestPairedSymbolExtractor(unittest.TestCase):
    def test_all_simple_pairs(self) -> None:
        extractor = PairedSymbolExtractor(symbol_pair=("《", "》"), strategy="all")
        text = "A《X》B《Y》C"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("X", 2, 3), ("Y", 6, 7)])

    def test_innermost_with_nesting(self) -> None:
        extractor = PairedSymbolExtractor(symbol_pair=("《", "》"), strategy="innermost")
        text = "《A《B》C》"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("B", 3, 4)])

    def test_outermost_with_nesting(self) -> None:
        extractor = PairedSymbolExtractor(symbol_pair=("《", "》"), strategy="outermost")
        text = "《A《B》C》"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("A《B》C", 1, 6)])

    def test_include_symbols_true(self) -> None:
        extractor = PairedSymbolExtractor(
            symbol_pair=("(", ")"), strategy="all", include_symbols=True
        )
        text = "(a) and (b)"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("(a)", 0, 3), ("(b)", 8, 11)])

    def test_outermost_fallback_to_outermost_closed_when_unclosed(self) -> None:
        # Outer left is unclosed; two inner closed at different times
        extractor = PairedSymbolExtractor(
            symbol_pair=("[", "]"), strategy="outermost", allow_fallback_on_unclosed=True
        )
        text = "[ A [B [C] D] E"  # last ']' for the outermost is missing
        spans = list(extractor.extract(text))
        # Expect the widest closed pair(s) inside the unclosed outer: "B [C] D"
        # Positions: [ at 2, C ] closes at index, then inner B...]
        self.assertEqual(to_simple(spans), [("B [C] D", 5, 12)])

    def test_outermost_fallback_returns_only_widest_level(self) -> None:
        extractor = PairedSymbolExtractor(
            symbol_pair=("<", ">"), strategy="outermost", allow_fallback_on_unclosed=True
        )
        text = "< A <B <C> D> E"  # outermost '>' missing
        spans = list(extractor.extract(text))
        # There are two closed depths: depth=3: C, then depth=2: B <C> D
        # Fallback should return only the outermost closed level (depth=2)
        self.assertEqual(to_simple(spans), [("B <C> D", 5, 12)])

    def test_outermost_no_fallback_when_disabled(self) -> None:
        extractor = PairedSymbolExtractor(
            symbol_pair=("《", "》"), strategy="outermost", allow_fallback_on_unclosed=False
        )
        text = "《A《B》C"  # outermost is unclosed
        spans = list(extractor.extract(text))
        # No result when fallback disabled
        self.assertEqual(spans, [])

    def test_no_matches(self) -> None:
        extractor = PairedSymbolExtractor(symbol_pair=("[", "]"), strategy="all")
        text = "no brackets here"
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_ignores_stray_right_symbol(self) -> None:
        extractor = PairedSymbolExtractor(symbol_pair=("{", "}"), strategy="all")
        text = "} {a} } {b}"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("a", 3, 4), ("b", 9, 10)])


if __name__ == "__main__":
    unittest.main()
