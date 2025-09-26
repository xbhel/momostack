"""Unit tests for the associator module."""

import unittest
from unittest.mock import patch

from recognition.associator import (
    associate,
    associate_law_title,
    _startswith_single_left_bracket,
    _without_sentence_ending,
    _move_space_after,
    _move_element_tag_after,
)
from recognition.datamodels import Entity, EntityType


class TestAssociate(unittest.TestCase):
    """Test the main associate function."""

    def test_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        entities = [Entity("test", 0, 4, EntityType.LAW_TITLE)]
        with self.assertRaises(ValueError) as context:
            associate("", entities)
        self.assertIn("Text cannot be empty", str(context.exception))

    def test_empty_entities_returns_unchanged(self):
        """Test that empty entities list returns unchanged."""
        result = associate("test text", [])
        self.assertEqual(list(result), [])

    def test_non_entity_raises_error(self):
        """Test that non-Entity objects raise TypeError."""
        with self.assertRaises(TypeError) as context:
            associate("test", ["not an entity"])
        self.assertIn("Expected Entity", str(context.exception))

    def test_valid_entities_processed(self):
        """Test that valid entities are processed correctly."""
        text = "Some law (2023)"
        entities = [Entity("Some law", 0, 8, EntityType.LAW_TITLE)]
        result = associate(text, entities)
        self.assertEqual(list(result), entities)

    def test_entities_with_dependencies_processed(self):
        """Test that entities with dependencies are processed."""
        text = "Law Title (2023)"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        date = Entity("2023", 11, 15, EntityType.DATE)
        entities = [law_title, date]
        
        result = associate(text, entities)
        self.assertEqual(len(list(result)), 2)
        # The law title should have the date as an attribute
        self.assertIsNotNone(law_title.attrs)
        self.assertIn(date, law_title.attrs or [])

    def test_empty_law_titles_returns_early(self):
        """Test that empty law titles list returns early."""
        # Should not raise any errors
        associate_law_title("test", [], iter([]))

    def test_invalid_entity_bounds_raises_error(self):
        """Test that invalid entity bounds raise ValueError."""
        text = "test"
        invalid_entity = Entity("test", 0, 10, EntityType.LAW_TITLE)  # end > len(text)
        
        with self.assertRaises(ValueError) as context:
            associate_law_title(text, [invalid_entity], iter([]))
        self.assertIn("Invalid entity bounds", str(context.exception))

    def test_forward_association_with_date(self):
        """Test forward association with date attribute."""
        text = "Law Title (2023)"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        date = Entity("2023", 11, 15, EntityType.DATE)
        
        associate_law_title(text, [law_title], iter([date]))
        
        self.assertIsNotNone(law_title.attrs)
        self.assertIn(date, law_title.attrs or [])

    def test_forward_association_with_issue_no(self):
        """Test forward association with issue number."""
        text = "Law Title (No. 123)"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        issue_no = Entity("No. 123", 11, 18, EntityType.ISSUE_NO)
        
        associate_law_title(text, [law_title], iter([issue_no]))
        
        self.assertIsNotNone(law_title.attrs)
        self.assertIn(issue_no, law_title.attrs or [])

    def test_backward_association(self):
        """Test backward association."""
        text = "2023 Law Title"
        date = Entity("2023", 0, 4, EntityType.DATE)
        law_title = Entity("Law Title", 5, 13, EntityType.LAW_TITLE)
        
        associate_law_title(text, [law_title], iter([date]))
        
        self.assertIsNotNone(law_title.attrs)
        self.assertIn(date, law_title.attrs or [])

    def test_invalid_attribute_skipped(self):
        """Test that invalid attributes are skipped."""
        text = "Law Title"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        invalid_attr = Entity("invalid", 0, 20, EntityType.DATE)  # end > len(text)
        
        # Should not raise error, just skip invalid attribute
        associate_law_title(text, [law_title], iter([invalid_attr]))
        
        self.assertIsNone(law_title.attrs)


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

    def test_startswith_single_left_bracket_valid(self):
        """Test _startswith_single_left_bracket with valid input."""
        text = " (content)"
        result = _startswith_single_left_bracket(text, 0, len(text))
        self.assertTrue(result)

    def test_startswith_single_left_bracket_invalid_range(self):
        """Test _startswith_single_left_bracket with invalid range."""
        text = "test"
        result = _startswith_single_left_bracket(text, 5, 10)  # Invalid range
        self.assertFalse(result)

    def test_startswith_single_left_bracket_no_bracket(self):
        """Test _startswith_single_left_bracket with no bracket."""
        text = "content"
        result = _startswith_single_left_bracket(text, 0, len(text))
        self.assertFalse(result)

    def test_startswith_single_left_bracket_multiple_brackets(self):
        """Test _startswith_single_left_bracket with multiple brackets."""
        text = " ((content))"
        result = _startswith_single_left_bracket(text, 0, len(text))
        self.assertFalse(result)

    def test_without_sentence_ending_no_ending(self):
        """Test _without_sentence_ending with no sentence ending."""
        text = "This is a sentence"
        result = _without_sentence_ending(text, 0, len(text))
        self.assertTrue(result)

    def test_without_sentence_ending_with_ending(self):
        """Test _without_sentence_ending with sentence ending."""
        text = "This is a sentence!"
        result = _without_sentence_ending(text, 0, len(text))
        self.assertFalse(result)

    def test_without_sentence_ending_invalid_range(self):
        """Test _without_sentence_ending with invalid range."""
        text = "test"
        result = _without_sentence_ending(text, 5, 10)  # Invalid range
        self.assertTrue(result)  # Invalid range considered as no sentence ending

    def test_move_space_after_no_spaces(self):
        """Test _move_space_after with no leading spaces."""
        text = "content"
        result = _move_space_after(text, 0, len(text))
        self.assertEqual(result, 0)

    def test_move_space_after_with_spaces(self):
        """Test _move_space_after with leading spaces."""
        text = "   content"
        result = _move_space_after(text, 0, len(text))
        self.assertEqual(result, 3)

    def test_move_space_after_invalid_range(self):
        """Test _move_space_after with invalid range."""
        text = "test"
        result = _move_space_after(text, 5, 10)  # Invalid range
        self.assertEqual(result, 10)  # Returns end

    def test_move_element_tag_after_no_tag(self):
        """Test _move_element_tag_after with no tag."""
        text = "content"
        result = _move_element_tag_after(text, 0, len(text))
        self.assertEqual(result, 0)

    def test_move_element_tag_after_with_tag(self):
        """Test _move_element_tag_after with HTML tag."""
        text = "<div>content</div>"
        result = _move_element_tag_after(text, 0, len(text))
        self.assertEqual(result, 5)  # After <div>

    def test_move_element_tag_after_invalid_range(self):
        """Test _move_element_tag_after with invalid range."""
        text = "test"
        result = _move_element_tag_after(text, 5, 10)  # Invalid range
        self.assertEqual(result, 5)  # Returns start

    def test_complete_association_workflow(self):
        """Test complete association workflow with multiple entities."""
        text = "Civil Code (2020) and Criminal Law (2019)"
        
        # Create entities
        civil_code = Entity("Civil Code", 0, 10, EntityType.LAW_TITLE)
        criminal_law = Entity("Criminal Law", 20, 32, EntityType.LAW_TITLE)
        date_2020 = Entity("2020", 12, 16, EntityType.DATE)
        date_2019 = Entity("2019", 34, 38, EntityType.DATE)
        
        entities = [civil_code, criminal_law, date_2020, date_2019]
        
        # Process associations
        result = associate(text, entities)
        
        # Verify results
        self.assertEqual(len(list(result)), 4)
        
        # Civil Code should have 2020 date
        self.assertIsNotNone(civil_code.attrs)
        self.assertIn(date_2020, civil_code.attrs or [])
        
        # Criminal Law should have 2019 date
        self.assertIsNotNone(criminal_law.attrs)
        self.assertIn(date_2019, criminal_law.attrs or [])


if __name__ == "__main__":
    unittest.main()
