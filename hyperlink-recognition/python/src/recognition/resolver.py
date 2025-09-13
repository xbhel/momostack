from collections.abc import Iterable

from recognition.datamodel import Segment


def resolve_overlaps_keep_longest(iterable: Iterable[Segment]) -> list[Segment]:
    """
    Given an iterable of Segment, return a list where overlapping segments are resolved
    by keeping the longest segment in each overlapping group.
    Segments are returned in order.
    """
    segments = sorted(iterable, key=lambda x: x.start)

    if not segments:
        return []

    result = []
    longest = segments[0]

    for _, segment in enumerate(segments, 1):
        if segment.start < longest.end:
            longest = max(segment, longest, key=lambda x: x.end - x.start)
        else:
            result.append(longest)
            longest = segment

    # Don't forget the last group
    result.append(longest)
    return result


def resolve_overlaps_keep_earliest(iterable: Iterable[Segment]) -> list[Segment]:
    """
    Given an iterable of Segment, return a list where overlapping segments are resolved
    by keeping the earliest (first) segment in each overlapping group.
    Segments are returned in order.
    """
    segments = sorted(iterable, key=lambda x: (x.start, x.end))
    if not segments:
        return []

    result = []
    prev_end = -1
    for segment in segments:
        if segment.start >= prev_end:
            result.append(segment)
            prev_end = segment.end
    return result
