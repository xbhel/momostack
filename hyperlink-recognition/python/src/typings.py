from typing import Any, Protocol, TypeVar

T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")
_T_contra = TypeVar("_T_contra", contravariant=True)


class SupportsDunderLT(Protocol[_T_contra]):
    def __lt__(self, other: _T_contra, /) -> bool: ...


class SupportsDunderGT(Protocol[_T_contra]):
    def __gt__(self, other: _T_contra, /) -> bool: ...


class SupportsDunderLE(Protocol[_T_contra]):
    def __le__(self, other: _T_contra, /) -> bool: ...


class SupportsDunderGE(Protocol[_T_contra]):
    def __ge__(self, other: _T_contra, /) -> bool: ...


type SupportsRichComparison = SupportsDunderLT[Any] | SupportsDunderGT[Any]
SupportsRichComparisonT = TypeVar(
    "SupportsRichComparisonT", bound=SupportsRichComparison
)
