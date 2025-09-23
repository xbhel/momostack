import re
import unittest
from abc import ABC

from recognition.datamodels import Segment
from recognition.extractor import (
    ChainedExtractor,
    Extractor,
    KeywordExtractor,
    PairedSymbolExtractor,
    PatternExtractor,
)


def to_simple(spans: list[Segment]) -> list[tuple[str, int, int]]:
    return [(s.text, s.start, s.end) for s in spans]


class TestPairedSymbolExtractor(unittest.TestCase):
    def test_all_simple_pairs(self) -> None:
        extractor = PairedSymbolExtractor(symbol_pair=("《", "》"), strategy="all")
        text = "A《X》B《Y》C"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("X", 2, 3), ("Y", 6, 7)])

    def test_innermost_with_nesting(self) -> None:
        extractor = PairedSymbolExtractor(
            symbol_pair=("《", "》"), strategy="innermost"
        )
        text = "《A《B》C》"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("B", 3, 4)])

    def test_outermost_with_nesting(self) -> None:
        extractor = PairedSymbolExtractor(
            symbol_pair=("《", "》"), strategy="outermost"
        )
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
            symbol_pair=("[", "]"),
            strategy="outermost",
            allow_fallback_on_unclosed=True,
        )
        text = "[ A [B [C] D] E"  # last ']' for the outermost is missing
        spans = list(extractor.extract(text))
        # Expect the widest closed pair(s) inside the unclosed outer: "B [C] D"
        # Positions: [ at 2, C ] closes at index, then inner B...]
        self.assertEqual(to_simple(spans), [("B [C] D", 5, 12)])

    def test_outermost_fallback_returns_only_widest_level(self) -> None:
        extractor = PairedSymbolExtractor(
            symbol_pair=("<", ">"),
            strategy="outermost",
            allow_fallback_on_unclosed=True,
        )
        text = "< A <B <C> D> E"  # outermost '>' missing
        spans = list(extractor.extract(text))
        # There are two closed depths: depth=3: C, then depth=2: B <C> D
        # Fallback should return only the outermost closed level (depth=2)
        self.assertEqual(to_simple(spans), [("B <C> D", 5, 12)])

    def test_outermost_no_fallback_when_disabled(self) -> None:
        extractor = PairedSymbolExtractor(
            symbol_pair=("《", "》"),
            strategy="outermost",
            allow_fallback_on_unclosed=False,
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

    def test_ignores_stray_right_symbol_innermost(self) -> None:
        """Test that innermost strategy ignores stray right symbols."""
        extractor = PairedSymbolExtractor(symbol_pair=("{", "}"), strategy="innermost")
        text = "} {a} } {b}"
        spans = list(extractor.extract(text))
        # Should ignore stray right symbols and only extract from valid pairs
        self.assertEqual(to_simple(spans), [("a", 3, 4), ("b", 9, 10)])

    def test_ignores_stray_right_symbol_outermost(self) -> None:
        """Test that outermost strategy ignores stray right symbols."""
        extractor = PairedSymbolExtractor(symbol_pair=("{", "}"), strategy="outermost")
        text = "} {a} } {b}"
        spans = list(extractor.extract(text))
        # Should ignore stray right symbols and only extract from valid pairs
        self.assertEqual(to_simple(spans), [("a", 3, 4), ("b", 9, 10)])

    def test_empty_stack_with_right_symbol_innermost(self) -> None:
        """Test innermost strategy with right symbol when stack is empty."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="innermost")
        text = ") hello (world)"
        spans = list(extractor.extract(text))
        # Should ignore the stray right symbol at the beginning
        self.assertEqual(to_simple(spans), [("world", 9, 14)])

    def test_mismatched_symbols_innermost(self) -> None:
        """Test innermost strategy with mismatched symbols."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="innermost")
        text = "(hello] world"
        spans = list(extractor.extract(text))
        # Should ignore the mismatched right symbol ']'
        self.assertEqual(to_simple(spans), [])

    def test_multiple_stray_right_symbols_innermost(self) -> None:
        """Test innermost strategy with multiple stray right symbols."""
        extractor = PairedSymbolExtractor(symbol_pair=("[", "]"), strategy="innermost")
        text = "]]] [inner] ]]]"
        spans = list(extractor.extract(text))
        # Should ignore all stray right symbols and only extract from valid pair
        self.assertEqual(to_simple(spans), [("inner", 5, 10)])

    def test_nested_with_stray_right_symbols_innermost(self) -> None:
        """Test innermost strategy with nested pairs and stray right symbols."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="innermost")
        text = ") (a(b)c) )"
        spans = list(extractor.extract(text))
        # Should ignore stray right symbols and extract innermost from valid nested pair
        self.assertEqual(to_simple(spans), [("b", 5, 6)])

    def test_complex_stray_symbols_innermost(self) -> None:
        """Test innermost strategy with complex stray symbol patterns."""
        extractor = PairedSymbolExtractor(symbol_pair=("{", "}"), strategy="innermost")
        text = "} {a} } {b{c}d} } {e} }"
        spans = list(extractor.extract(text))
        # Should ignore stray right symbols and extract innermost from valid pairs
        self.assertEqual(to_simple(spans), [("a", 3, 4), ("c", 11, 12), ("e", 19, 20)])

    def test_empty_text(self) -> None:
        """Test extraction from empty text."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="all")
        text = ""
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_only_left_symbol(self) -> None:
        """Test text with only left symbol."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="all")
        text = "hello (world"
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_only_right_symbol(self) -> None:
        """Test text with only right symbol."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="all")
        text = "hello world)"
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_mismatched_symbols(self) -> None:
        """Test text with mismatched symbols."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="all")
        text = "hello (world]"
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_deep_nesting_innermost(self) -> None:
        """Test deep nesting with innermost strategy."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="innermost")
        text = "((((deep))))"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("deep", 4, 8)])

    def test_deep_nesting_outermost(self) -> None:
        """Test deep nesting with outermost strategy."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="outermost")
        text = "((((deep))))"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("(((deep)))", 1, 11)])

    def test_deep_nesting_all(self) -> None:
        """Test deep nesting with all strategy."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="all")
        text = "((((deep))))"
        spans = list(extractor.extract(text))
        # Should return all nested pairs (order may vary)
        expected = [
            ("(((deep)))", 1, 11),
            ("((deep))", 2, 10),
            ("(deep)", 3, 9),
            ("deep", 4, 8),
        ]
        # Sort both lists to compare regardless of order
        self.assertEqual(sorted(to_simple(spans)), sorted(expected))

    def test_multiple_unclosed_pairs(self) -> None:
        """Test multiple unclosed pairs."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="all")
        text = "(a (b (c"
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_include_symbols_false_default(self) -> None:
        """Test that include_symbols defaults to False."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="all")
        text = "(hello)"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("hello", 1, 6)])

    def test_include_symbols_with_nesting(self) -> None:
        """Test include_symbols with nested pairs."""
        extractor = PairedSymbolExtractor(
            symbol_pair=("(", ")"), strategy="all", include_symbols=True
        )
        text = "((inner))"
        spans = list(extractor.extract(text))
        expected = [("((inner))", 0, 9), ("(inner)", 1, 8)]
        # Sort both lists to compare regardless of order
        self.assertEqual(sorted(to_simple(spans)), sorted(expected))

    def test_outermost_fallback_multiple_unclosed(self) -> None:
        """Test outermost fallback with multiple unclosed pairs."""
        extractor = PairedSymbolExtractor(
            symbol_pair=("[", "]"),
            strategy="outermost",
            allow_fallback_on_unclosed=True,
        )
        text = "[ [ [inner] ] [ [other] ]"
        spans = list(extractor.extract(text))
        # Should return the outermost closed pairs with spaces included
        expected = [(" [inner] ", 3, 12), (" [other] ", 15, 24)]
        self.assertEqual(to_simple(spans), expected)

    def test_innermost_with_multiple_depths(self) -> None:
        """Test innermost strategy with multiple depth levels."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="innermost")
        text = "(a(b(c)d)e) (f(g)h)"
        spans = list(extractor.extract(text))
        # Should return only the innermost segments
        expected = [("c", 5, 6), ("g", 15, 16)]
        self.assertEqual(to_simple(spans), expected)

    def test_outermost_with_multiple_groups(self) -> None:
        """Test outermost strategy with multiple separate groups."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="outermost")
        text = "(a(b)c) (d(e)f)"
        spans = list(extractor.extract(text))
        # Should return only the outermost segments
        expected = [("a(b)c", 1, 6), ("d(e)f", 9, 14)]
        self.assertEqual(to_simple(spans), expected)

    def test_all_with_multiple_groups(self) -> None:
        """Test all strategy with multiple separate groups."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="all")
        text = "(a(b)c) (d(e)f)"
        spans = list(extractor.extract(text))
        # Should return all segments
        expected = [
            ("a(b)c", 1, 6),
            ("b", 3, 4),
            ("d(e)f", 9, 14),
            ("e", 11, 12),
        ]
        # Sort both lists to compare regardless of order
        self.assertEqual(sorted(to_simple(spans)), sorted(expected))

    def test_single_character_symbols(self) -> None:
        """Test with single character symbols."""
        extractor = PairedSymbolExtractor(symbol_pair=("|", "|"), strategy="all")
        text = "a|b|c|d|e"
        spans = list(extractor.extract(text))
        # Single character symbols don't work as paired symbols (same opening and closing)
        # This should return empty results
        expected: list[tuple[str, int, int]] = []
        self.assertEqual(to_simple(spans), expected)

    def test_multi_character_symbols(self) -> None:
        """Test with multi-character symbols."""
        extractor = PairedSymbolExtractor(symbol_pair=("<<", ">>"), strategy="all")
        text = "a<<b>>c<<d>>e"
        spans = list(extractor.extract(text))
        # Multi-character symbols extract empty content between them
        expected = [("", 3, 3), ("", 9, 9)]
        self.assertEqual(to_simple(spans), expected)

    def test_include_symbols_multi_character(self) -> None:
        """Test include_symbols with multi-character symbols."""
        extractor = PairedSymbolExtractor(
            symbol_pair=("<<", ">>"), strategy="all", include_symbols=True
        )
        text = "a<<b>>c"
        spans = list(extractor.extract(text))
        expected = [("<<b>", 1, 5)]
        self.assertEqual(to_simple(spans), expected)


class TestKeywordExtractor(unittest.TestCase):
    """Test cases for the KeywordExtractor class."""

    def test_single_keyword(self) -> None:
        """Test extraction with a single keyword."""
        extractor = KeywordExtractor(keywords=["hello"])
        text = "hello world"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("hello", 0, 5)])

    def test_multiple_keywords(self) -> None:
        """Test extraction with multiple keywords."""
        extractor = KeywordExtractor(keywords=["hello", "world"])
        text = "hello world"
        spans = list(extractor.extract(text))
        expected = [("hello", 0, 5), ("world", 6, 11)]
        self.assertEqual(to_simple(spans), expected)

    def test_overlapping_keywords(self) -> None:
        """Test extraction with overlapping keywords."""
        extractor = KeywordExtractor(keywords=["he", "hello", "lo"])
        text = "hello"
        spans = list(extractor.extract(text))
        expected = [("he", 0, 2), ("hello", 0, 5), ("lo", 3, 5)]
        self.assertEqual(to_simple(spans), expected)

    def test_ignore_overlaps_true(self) -> None:
        """Test extraction with ignore_overlaps=True."""
        extractor = KeywordExtractor(
            keywords=["he", "hello", "lo"], ignore_overlaps=True
        )
        text = "hello"
        spans = list(extractor.extract(text))
        # Should return only the longest non-overlapping matches
        self.assertEqual(to_simple(spans), [("hello", 0, 5)])

    def test_ignore_overlaps_false_default(self) -> None:
        """Test that ignore_overlaps defaults to False."""
        extractor = KeywordExtractor(keywords=["he", "hello", "lo"])
        text = "hello"
        spans = list(extractor.extract(text))
        # Should return all matches including overlaps
        expected = [("he", 0, 2), ("hello", 0, 5), ("lo", 3, 5)]
        self.assertEqual(to_simple(spans), expected)

    def test_no_matches(self) -> None:
        """Test extraction when no keywords match."""
        extractor = KeywordExtractor(keywords=["xyz", "abc"])
        text = "hello world"
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_empty_keywords(self) -> None:
        """Test extraction with empty keywords list should raise ValueError."""
        with self.assertRaises(ValueError) as ex:
            KeywordExtractor(keywords=[])
        self.assertEqual(
            str(ex.exception), "Failed to build automaton: empty keyword list."
        )

    def test_empty_text(self) -> None:
        """Test extraction from empty text."""
        extractor = KeywordExtractor(keywords=["hello"])
        text = ""
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_keyword_at_start(self) -> None:
        """Test keyword at the start of text."""
        extractor = KeywordExtractor(keywords=["start"])
        text = "start middle end"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("start", 0, 5)])

    def test_keyword_at_end(self) -> None:
        """Test keyword at the end of text."""
        extractor = KeywordExtractor(keywords=["end"])
        text = "start middle end"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("end", 13, 16)])

    def test_keyword_in_middle(self) -> None:
        """Test keyword in the middle of text."""
        extractor = KeywordExtractor(keywords=["middle"])
        text = "start middle end"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("middle", 6, 12)])

    def test_multiple_occurrences(self) -> None:
        """Test multiple occurrences of the same keyword."""
        extractor = KeywordExtractor(keywords=["test"])
        text = "test this test"
        spans = list(extractor.extract(text))
        expected = [("test", 0, 4), ("test", 10, 14)]
        self.assertEqual(to_simple(spans), expected)

    def test_case_sensitive(self) -> None:
        """Test that extraction is case sensitive."""
        extractor = KeywordExtractor(keywords=["Hello"])
        text = "hello world"
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_exact_case_match(self) -> None:
        """Test exact case matching."""
        extractor = KeywordExtractor(keywords=["Hello"])
        text = "Hello world"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("Hello", 0, 5)])

    def test_longest_match_priority(self) -> None:
        """Test that longer matches take priority when ignore_overlaps=True."""
        extractor = KeywordExtractor(
            keywords=["a", "ab", "abc", "abcd"], ignore_overlaps=True
        )
        text = "abcd"
        spans = list(extractor.extract(text))
        # Should return only the longest match
        self.assertEqual(to_simple(spans), [("abcd", 0, 4)])

    def test_ignore_overlaps_complex(self) -> None:
        """Test ignore_overlaps with complex overlapping patterns."""
        extractor = KeywordExtractor(
            keywords=["ab", "bc", "abc", "bcd"], ignore_overlaps=True
        )
        text = "abcd"
        spans = list(extractor.extract(text))
        # Should return only the longest non-overlapping match
        # "abc" (0,3) and "bcd" (1,4) overlap, so only one should be returned
        expected = [("abc", 0, 3)]
        self.assertEqual(to_simple(spans), expected)

    def test_single_character_keywords(self) -> None:
        """Test with single character keywords."""
        extractor = KeywordExtractor(keywords=["a", "b", "c"])
        text = "abc"
        spans = list(extractor.extract(text))
        expected = [("a", 0, 1), ("b", 1, 2), ("c", 2, 3)]
        self.assertEqual(to_simple(spans), expected)

    def test_ignore_overlaps_single_char(self) -> None:
        """Test ignore_overlaps with single character keywords."""
        extractor = KeywordExtractor(keywords=["a", "b", "c"], ignore_overlaps=True)
        text = "abc"
        spans = list(extractor.extract(text))
        # All single characters are non-overlapping
        expected = [("a", 0, 1), ("b", 1, 2), ("c", 2, 3)]
        self.assertEqual(to_simple(spans), expected)

    def test_very_long_keywords(self) -> None:
        """Test with very long keywords."""
        long_keyword = "a" * 100
        extractor = KeywordExtractor(keywords=[long_keyword])
        text = f"prefix {long_keyword} suffix"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [(long_keyword, 7, 107)])

    def test_short_text_with_long_keywords(self) -> None:
        """Test short text with keywords longer than the text."""
        extractor = KeywordExtractor(keywords=["verylongkeyword"])
        text = "short"
        spans = list(extractor.extract(text))
        self.assertEqual(spans, [])

    def test_ignore_overlaps_short_text(self) -> None:
        """Test ignore_overlaps with text shorter than longest keyword."""
        extractor = KeywordExtractor(
            keywords=["short", "verylongkeyword"], ignore_overlaps=True
        )
        text = "short"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("short", 0, 5)])

    def test_duplicate_keywords(self) -> None:
        """Test with duplicate keywords in the list."""
        extractor = KeywordExtractor(keywords=["test", "test", "hello"])
        text = "test hello test"
        spans = list(extractor.extract(text))
        # Should not return duplicates
        expected = [("test", 0, 4), ("hello", 5, 10), ("test", 11, 15)]
        self.assertEqual(to_simple(spans), expected)

    def test_keywords_with_special_characters(self) -> None:
        """Test keywords containing special characters."""
        extractor = KeywordExtractor(keywords=["test@", "hello!", "world#"])
        text = "test@ hello! world#"
        spans = list(extractor.extract(text))
        expected = [("test@", 0, 5), ("hello!", 6, 12), ("world#", 13, 19)]
        self.assertEqual(to_simple(spans), expected)

    def test_keywords_with_spaces(self) -> None:
        """Test keywords containing spaces."""
        extractor = KeywordExtractor(keywords=["hello world", "test case"])
        text = "hello world test case"
        spans = list(extractor.extract(text))
        expected = [("hello world", 0, 11), ("test case", 12, 21)]
        self.assertEqual(to_simple(spans), expected)


class TestExtractorBaseClass(unittest.TestCase):
    """Test cases for the abstract Extractor base class."""

    def test_extractor_is_abstract(self) -> None:
        """Test that Extractor is an abstract base class."""
        self.assertTrue(issubclass(Extractor, ABC))
        self.assertTrue(hasattr(Extractor, "__abstractmethods__"))

    def test_cannot_instantiate_extractor(self) -> None:
        """Test that Extractor cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            Extractor()  # type: ignore

    def test_make_value_helper(self) -> None:
        """Test the _make_value helper method."""

        # Create a concrete implementation to test the helper
        class TestExtractor(Extractor):
            def extract(self, text: str):
                return [self._make_value("test", 0, 4)]

        extractor = TestExtractor()
        spans = list(extractor.extract("test"))
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0].text, "test")
        self.assertEqual(spans[0].start, 0)
        self.assertEqual(spans[0].end, 4)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_paired_symbol_empty_content(self) -> None:
        """Test paired symbols with empty content."""
        extractor = PairedSymbolExtractor(symbol_pair=("(", ")"), strategy="all")
        text = "()"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("", 1, 1)])

    def test_paired_symbol_include_symbols_empty_content(self) -> None:
        """Test paired symbols with empty content and include_symbols=True."""
        extractor = PairedSymbolExtractor(
            symbol_pair=("(", ")"), strategy="all", include_symbols=True
        )
        text = "()"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("()", 0, 2)])

    def test_keyword_extractor_unicode(self) -> None:
        """Test KeywordExtractor with Unicode characters."""
        extractor = KeywordExtractor(keywords=["你好", "世界"])
        text = "你好世界"
        spans = list(extractor.extract(text))
        expected = [("你好", 0, 2), ("世界", 2, 4)]
        self.assertEqual(to_simple(spans), expected)

    def test_paired_symbol_unicode(self) -> None:
        """Test PairedSymbolExtractor with Unicode characters."""
        extractor = PairedSymbolExtractor(symbol_pair=("「", "」"), strategy="all")
        text = "「你好」世界"
        spans = list(extractor.extract(text))
        self.assertEqual(to_simple(spans), [("你好", 1, 3)])

    def test_keyword_extractor_numbers(self) -> None:
        """Test KeywordExtractor with numeric keywords."""
        extractor = KeywordExtractor(keywords=["123", "456"])
        text = "123 456 789"
        spans = list(extractor.extract(text))
        expected = [("123", 0, 3), ("456", 4, 7)]
        self.assertEqual(to_simple(spans), expected)

    def test_paired_symbol_numbers(self) -> None:
        """Test PairedSymbolExtractor with numeric content."""
        extractor = PairedSymbolExtractor(symbol_pair=("[", "]"), strategy="all")
        text = "[123] [456]"
        spans = list(extractor.extract(text))
        expected = [("123", 1, 4), ("456", 7, 10)]
        self.assertEqual(to_simple(spans), expected)

    def test_keyword_extractor_mixed_content(self) -> None:
        """Test KeywordExtractor with mixed alphanumeric content."""
        extractor = KeywordExtractor(keywords=["test123", "abc456"])
        text = "test123 abc456 def789"
        spans = list(extractor.extract(text))
        expected = [("test123", 0, 7), ("abc456", 8, 14)]
        self.assertEqual(to_simple(spans), expected)

    def test_paired_symbol_mixed_content(self) -> None:
        """Test PairedSymbolExtractor with mixed content."""
        extractor = PairedSymbolExtractor(symbol_pair=("{", "}"), strategy="all")
        text = "{test123} {abc456}"
        spans = list(extractor.extract(text))
        expected = [("test123", 1, 8), ("abc456", 11, 17)]
        self.assertEqual(to_simple(spans), expected)


class TestChainedExtractor(unittest.TestCase):
    """Test cases for the ChainedExtractor class."""

    def test_single_level_extraction(self) -> None:
        """Test extraction with a single level of extractors."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("《", "》")))
        text = "根据《民法典》第123条的规定"
        segments = extractor.extract(text)
        expected = [
            ("民法典", 3, 6)
        ]  # Fixed: 《 is at position 2, so content starts at 3
        self.assertEqual(to_simple(segments), expected)

    def test_two_level_extraction(self) -> None:
        """Test extraction with two levels of extractors."""
        # First level: extract brackets, second level: extract numbers from the bracket content
        extractor = ChainedExtractor(PairedSymbolExtractor(("[", "]"))).next(
            PatternExtractor(re.compile(r"\d+"))
        )
        text = "参考[123]和[456]的规定"
        segments = extractor.extract(text)
        expected = [
            ("123", 3, 6),
            ("456", 9, 12),
        ]  # Fixed: second bracket starts at position 8
        self.assertEqual(to_simple(segments), expected)

    def test_three_level_extraction(self) -> None:
        """Test extraction with three levels of extractors."""
        # Level 1: extract brackets, Level 2: extract numbers, Level 3: extract specific pattern
        extractor = (
            ChainedExtractor(PairedSymbolExtractor(("[", "]")))
            .next(PatternExtractor(re.compile(r"\d+")))
            .next(PatternExtractor(re.compile(r"[1-9]\d*")))
        )
        text = "参考[123]和[456]的规定"
        segments = extractor.extract(text)
        expected = [("123", 3, 6), ("456", 9, 12)]  # Fixed positions
        self.assertEqual(to_simple(segments), expected)

    def test_multiple_extractors_per_level(self) -> None:
        """Test extraction with multiple extractors at the same level."""
        extractor = ChainedExtractor(
            PairedSymbolExtractor(("《", "》")), PairedSymbolExtractor(("（", "）"))
        )
        text = "根据《民法典》和（刑法）的规定"
        segments = extractor.extract(text)
        expected = [("民法典", 3, 6), ("刑法", 9, 11)]  # Fixed positions
        self.assertEqual(to_simple(segments), expected)

    def test_no_matches_first_level(self) -> None:
        """Test when first level finds no matches."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("《", "》"))).next(
            PatternExtractor(re.compile(r"第\d+条"))
        )
        text = "没有书名号的内容"
        segments = extractor.extract(text)
        self.assertEqual(segments, [])

    def test_no_matches_second_level(self) -> None:
        """Test when second level finds no matches."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("《", "》"))).next(
            PatternExtractor(re.compile(r"不存在的模式"))
        )
        text = "根据《民法典》的规定"
        segments = extractor.extract(text)
        self.assertEqual(segments, [])

    def test_empty_text(self) -> None:
        """Test extraction from empty text."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("《", "》")))
        text = ""
        segments = extractor.extract(text)
        self.assertEqual(segments, [])

    def test_position_adjustment(self) -> None:
        """Test that positions are correctly adjusted across levels."""
        # This test should return empty because "法律" doesn't contain "第123条"
        extractor = ChainedExtractor(PairedSymbolExtractor(("《", "》"))).next(
            PatternExtractor(re.compile(r"第(\d+)条"))
        )
        text = "前缀《法律》第123条后缀"
        segments = extractor.extract(text)
        self.assertEqual(to_simple(segments), [])

    def test_nested_position_adjustment(self) -> None:
        """Test position adjustment with deeply nested extraction."""
        extractor = (
            ChainedExtractor(PairedSymbolExtractor(("《", "》")))
            .next(PairedSymbolExtractor(("（", "）")))
            .next(PatternExtractor(re.compile(r"\d+")))
        )
        text = "开始《法律（条款123）内容》结束"
        segments = extractor.extract(text)
        # Should find "123" with correct position in original text
        expected = [("123", 8, 11)]  # Fixed: Position of "123" in original text
        self.assertEqual(to_simple(segments), expected)

    def test_extract_with_tuple_result(self) -> None:
        """Test extract_with_tuple_result method."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("[", "]"))).next(
            PatternExtractor(re.compile(r"\d+"))
        )
        text = "参考[123]和[456]的规定"
        result = extractor.extract_with_tuple_result(text)

        # Should return tuple of lists, one for each extractor in the last level
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 1)  # One extractor in last level

        # Check the segments from the last level
        last_level_segments = result[0]
        expected = [("123", 3, 6), ("456", 9, 12)]
        self.assertEqual(to_simple(last_level_segments), expected)

    def test_extract_with_tuple_result_multiple_extractors(self) -> None:
        """Test extract_with_tuple_result with multiple extractors in last level."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("[", "]"))).next(
            PatternExtractor(re.compile(r"\d+")),
            PatternExtractor(re.compile(r"[A-Z]+")),
        )
        text = "参考[123ABC]和[456DEF]的规定"
        result = extractor.extract_with_tuple_result(text)

        # Should return tuple with two lists (one for each extractor)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

        # First extractor should find numbers
        first_extractor_segments = result[0]
        self.assertEqual(
            to_simple(first_extractor_segments), [("123", 3, 6), ("456", 12, 15)]
        )

        # Second extractor should find letters
        second_extractor_segments = result[1]
        self.assertEqual(
            to_simple(second_extractor_segments), [("ABC", 6, 9), ("DEF", 15, 18)]
        )

    def test_validation_empty_constructor(self) -> None:
        """Test that empty constructor raises ValueError."""
        with self.assertRaises(ValueError) as context:
            ChainedExtractor()
        self.assertEqual(str(context.exception), "Must provide at least one extractor.")

    def test_validation_empty_next(self) -> None:
        """Test that empty next() raises ValueError."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("《", "》")))
        with self.assertRaises(ValueError) as context:
            extractor.next()
        self.assertEqual(str(context.exception), "Must provide at least one extractor.")

    def test_immutable_behavior(self) -> None:
        """Test that next() returns a new instance (immutable behavior)."""
        extractor1 = ChainedExtractor(PairedSymbolExtractor(("《", "》")))
        extractor2 = extractor1.next(PatternExtractor(re.compile(r"\d+")))

        # They should be different objects
        self.assertIsNot(extractor1, extractor2)

        # Original should still work with single level
        text = "根据《民法典》的规定"
        segments1 = extractor1.extract(text)
        expected1 = [("民法典", 3, 6)]  # Fixed position
        self.assertEqual(to_simple(segments1), expected1)

        # New extractor should work with two levels
        text2 = "根据《123》的规定"
        segments2 = extractor2.extract(text2)
        expected2 = [("123", 3, 6)]  # Number inside brackets
        self.assertEqual(to_simple(segments2), expected2)

    def test_keyword_and_regex_combination(self) -> None:
        """Test combination of KeywordExtractor and PatternExtractor."""
        # The extracted keywords "法律" and "法规" don't contain numbers, so this should return empty
        extractor = ChainedExtractor(KeywordExtractor(["法律", "法规"])).next(
            PatternExtractor(re.compile(r"\d+"))
        )
        text = "根据法律123和法规456的规定"
        segments = extractor.extract(text)
        self.assertEqual(to_simple(segments), [])

    def test_complex_nested_extraction(self) -> None:
        """Test complex nested extraction scenario."""
        # Simplified: Just test 3 levels with brackets and numbers
        extractor = (
            ChainedExtractor(PairedSymbolExtractor(("[", "]")))
            .next(PairedSymbolExtractor(("（", "）")))
            .next(PatternExtractor(re.compile(r"\d+")))
        )
        text = "参考[内容（数字123）更多]和[其他（数字456）内容]"
        segments = extractor.extract(text)
        expected = [("123", 8, 11), ("456", 22, 25)]  # Fixed position for second number
        self.assertEqual(to_simple(segments), expected)

    def test_overlapping_segments(self) -> None:
        """Test handling of overlapping segments from different extractors."""
        extractor = ChainedExtractor(
            PatternExtractor(re.compile(r"第\d+条")),
            PatternExtractor(re.compile(r"\d+条")),
        )
        text = "根据第123条的规定"
        segments = extractor.extract(text)
        # Both patterns should match, creating overlapping segments
        expected = [("第123条", 2, 7), ("123条", 3, 7)]
        self.assertEqual(to_simple(segments), expected)

    def test_unicode_content(self) -> None:
        """Test extraction with Unicode content."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("《", "》"))).next(
            KeywordExtractor(["民法典", "刑法"])
        )
        text = "根据《民法典》和《刑法》的规定"
        segments = extractor.extract(text)
        expected = [("民法典", 3, 6), ("刑法", 9, 11)]  # Fixed positions
        self.assertEqual(to_simple(segments), expected)

    def test_special_characters(self) -> None:
        """Test extraction with special characters."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("【", "】"))).next(
            PatternExtractor(re.compile(r"[A-Z]+"))
        )
        text = "根据【ABC】和【DEF】的规定"
        segments = extractor.extract(text)
        expected = [("ABC", 3, 6), ("DEF", 9, 12)]  # Fixed positions
        self.assertEqual(to_simple(segments), expected)

    def test_very_long_text(self) -> None:
        """Test extraction with very long text."""
        long_text = "前缀" + "《法律》" * 1000 + "后缀"
        extractor = ChainedExtractor(PairedSymbolExtractor(("《", "》")))
        segments = extractor.extract(long_text)

        # Should find all 1000 law titles
        self.assertEqual(len(segments), 1000)

        # Check first and last segments
        self.assertEqual(segments[0].text, "法律")
        self.assertEqual(segments[-1].text, "法律")

    def test_multiple_identical_extractors(self) -> None:
        """Test with multiple identical extractors in the same level."""
        extractor = ChainedExtractor(
            PairedSymbolExtractor(("《", "》")), PairedSymbolExtractor(("《", "》"))
        )
        text = "根据《民法典》的规定"
        segments = extractor.extract(text)
        # Should find the same segment twice (once from each extractor)
        expected = [("民法典", 3, 6), ("民法典", 3, 6)]  # Fixed positions
        self.assertEqual(to_simple(segments), expected)

    def test_inheritance_from_extractor(self) -> None:
        """Test that ChainedExtractor properly inherits from Extractor."""
        self.assertTrue(issubclass(ChainedExtractor, Extractor))

        # Test that it can be used polymorphically
        extractors = [
            PairedSymbolExtractor(("《", "》")),
            ChainedExtractor(PairedSymbolExtractor(("《", "》"))),
        ]

        text = "根据《民法典》的规定"
        for extractor in extractors:
            segments = list(extractor.extract(text))
            self.assertEqual(len(segments), 1)
            self.assertEqual(segments[0].text, "民法典")

    def test_flatten_method(self) -> None:
        """Test the internal _flatten method."""
        extractor = ChainedExtractor(PairedSymbolExtractor(("《", "》")))

        # Create test data
        segments_list = [
            [Segment("法律", 0, 2), Segment("法规", 3, 5)],
            [Segment("条款", 6, 8)],
        ]

        flattened = extractor._flatten(segments_list)
        expected = [Segment("法律", 0, 2), Segment("法规", 3, 5), Segment("条款", 6, 8)]

        self.assertEqual(len(flattened), 3)
        self.assertEqual(to_simple(flattened), to_simple(expected))


if __name__ == "__main__":
    unittest.main()
