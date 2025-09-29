import unittest

from linkgen.extractor import CaseNoExtractor
from linkgen.models import Entity, EntityType


class TestCaseNoExtractor(unittest.TestCase):
    def test_extract(self):
        text = "根据（2025）沪0101刑初第682号"
        extractor = CaseNoExtractor()
        entities = list(extractor.extract(text))
        self.assertEqual(
            entities,
            [
                Entity(
                    text="（2025）沪0101刑初第682号",
                    start=2,
                    end=20,
                    entity_type=EntityType.CASE_NO,
                ),
            ],
        )

    def test_multiple_case_nos(self):
        text = "根据（2025）沪0101刑初第682号、第683号"
        extractor = CaseNoExtractor()
        entities = list(extractor.extract(text))
        self.assertEqual(
            entities,
            [
                Entity(
                    text="（2025）沪0101刑初第682号",
                    start=2,
                    end=20,
                    entity_type=EntityType.CASE_NO,
                    alias="（2025）沪0101刑初第682号"
                ),
                Entity(
                    text="683号",
                    start=22,
                    end=26,
                    entity_type=EntityType.CASE_NO,
                    alias="（2025）沪0101刑初第683号"
                ),
            ],
        )