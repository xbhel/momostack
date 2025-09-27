"""Unit tests for the normalizer module."""

import unittest

from recognition.normalizer import Normalizer, ChineseLawTitleNormalizer


class TestNormalizer(unittest.TestCase):
    """Test cases for the base Normalizer class."""

    def test_normalize_basic(self):
        """Test basic normalization functionality."""
        normalizer = Normalizer()
        result = normalizer.normalize("  Hello World  ")
        self.assertEqual(result, "Hello World")

    def test_normalize_html_entities(self):
        """Test HTML entity unescaping."""
        normalizer = Normalizer()
        result = normalizer.normalize("&lt;tag&gt;")
        self.assertEqual(result, "<tag>")

    def test_normalize_ascii_conversion(self):
        """Test ASCII conversion."""
        normalizer = Normalizer()
        result = normalizer.normalize('"Hello"')
        self.assertEqual(result, '"Hello"')

    def test_normalize_whitespace_trimming(self):
        """Test whitespace trimming."""
        normalizer = Normalizer()
        result = normalizer.normalize("  \t\n  content  \t\n  ")
        self.assertEqual(result, "content")

    def test_call_method(self):
        """Test that __call__ method works correctly."""
        normalizer = Normalizer()
        result = normalizer("  test  ")
        self.assertEqual(result, "test")

    def test_empty_string(self):
        """Test normalization of empty string."""
        normalizer = Normalizer()
        result = normalizer.normalize("")
        self.assertEqual(result, "")

    def test_whitespace_only_string(self):
        """Test normalization of whitespace-only string."""
        normalizer = Normalizer()
        result = normalizer.normalize("   \t\n   ")
        self.assertEqual(result, "")


class TestChineseLawTitleNormalizer(unittest.TestCase):
    """Test cases for the ChineseLawTitleNormalizer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = ChineseLawTitleNormalizer(['中华人民共和国', '最高人民法院'])

    def test_normalize_basic_law_title(self):
        """Test normalization of basic law title."""
        result = self.normalizer.normalize("中华人民共和国民法典(2020年)")
        self.assertEqual(result, "民法典")

    def test_normalize_complex_law_title(self):
        """Test normalization of complex law title."""
        result = self.normalizer.normalize(
            "最高人民法院关于适用《中华人民共和国公司法》若干问题的规定(一)"
        )
        self.assertEqual(result, "公司法")

    def test_normalize_with_multiple_promulgators(self):
        """Test normalization with multiple promulgators."""
        result = self.normalizer.normalize("中华人民共和国最高人民法院民法典(2020年)")
        self.assertEqual(result, "民法典")

    def test_normalize_with_nested_content(self):
        """Test normalization with nested content."""
        result = self.normalizer.normalize("《民法典》")
        self.assertEqual(result, "民法典")

    def test_normalize_with_forward_chinese(self):
        """Test normalization with forward Chinese content."""
        result = self.normalizer.normalize("转发民法典")
        self.assertEqual(result, "转发民法典")

    def test_normalize_remove_trailing_brackets(self):
        """Test removal of trailing brackets."""
        result = self.normalizer.normalize("民法典(2020年)")
        self.assertEqual(result, "民法典")

    def test_normalize_remove_multiple_trailing_brackets(self):
        """Test removal of multiple trailing brackets."""
        result = self.normalizer.normalize("民法典(2020年)(修订版)")
        self.assertEqual(result, "民法典")

    def test_normalize_remove_leading_promulgators(self):
        """Test removal of leading promulgators."""
        result = self.normalizer.normalize("中华人民共和国, 民法典")
        self.assertEqual(result, "民法典")

    def test_normalize_remove_leading_promulgators_with_brackets(self):
        """Test removal of leading promulgators with brackets."""
        result = self.normalizer.normalize("中华人民共和国(2020年), 民法典")
        self.assertEqual(result, "民法典")

    def test_normalize_remove_leading_promulgators_with_commas(self):
        """Test removal of leading promulgators with commas."""
        result = self.normalizer.normalize("中华人民共和国, 最高人民法院, 民法典")
        self.assertEqual(result, "民法典")

    def test_normalize_empty_input_raises_error(self):
        """Test that empty input raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.normalizer.normalize("")
        self.assertEqual(str(context.exception), "Input text cannot be empty")

    def test_normalize_whitespace_only_input_raises_error(self):
        """Test that whitespace-only input raises ValueError."""
        with self.assertRaises(ValueError) as context:
            self.normalizer.normalize("   \t\n   ")
        self.assertEqual(str(context.exception), "Input text cannot be empty")

    def test_normalize_no_promulgators(self):
        """Test normalization when no promulgators are found."""
        result = self.normalizer.normalize("民法典")
        self.assertEqual(result, "民法典")

    def test_normalize_no_brackets(self):
        """Test normalization when no brackets are found."""
        result = self.normalizer.normalize("民法典")
        self.assertEqual(result, "民法典")

    def test_normalize_complex_nested_structure(self):
        """Test normalization with complex nested structure."""
        result = self.normalizer.normalize("中华人民共和国《民法典》(2020年)(修订版)")
        self.assertEqual(result, "民法典")

    def test_normalize_with_special_characters(self):
        """Test normalization with special characters."""
        result = self.normalizer.normalize("民法典（2020年）")
        self.assertEqual(result, "民法典")

    def test_normalize_unicode_content(self):
        """Test normalization with Unicode content."""
        result = self.normalizer.normalize("中华人民共和国民法典（2020年）")
        self.assertEqual(result, "民法典")

    def test_normalize_very_long_title(self):
        """Test normalization with very long title."""
        long_title = "中华人民共和国" + "最高人民法院" * 10 + "民法典(2020年)"
        result = self.normalizer.normalize(long_title)
        self.assertEqual(result, "民法典")

    def test_normalize_with_mixed_content(self):
        """Test normalization with mixed content types."""
        result = self.normalizer.normalize("中华人民共和国123民法典456(2020年)")
        self.assertEqual(result, "123民法典456")

    def test_normalize_preserve_inner_content(self):
        """Test that inner content is preserved correctly."""
        result = self.normalizer.normalize("中华人民共和国《民法典》")
        self.assertEqual(result, "民法典")

    def test_normalize_handle_edge_cases(self):
        """Test normalization with edge cases."""
        test_cases = [
            ("民法典", "民法典"),
            ("(民法典)", "(民法典)"),
            ("民法典()", "民法典"),
            ("()民法典", "()民法典"),
            ("民法典(2020年)(修订版)", "民法典"),
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = self.normalizer.normalize(input_text)
                self.assertEqual(result, expected)

    def test_normalize_inheritance(self):
        """Test that ChineseLawTitleNormalizer inherits from Normalizer."""
        self.assertIsInstance(self.normalizer, Normalizer)

    def test_normalize_call_method(self):
        """Test that __call__ method works correctly."""
        result = self.normalizer("中华人民共和国民法典(2020年)")
        self.assertEqual(result, "民法典")

    def test_normalize_with_complex_bracket_structure(self):
        """Test normalization with complex bracket structure."""
        result = self.normalizer.normalize("中华人民共和国(2020年)(修订版)民法典(最终版)")
        self.assertEqual(result, "民法典")

    def test_normalize_with_nested_brackets(self):
        """Test normalization with nested brackets."""
        result = self.normalizer.normalize("中华人民共和国((2020年))民法典")
        self.assertEqual(result, "民法典")

    def test_normalize_with_unbalanced_brackets(self):
        """Test normalization with unbalanced brackets."""
        result = self.normalizer.normalize("中华人民共和国民法典(2020年")
        self.assertEqual(result, "民法典(2020年")

    def test_normalize_with_multiple_law_titles(self):
        """Test normalization with multiple law titles."""
        result = self.normalizer.normalize("民法典刑法")
        self.assertEqual(result, "民法典刑法")

    def test_normalize_with_special_promulgators(self):
        """Test normalization with special promulgators."""
        normalizer = ChineseLawTitleNormalizer(['最高', '法院'])
        result = normalizer.normalize("最高法院民法典")
        self.assertEqual(result, "民法典")

    def test_normalize_with_overlapping_promulgators(self):
        """Test normalization with overlapping promulgators."""
        normalizer = ChineseLawTitleNormalizer(['中华', '中华人民共和国'])
        result = normalizer.normalize("中华人民共和国民法典")
        self.assertEqual(result, "民法典")

    def test_normalize_with_duplicate_promulgators(self):
        """Test normalization with duplicate promulgators."""
        normalizer = ChineseLawTitleNormalizer(['中华人民共和国', '中华人民共和国'])
        result = normalizer.normalize("中华人民共和国民法典")
        self.assertEqual(result, "民法典")

    def test_normalize_with_unicode_promulgators(self):
        """Test normalization with Unicode promulgators."""
        normalizer = ChineseLawTitleNormalizer(['中华人民共和国'])
        result = normalizer.normalize("中华人民共和国民法典")
        self.assertEqual(result, "民法典")


if __name__ == "__main__":
    unittest.main()
