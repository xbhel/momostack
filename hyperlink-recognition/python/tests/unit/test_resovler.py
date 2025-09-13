import unittest

from recognition.datamodel import Segment
from recognition.resolver import (
    resolve_overlaps_keep_longest,
    resolve_overlaps_keep_earliest,
)


def to_simple(spans: list[Segment]) -> list[tuple[str, int, int]]:
    return [(s.text, s.start, s.end) for s in spans]


class TestResolveOverlaps(unittest.TestCase):
    def test_keep_longest_no_overlap(self):
        segments = [
            Segment("a", 0, 1),
            Segment("b", 2, 3),
            Segment("c", 4, 5),
        ]
        result = resolve_overlaps_keep_longest(segments)
        self.assertEqual(to_simple(result), [("a", 0, 1), ("b", 2, 3), ("c", 4, 5)])

    def test_keep_longest_simple_overlap(self):
        segments = [
            Segment("a", 0, 3),
            Segment("b", 1, 2),
            Segment("c", 3, 5),
        ]
        result = resolve_overlaps_keep_longest(segments)
        self.assertEqual(to_simple(result), [("a", 0, 3), ("c", 3, 5)])

    def test_keep_longest_multiple_overlap(self):
        segments = [
            Segment("a", 0, 2),
            Segment("b", 1, 5),
            Segment("c", 2, 4),
            Segment("d", 6, 8),
        ]
        result = resolve_overlaps_keep_longest(segments)
        # "a", "b", "c" overlap, keep "b" (longest), then "d"
        self.assertEqual(to_simple(result), [("b", 1, 5), ("d", 6, 8)])

    def test_keep_longest_all_overlap(self):
        segments = [
            Segment("a", 0, 5),
            Segment("b", 1, 4),
            Segment("c", 2, 3),
        ]
        result = resolve_overlaps_keep_longest(segments)
        self.assertEqual(to_simple(result), [("a", 0, 5)])

    def test_keep_longest_empty(self):
        result = resolve_overlaps_keep_longest([])
        self.assertEqual(result, [])

    def test_keep_earliest_no_overlap(self):
        segments = [
            Segment("a", 0, 1),
            Segment("b", 2, 3),
            Segment("c", 4, 5),
        ]
        result = resolve_overlaps_keep_earliest(segments)
        self.assertEqual(to_simple(result), [("a", 0, 1), ("b", 2, 3), ("c", 4, 5)])

    def test_keep_earliest_simple_overlap(self):
        segments = [
            Segment("a", 0, 3),
            Segment("b", 1, 2),
            Segment("c", 3, 5),
        ]
        result = resolve_overlaps_keep_earliest(segments)
        self.assertEqual(to_simple(result), [("a", 0, 3), ("c", 3, 5)])

    def test_keep_earliest_multiple_overlap(self):
        segments = [
            Segment("a", 0, 2),
            Segment("b", 1, 5),
            Segment("c", 2, 4),
            Segment("d", 6, 8),
        ]
        result = resolve_overlaps_keep_earliest(segments)
        # "a" (0,2), "b" (1,5) overlaps with "a", skip, "c" (2,4) does not overlap with "a" (2 >= 2), so keep "c", "d" (6,8) after "c"
        self.assertEqual(to_simple(result), [("a", 0, 2), ("c", 2, 4), ("d", 6, 8)])

    def test_keep_earliest_all_overlap(self):
        segments = [
            Segment("a", 0, 5),
            Segment("b", 1, 4),
            Segment("c", 2, 3),
        ]
        result = resolve_overlaps_keep_earliest(segments)
        self.assertEqual(to_simple(result), [("a", 0, 5)])

    def test_keep_earliest_empty(self):
        result = resolve_overlaps_keep_earliest([])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
