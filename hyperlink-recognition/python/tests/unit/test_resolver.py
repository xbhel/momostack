import unittest
from typing import Literal

from recognition.datamodels import Segment
from recognition.resolver import resolve_overlaps


def to_simple(segments: list[Segment]) -> list[tuple[str, int, int]]:
    """Helper function to convert segments to simple tuples for easier testing."""
    return [(s.text, s.start, s.end) for s in segments]


class TestResolveOverlaps(unittest.TestCase):
    """Test cases for the resolve_overlaps function."""

    def test_empty_input(self) -> None:
        """Test that empty input returns empty list."""
        result = resolve_overlaps([], "longest")
        self.assertEqual(result, [])

    def test_single_segment(self) -> None:
        """Test that single segment is returned unchanged."""
        segment = Segment("test", 0, 5)
        result = resolve_overlaps([segment], "longest")
        self.assertEqual(result, [segment])

    def test_no_overlaps(self) -> None:
        """Test segments with no overlaps are all returned."""
        segments = [
            Segment("a", 0, 3),
            Segment("b", 5, 8),
            Segment("c", 10, 13),
        ]
        result = resolve_overlaps(segments, "longest")
        self.assertEqual(to_simple(result), [("a", 0, 3), ("b", 5, 8), ("c", 10, 13)])

    def test_invalid_strategy_raises_error(self) -> None:
        """Test that invalid strategy raises appropriate error."""
        segments = [Segment("test", 0, 5)]
        with self.assertRaises(UnboundLocalError):
            resolve_overlaps(segments, "invalid_strategy")  # type: ignore


class TestLongestStrategy(unittest.TestCase):
    """Test cases for the 'longest' strategy."""

    def test_longest_basic_overlap(self) -> None:
        """Test basic overlap resolution keeping longest segment."""
        segments = [
            Segment("short", 0, 3),
            Segment("longer", 2, 8),
        ]
        result = resolve_overlaps(segments, "longest")
        self.assertEqual(to_simple(result), [("longer", 2, 8)])

    def test_longest_multiple_overlaps(self) -> None:
        """Test multiple overlapping segments keeping longest."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 4, 7),
            Segment("c", 6, 10),
        ]
        result = resolve_overlaps(segments, "longest")
        # All segments overlap in a chain, keep the longest one (a has length 5)
        self.assertEqual(to_simple(result), [("a", 0, 5)])

    def test_longest_chain_overlaps(self) -> None:
        """Test chained overlaps with longest strategy."""
        segments = [
            Segment("a", 0, 3),
            Segment("b", 2, 5),
            Segment("c", 4, 7),
            Segment("d", 6, 9),
        ]
        result = resolve_overlaps(segments, "longest")
        # All segments overlap in a chain, keep the longest one (all have length 3, so keep first)
        self.assertEqual(to_simple(result), [("a", 0, 3)])

    def test_longest_direct_only_true(self) -> None:
        """Test longest strategy with direct_only=True."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 4, 7),
            Segment("c", 6, 10),
        ]
        result = resolve_overlaps(segments, "longest", direct_only=True)
        # Only direct overlaps considered: (a,b) and (b,c) separately
        # Between a(0-5) and b(4-7): keep a (longer)
        # Between b(4-7) and c(6-10): keep c (longer)
        self.assertEqual(to_simple(result), [("a", 0, 5), ("c", 6, 10)])

    def test_longest_direct_only_false(self) -> None:
        """Test longest strategy with direct_only=False (default)."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 4, 7),
            Segment("c", 6, 10),
        ]
        result = resolve_overlaps(segments, "longest", direct_only=False)
        # All segments form one overlapping chain, keep the longest (a has length 5)
        self.assertEqual(to_simple(result), [("a", 0, 5)])

    def test_longest_tie_breaking(self) -> None:
        """Test longest strategy when segments have same length."""
        segments = [
            Segment("a", 0, 3),
            Segment("b", 2, 5),
        ]
        result = resolve_overlaps(segments, "longest")
        # Both have same length, should keep the first one (earliest start)
        self.assertEqual(to_simple(result), [("a", 0, 3)])

    def test_longest_unsorted_input(self) -> None:
        """Test that input is properly sorted before processing."""
        segments = [
            Segment("c", 6, 10),
            Segment("a", 0, 5),
            Segment("b", 4, 7),
        ]
        result = resolve_overlaps(segments, "longest")
        # Should be sorted by start position first, then longest selected (a has length 5)
        self.assertEqual(to_simple(result), [("a", 0, 5)])


class TestEarliestStrategy(unittest.TestCase):
    """Test cases for the 'earliest' strategy."""

    def test_earliest_basic_overlap(self) -> None:
        """Test basic overlap resolution keeping earliest segment."""
        segments = [
            Segment("first", 0, 5),
            Segment("second", 3, 8),
        ]
        result = resolve_overlaps(segments, "earliest")
        self.assertEqual(to_simple(result), [("first", 0, 5)])

    def test_earliest_multiple_overlaps(self) -> None:
        """Test multiple overlapping segments keeping earliest."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 4, 7),
            Segment("c", 6, 10),
        ]
        result = resolve_overlaps(segments, "earliest")
        # All segments overlap in a chain, keep only the first (earliest)
        self.assertEqual(to_simple(result), [("a", 0, 5)])

    def test_earliest_chain_overlaps(self) -> None:
        """Test chained overlaps with earliest strategy."""
        segments = [
            Segment("a", 0, 3),
            Segment("b", 2, 5),
            Segment("c", 4, 7),
            Segment("d", 6, 9),
        ]
        result = resolve_overlaps(segments, "earliest")
        # All segments overlap in a chain, keep only the first (earliest)
        self.assertEqual(to_simple(result), [("a", 0, 3)])

    def test_earliest_direct_only_true(self) -> None:
        """Test earliest strategy with direct_only=True."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 4, 7),
            Segment("c", 6, 10),
        ]
        result = resolve_overlaps(segments, "earliest", direct_only=True)
        # Only direct overlaps considered
        self.assertEqual(to_simple(result), [("a", 0, 5), ("c", 6, 10)])

    def test_earliest_direct_only_false(self) -> None:
        """Test earliest strategy with direct_only=False (default)."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 4, 7),
            Segment("c", 6, 10),
        ]
        result = resolve_overlaps(segments, "earliest", direct_only=False)
        # All segments form one overlapping chain, keep only the first
        self.assertEqual(to_simple(result), [("a", 0, 5)])

    def test_earliest_no_overlaps(self) -> None:
        """Test earliest strategy with no overlapping segments."""
        segments = [
            Segment("a", 0, 3),
            Segment("b", 5, 8),
            Segment("c", 10, 13),
        ]
        result = resolve_overlaps(segments, "earliest")
        self.assertEqual(to_simple(result), [("a", 0, 3), ("b", 5, 8), ("c", 10, 13)])

    def test_earliest_adjacent_segments(self) -> None:
        """Test earliest strategy with adjacent (non-overlapping) segments."""
        segments = [
            Segment("a", 0, 3),
            Segment("b", 3, 6),
            Segment("c", 6, 9),
        ]
        result = resolve_overlaps(segments, "earliest")
        # Adjacent segments don't overlap, all should be kept
        self.assertEqual(to_simple(result), [("a", 0, 3), ("b", 3, 6), ("c", 6, 9)])


class TestEarliestLongestStrategy(unittest.TestCase):
    """Test cases for the 'earliest_longest' strategy."""

    def test_earliest_longest_basic(self) -> None:
        """Test basic earliest_longest strategy."""
        segments = [
            Segment("short", 0, 3),
            Segment("longer", 0, 8),
        ]
        result = resolve_overlaps(segments, "earliest_longest")
        # Same start position, keep the longer one
        self.assertEqual(to_simple(result), [("longer", 0, 8)])

    def test_earliest_longest_different_starts(self) -> None:
        """Test earliest_longest with different start positions."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 2, 7),
            Segment("c", 4, 9),
        ]
        result = resolve_overlaps(segments, "earliest_longest")
        # All segments overlap in a chain, keep only the first (earliest)
        self.assertEqual(to_simple(result), [("a", 0, 5)])

    def test_earliest_longest_tie_breaking(self) -> None:
        """Test earliest_longest tie breaking (earliest first, then longest)."""
        segments = [
            Segment("a", 0, 3),
            Segment("b", 0, 5),
            Segment("c", 2, 4),
        ]
        result = resolve_overlaps(segments, "earliest_longest")
        # Among segments starting at 0, keep the longest (b)
        # Then check if c overlaps with b
        self.assertEqual(to_simple(result), [("b", 0, 5)])

    def test_earliest_longest_direct_only_true(self) -> None:
        """Test earliest_longest strategy with direct_only=True."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 4, 7),
            Segment("c", 6, 10),
        ]
        result = resolve_overlaps(segments, "earliest_longest", direct_only=True)
        # Only direct overlaps considered
        self.assertEqual(to_simple(result), [("a", 0, 5), ("c", 6, 10)])

    def test_earliest_longest_direct_only_false(self) -> None:
        """Test earliest_longest strategy with direct_only=False (default)."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 4, 7),
            Segment("c", 6, 10),
        ]
        result = resolve_overlaps(segments, "earliest_longest", direct_only=False)
        # All segments form one overlapping chain, keep only the first
        self.assertEqual(to_simple(result), [("a", 0, 5)])


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_zero_length_segments(self) -> None:
        """Test segments with zero length."""
        segments = [
            Segment("a", 0, 0),
            Segment("b", 0, 5),
        ]
        result = resolve_overlaps(segments, "longest")
        # Zero-length segment at position 0 does not overlap with (0,5)
        # since zero-length segments have no actual content
        # Both segments should be kept
        self.assertEqual(to_simple(result), [("a", 0, 0), ("b", 0, 5)])

    def test_negative_positions(self) -> None:
        """Test segments with negative positions."""
        segments = [
            Segment("a", -5, -2),
            Segment("b", -3, 0),
        ]
        result = resolve_overlaps(segments, "longest")
        # Should handle negative positions correctly
        # a has length 3, b has length 3, keep first (a)
        self.assertEqual(to_simple(result), [("a", -5, -2)])

    def test_very_large_positions(self) -> None:
        """Test segments with very large positions."""
        segments = [
            Segment("a", 1000000, 1000005),
            Segment("b", 1000003, 1000008),
        ]
        result = resolve_overlaps(segments, "longest")
        # Should handle large numbers correctly
        # Both have length 5, keep first (a)
        self.assertEqual(to_simple(result), [("a", 1000000, 1000005)])

    def test_identical_segments(self) -> None:
        """Test identical segments."""
        segments = [
            Segment("a", 0, 5),
            Segment("a", 0, 5),
        ]
        result = resolve_overlaps(segments, "longest")
        # Identical segments should be deduplicated to one segment
        self.assertEqual(to_simple(result), [("a", 0, 5)])

    def test_contained_segments(self) -> None:
        """Test one segment completely contained within another."""
        segments = [
            Segment("outer", 0, 10),
            Segment("inner", 3, 7),
        ]
        result = resolve_overlaps(segments, "longest")
        # Should keep the longer (outer) segment
        self.assertEqual(to_simple(result), [("outer", 0, 10)])

    def test_contained_segments_earliest_strategy(self) -> None:
        """Test contained segments with earliest strategy."""
        segments = [
            Segment("outer", 0, 10),
            Segment("inner", 3, 7),
        ]
        result = resolve_overlaps(segments, "earliest")
        # Should keep only the first (earliest) segment
        self.assertEqual(to_simple(result), [("outer", 0, 10)])


class TestComplexScenarios(unittest.TestCase):
    """Test complex real-world scenarios."""

    def test_mixed_overlap_patterns(self) -> None:
        """Test complex patterns with mixed overlaps."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 3, 8),
            Segment("c", 7, 12),
            Segment("d", 10, 15),
            Segment("e", 20, 25),
        ]
        result = resolve_overlaps(segments, "longest")
        # First group (a,b,c,d) overlaps, keep longest (a has length 5)
        # Second group (e) is separate
        self.assertEqual(to_simple(result), [("a", 0, 5), ("e", 20, 25)])

    def test_mixed_overlap_patterns_earliest(self) -> None:
        """Test complex patterns with earliest strategy."""
        segments = [
            Segment("a", 0, 5),
            Segment("b", 3, 8),
            Segment("c", 7, 12),
            Segment("d", 10, 15),
            Segment("e", 20, 25),
        ]
        result = resolve_overlaps(segments, "earliest")
        # Should keep earliest non-overlapping segments
        self.assertEqual(to_simple(result), [("a", 0, 5), ("e", 20, 25)])

    def test_unsorted_complex_input(self) -> None:
        """Test that complex unsorted input is handled correctly."""
        segments = [
            Segment("e", 20, 25),
            Segment("a", 0, 5),
            Segment("c", 7, 12),
            Segment("b", 3, 8),
            Segment("d", 10, 15),
        ]
        result = resolve_overlaps(segments, "longest")
        # Should sort by start position and then apply longest strategy
        # First group (a,b,c,d) overlaps, keep longest (a has length 5)
        # Second group (e) is separate
        self.assertEqual(to_simple(result), [("a", 0, 5), ("e", 20, 25)])


if __name__ == "__main__":
    unittest.main()
