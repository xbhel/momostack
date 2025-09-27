import unittest

from linkgen.utils.text_util import (
    fullwidth_to_halfwidth,
    is_balanced_symbols,
    remove_all_whitespaces,
    to_ascii,
    unescape_html_entities,
    strip_equivalent_symbols,
)


class TestTextUtil(unittest.TestCase):
    def test_to_ascii_basic_mapping(self) -> None:
        self.assertEqual(to_ascii("“Hello—World”"), '"Hello-World"')

    def test_remove_all_whitespaces(self) -> None:
        self.assertEqual(remove_all_whitespaces(" a\t b\n\u2007c \u3000"), "abc")

    def test_fullwidth_to_halfwidth_letters_and_spaces(self) -> None:
        # Full-width A (FF21) should remain as is (not in FF01-FF5E), but punctuation converts
        self.assertEqual(fullwidth_to_halfwidth("Ａ！＃＠ ＂"), 'A!#@ "')

    def test_unescape_html_entities_recursively(self) -> None:
        self.assertEqual(unescape_html_entities("&amp;amp;"), "&")
        self.assertEqual(
            unescape_html_entities("&amp;amp;", max_unescape_times=1), "&amp;"
        )

    def test_strip_equivalent_symbols_uses_variants_table(self) -> None:
        # Should strip ASCII quotes and their typographic variants
        text = "“Hello”"
        self.assertEqual(strip_equivalent_symbols(text, '"'), "Hello")

    def test_is_balanced_symbols_simple_parentheses(self) -> None:
        self.assertTrue(is_balanced_symbols("(a(b)c)", ("(", ")")))
        self.assertTrue(is_balanced_symbols("<p><q>xxx</p></q>", ("<", ">")))
        self.assertFalse(is_balanced_symbols("(a(b)c", ("(", ")")))

    def test_is_balanced_symbols_custom_tokens(self) -> None:
        self.assertTrue(is_balanced_symbols("<<a<<b>>c>>", ("<<", ">>")))
        self.assertFalse(is_balanced_symbols("<<a<<b>>", ("<<", ">>")))

    def test_is_balanced_symbols_quotes_identical_left_right(self) -> None:
        self.assertTrue(is_balanced_symbols('"a "b" c"', ('"', '"')))
        self.assertFalse(is_balanced_symbols('"a "b c"', ('"', '"')))

    def test_is_balanced_symbols_slice_bounds_and_empty(self) -> None:
        s = "(ab)(cd)"
        self.assertTrue(is_balanced_symbols(s, ("(", ")"), start=0, end=4))  # (ab)
        self.assertTrue(
            is_balanced_symbols(s, ("(", ")"), start=2, end=2)
        )  # empty selection


if __name__ == "__main__":
    unittest.main()
