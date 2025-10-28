"""Unit tests for the optimized postprocessor module."""

import unittest

from linkgen.resolver import (
    _associate_entities,
    _associate_attributes,
    _associate_ref_definitions,
    _associate_ref_defs_for_dynamic_abbr,
    _without_sentence_ending,
    _startswith_single_left_bracket,
    _skip_leading_whitespace,
    _skip_whitespace_and_tags,
)
from linkgen.models import Entity, EntityType, DocMeta


TEST_METADATA = DocMeta(
    doc_id="law_001",
    doc_type="Legislation",
    doc_url="https://example.com/law_001",
    title="深圳证券交易所章程",
    core_term="章程",
    status="1",
    created_at=1641081600,
    updated_at=1641081600,
    release_date=662659200,
    version="",
    version_timestamp=1641081600,
    promulgators=[],
    effective_status="",
    effective_scope="",
    effective_date=662659200,
)


class TestAssociate(unittest.TestCase):
    """Test the main associate function."""

    def test_empty_entities_returns_unchanged(self):
        """Test that empty entities list returns unchanged."""
        _associate_entities("test text", [], TEST_METADATA)
        # Function modifies entities in-place and returns None

    def test_valid_entities_processed(self):
        """Test that valid entities are processed correctly."""
        text = "Some law (2023)"
        entities = [Entity("Some law", 0, 8, EntityType.LAW_TITLE)]
        _associate_entities(text, entities, TEST_METADATA)
        # Function modifies entities in-place and returns None

    def test_entities_with_dependencies_processed(self):
        """Test that entities with dependencies are processed."""
        text = "Law Title (2023)"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        date = Entity("2023", 11, 15, EntityType.DATE)
        entities = [law_title, date]

        _associate_entities(text, entities, TEST_METADATA)
        # The law title should have the date as an attribute
        self.assertIsNotNone(law_title.attrs)
        self.assertIn(date, law_title.attrs)


class TestAssociateAttributes(unittest.TestCase):
    """Test the _associate_attributes function."""

    def test_forward_association_with_date(self):
        """Test forward association with date attribute."""
        text = "Law Title (2023)"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        date = Entity("2023", 11, 15, EntityType.DATE)

        _associate_attributes(text, [law_title], iter([date]))

        self.assertIsNotNone(law_title.attrs)
        self.assertIn(date, law_title.attrs)

    def test_forward_association_with_issue_no(self):
        """Test forward association with issue number."""
        text = "Law Title (No. 123)"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        issue_no = Entity("No. 123", 11, 18, EntityType.ISSUE_NO)

        _associate_attributes(text, [law_title], iter([issue_no]))

        self.assertIsNotNone(law_title.attrs)
        self.assertIn(issue_no, law_title.attrs)

    def test_backward_association(self):
        """Test backward association."""
        text = "2023 Law Title"
        date = Entity("2023", 0, 4, EntityType.DATE)
        law_title = Entity("Law Title", 5, 13, EntityType.LAW_TITLE)

        _associate_attributes(text, [law_title], iter([date]))

        self.assertIsNotNone(law_title.attrs)
        self.assertIn(date, law_title.attrs)

    def test_no_association_with_sentence_ending(self):
        """Test that no association occurs across sentence endings."""
        text = "Law Title. 2023"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        date = Entity("2023", 11, 15, EntityType.DATE)

        _associate_attributes(text, [law_title], iter([date]))

        # Should not associate across sentence ending
        self.assertEqual(len(law_title.attrs), 0)

    def test_no_association_without_bracket(self):
        """Test that forward association requires bracket."""
        text = "Law Title 2023"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        date = Entity("2023", 10, 14, EntityType.DATE)

        _associate_attributes(text, [law_title], iter([date]))

        # Should not associate without bracket
        self.assertEqual(len(law_title.attrs), 0)


class TestAssociateReferences(unittest.TestCase):
    """Test the _associate_references function."""

    def test_basic_reference_association(self):
        """Test basic reference association."""
        text = "Law Title Article 1"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        article = Entity("Article 1", 10, 19, EntityType.LAW_ARTICLE)

        _associate_ref_definitions(text, [article], iter([law_title]))

        self.assertEqual(article.refers_to, law_title)

    def test_no_association_with_sentence_ending(self):
        """Test that no association occurs across sentence endings."""
        text = "Law Title. Article 1"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        article = Entity("Article 1", 11, 20, EntityType.LAW_ARTICLE)

        _associate_ref_definitions(text, [article], iter([law_title]))

        # Should not associate across sentence ending
        self.assertIsNone(article.refers_to)

    def test_no_reference_found(self):
        """Test when no reference is found."""
        text = "Article 1"
        article = Entity("Article 1", 0, 9, EntityType.LAW_ARTICLE)

        _associate_ref_definitions(text, [article], iter([]))

        self.assertIsNone(article.refers_to)


class TestAssociateReferencesForDynamicAbbr(unittest.TestCase):
    """Test the _associate_references_for_dynamic_abbr function."""

    def test_basic_dynamic_abbr_association(self):
        """Test basic dynamic abbreviation association."""
        text = "Law Title (Abbr) Abbr"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        abbr_def = Entity("Abbr", 11, 15, EntityType.LAW_DYNAMIC_ABBR)

        abbr_ref1 = Entity("Abbr", 11, 15, EntityType.LAW_DYNAMIC_ABBR)
        abbr_ref2 = Entity("Abbr", 17, 21, EntityType.LAW_DYNAMIC_ABBR)

        # Set up the existing reference
        abbr_ref1.refers_to = abbr_def
        abbr_ref2.refers_to = abbr_def

        _associate_ref_defs_for_dynamic_abbr(
            text, [abbr_ref1, abbr_ref2], iter([law_title])
        )

        # The abbreviation should now refer to the law title
        self.assertEqual(abbr_ref1.refers_to, law_title)
        self.assertEqual(abbr_ref2.refers_to, law_title)

    def test_missing_definition_raises_error(self):
        """Test that missing definition raises ValueError."""
        text = "Abbr reference"
        abbr_ref = Entity("Abbr reference", 0, 14, EntityType.LAW_DYNAMIC_ABBR)
        # No refers_to set

        with self.assertRaises(ValueError) as context:
            _associate_ref_defs_for_dynamic_abbr(text, [abbr_ref], iter([]))
        self.assertIn(
            "Missing definition for dynamic abbreviation", str(context.exception)
        )


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions."""

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

    def test_without_sentence_ending_with_chinese_ending(self):
        """Test _without_sentence_ending with Chinese sentence ending."""
        text = "这是一个句子。"
        result = _without_sentence_ending(text, 0, len(text))
        self.assertFalse(result)

    def test_startswith_single_left_bracket_valid(self):
        """Test _startswith_single_left_bracket with valid input."""
        text = " (content)"
        result = _startswith_single_left_bracket(text, 0, len(text))
        self.assertTrue(result)

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

    def test_startswith_single_left_bracket_with_tags(self):
        """Test _startswith_single_left_bracket with HTML tags."""
        text = " <div>(content)</div>"
        result = _startswith_single_left_bracket(text, 0, len(text))
        self.assertTrue(result)

    def test_skip_leading_whitespace_no_spaces(self):
        """Test _skip_leading_whitespace with no leading spaces."""
        text = "content"
        result = _skip_leading_whitespace(text, 0, len(text))
        self.assertEqual(result, 0)

    def test_skip_leading_whitespace_with_spaces(self):
        """Test _skip_leading_whitespace with leading spaces."""
        text = "   content"
        result = _skip_leading_whitespace(text, 0, len(text))
        self.assertEqual(result, 3)

    def test_skip_leading_whitespace_all_spaces(self):
        """Test _skip_leading_whitespace with all spaces."""
        text = "   "
        result = _skip_leading_whitespace(text, 0, len(text))
        self.assertEqual(result, 3)

    def test_skip_whitespace_and_tags_no_tag(self):
        """Test _skip_whitespace_and_tags with no tag."""
        text = "content"
        result = _skip_whitespace_and_tags(text, 0, len(text))
        self.assertEqual(result, 0)

    def test_skip_whitespace_and_tags_with_tag(self):
        """Test _skip_whitespace_and_tags with HTML tag."""
        text = "<div>content</div>"
        result = _skip_whitespace_and_tags(text, 0, len(text))
        self.assertEqual(result, 5)  # After <div>

    def test_skip_whitespace_and_tags_incomplete_tag(self):
        """Test _skip_whitespace_and_tags with incomplete tag."""
        text = "<div content"
        result = _skip_whitespace_and_tags(text, 0, len(text))
        self.assertEqual(result, 0)  # No closing >


class TestCompleteWorkflow(unittest.TestCase):
    """Test complete association workflow with multiple entities."""

    def test_complete_association_workflow(self):
        """Test complete association workflow with multiple entities."""
        text = "Civil Code (2020) and Criminal Law (2019)"

        # Create entities
        civil_code = Entity("Civil Code", 0, 10, EntityType.LAW_TITLE)
        criminal_law = Entity("Criminal Law", 22, 34, EntityType.LAW_TITLE)
        date_2020 = Entity("2020", 12, 16, EntityType.DATE)
        date_2019 = Entity("2019", 36, 40, EntityType.DATE)

        entities = [civil_code, criminal_law, date_2020, date_2019]

        # Process associations
        _associate_entities(text, entities, TEST_METADATA)

        # Civil Code should have 2020 date
        self.assertIsNotNone(civil_code.attrs)
        self.assertIn(date_2020, civil_code.attrs)

        # Criminal Law should have 2019 date
        self.assertIsNotNone(criminal_law.attrs)
        self.assertIn(date_2019, criminal_law.attrs)

    def test_complex_nested_structure(self):
        """Test association with complex nested structure."""
        text = "Supreme Court (Judicial Committee) Civil Code (2020)"

        # Create entities
        supreme_court = Entity("Supreme Court", 0, 13, EntityType.PROMULGATOR)
        judicial_committee = Entity(
            "Judicial Committee", 15, 32, EntityType.PROMULGATOR
        )
        civil_code = Entity("Civil Code", 35, 45, EntityType.LAW_TITLE)
        date = Entity("2020", 47, 51, EntityType.DATE)

        entities = [supreme_court, judicial_committee, civil_code, date]

        # Process associations
        _associate_entities(text, entities, TEST_METADATA)

        # Civil Code should have the date
        self.assertIsNotNone(civil_code.attrs)
        self.assertIn(date, civil_code.attrs)

    def test_multiple_law_titles_with_attributes(self):
        """Test association with multiple law titles and attributes."""
        text = "Civil Code (2020), Criminal Law (2019), Administrative Law (2021)"

        # Create entities
        civil_code = Entity("Civil Code", 0, 10, EntityType.LAW_TITLE)
        date_2020 = Entity("2020", 12, 16, EntityType.DATE)
        criminal_law = Entity("Criminal Law", 19, 31, EntityType.LAW_TITLE)
        date_2019 = Entity("2019", 33, 37, EntityType.DATE)
        admin_law = Entity("Administrative Law", 40, 58, EntityType.LAW_TITLE)
        date_2021 = Entity("2021", 60, 64, EntityType.DATE)

        entities = [
            civil_code,
            date_2020,
            criminal_law,
            date_2019,
            admin_law,
            date_2021,
        ]

        # Process associations
        _associate_entities(text, entities, TEST_METADATA)

        # Each law should have its corresponding date
        self.assertIn(date_2020, civil_code.attrs)
        self.assertIn(date_2019, criminal_law.attrs)
        self.assertIn(date_2021, admin_law.attrs)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_text(self):
        """Test association with empty text."""
        entities: list[Entity] = []
        _associate_entities("", entities, TEST_METADATA)
        # Function modifies entities in-place and returns None

    def test_single_entity(self):
        """Test association with single entity."""
        text = "Law Title"
        law_title = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        entities = [law_title]

        _associate_entities(text, entities, TEST_METADATA)
        # No attributes should be added
        self.assertEqual(len(law_title.attrs), 0)

    def test_entities_without_dependencies(self):
        """Test entities without dependencies."""
        text = "Some text"
        entity = Entity("Some text", 0, 9, EntityType.DATE)
        entities = [entity]

        _associate_entities(text, entities, TEST_METADATA)
        # No changes should occur
        self.assertEqual(len(entity.attrs), 0)

    def test_very_long_text(self):
        """Test association with very long text."""
        long_text = "A" * 10000 + " (2020)"
        law_title = Entity("A" * 10000, 0, 10000, EntityType.LAW_TITLE)
        date = Entity("2020", 10002, 10006, EntityType.DATE)
        entities = [law_title, date]

        _associate_entities(long_text, entities, TEST_METADATA)
        self.assertIn(date, law_title.attrs)

    def test_unicode_content(self):
        """Test association with Unicode content."""
        text = "民法典（2020年）"
        law_title = Entity("民法典", 0, 3, EntityType.LAW_TITLE)
        date = Entity("2020年", 4, 9, EntityType.DATE)
        entities = [law_title, date]

        _associate_entities(text, entities, TEST_METADATA)
        self.assertIn(date, law_title.attrs)

    def test_mixed_bracket_types(self):
        """Test association with mixed bracket types."""
        text = "Law Title (2020) and Other Law （2021）"
        law_title1 = Entity("Law Title", 0, 9, EntityType.LAW_TITLE)
        date1 = Entity("2020", 11, 15, EntityType.DATE)
        law_title2 = Entity("Other Law", 21, 30, EntityType.LAW_TITLE)
        date2 = Entity("2021", 32, 36, EntityType.DATE)
        entities = [law_title1, date1, law_title2, date2]

        _associate_entities(text, entities, TEST_METADATA)
        self.assertIn(date1, law_title1.attrs)
        self.assertIn(date2, law_title2.attrs)


if __name__ == "__main__":
    unittest.main()
