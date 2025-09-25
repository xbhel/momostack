from collections.abc import Iterable
from typing import Literal

from datamodels import Segment


def resolve_overlaps[T: Segment](
    iterable: Iterable[T],
    strategy: Literal["longest", "earliest", "earliest_longest"],
    direct_only: bool = False,
) -> list[T]:
    """
    Resolve overlapping segments according to the specified strategy.

    This function processes a sequence of Segment objects and removes overlaps
    according to the chosen strategy. Optionally, you can restrict overlap
    handling to *direct* overlaps only.

    Args:
        iterable: An iterable of Segment objects.
        strategy: The overlap resolution strategy. One of:
            - "longest": For each group of overlapping segments, keep the longest.
            - "earliest": Keep the earliest non-overlapping segments.
            - "earliest_longest": Prefer earliest, break ties by longest.
        direct_only: If True, only directly overlapping segments are considered
                        conflicts; indirectly overlapping segments (via a chain of
                        overlaps) are treated as separate. Default is False.

    Returns:
        A list of resolved, non-overlapping Segment objects.

    Examples::

        # Suppose we have three segments: (0, 5), (4, 7), (6, 10)
        segments = [Segment(0, 5), Segment(4, 7), Segment(6, 10)]

        # Longest strategy, chained overlaps (direct_only=False)
        resolve_overlaps(segments, "longest", direct_only=False)

        # Output: [(0, 5)]  -> the overlapping chain (0-5,4-7,6-10) is merged,
        #           keeping the longest segment

        # Longest strategy, direct overlaps only (direct_only=True)
        resolve_overlaps(segments, "longest", direct_only=True)
        # Output: [(0, 5), (6, 10)] -> only direct overlaps are considered,
        #           so (0,5) and (4,7) are compared separately from (6,10)
    """
    match strategy:
        case "longest":
            segments = sorted(iterable, key=lambda x: x.start)
            func = _resolve_overlaps_keep_longest
        case "earliest":
            segments = sorted(iterable, key=lambda x: x.start)
            func = _resolve_overlaps_keep_earliest
        case "earliest_longest":
            segments = sorted(iterable, key=lambda x: (x.start, -x.end))
            func = _resolve_overlaps_keep_earliest

    if not segments:
        return []
    return func(segments, direct_only)


def _resolve_overlaps_keep_longest[T: Segment](
    segments: list[T], direct_only: bool = False
) -> list[T]:
    result = []
    longest = segments[0]
    group_end = longest.end

    for index in range(1, len(segments)):
        seg = segments[index]
        # Check if segments overlap: seg.start < group_end
        if seg.start < group_end:
            # Segments overlap, keep the longer one
            if (seg.end - seg.start) > (longest.end - longest.start):
                longest = seg
            group_end = longest.end if direct_only else max(group_end, seg.end)
        else:
            # No overlap, add the current longest to result and start new group
            result.append(longest)
            longest = seg
            group_end = longest.end

    # The last group
    result.append(longest)
    return result


def _resolve_overlaps_keep_earliest[T: Segment](
    segments: list[T], direct_only: bool = False
) -> list[T]:
    result = []
    prev_end = -1

    for segment in segments:
        if segment.start >= prev_end:
            result.append(segment)
            prev_end = segment.end
        if not direct_only:
            prev_end = max(prev_end, segment.end)
    return result
