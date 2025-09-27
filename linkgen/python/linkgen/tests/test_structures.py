import unittest
from typing import Any

from linkgen.structures import LookupDict


class TestLookupDict(unittest.TestCase):
    def setUp(self) -> None:
        self.ld = LookupDict({3.0: 'c', 1: 'a', 4: 'd', 2: 'b'})

    def test_initialization_sorts_keys(self):
        self.assertEqual(list(self.ld.keys()), [1, 2, 3, 4])
        self.assertEqual(list(self.ld.values()), ['a', 'b', 'c', 'd'])

    def test_getitem(self):
        self.assertEqual(self.ld[1], 'a')
        self.assertEqual(self.ld[4], 'd')
        with self.assertRaises(KeyError):
            _ = self.ld[999]

    def test_iter(self):
        self.assertEqual(list(iter(self.ld)), [1, 2, 3, 4])

    def test_len(self):
        self.assertEqual(len(self.ld), 4)

    def test_contains(self):
        self.assertIn(2, self.ld)
        self.assertNotIn(999, self.ld)

    def test_immutable_setitem(self):
        with self.assertRaises(TypeError) as cm:
            self.ld[5] = 'e'
        self.assertIn("does not support item assignment", str(cm.exception))

    def test_immutable_delitem(self):
        with self.assertRaises(TypeError) as cm:
            del self.ld[1]
        self.assertIn("does not support item deletion", str(cm.exception))

    def test_floor(self):
        self.assertEqual(self.ld.floor(2.5), 'b')  # key=2 < 2.5
        self.assertEqual(self.ld.floor(2), 'b')  # exact match
        self.assertIsNone(self.ld.floor(0.5))  # below all
        self.assertEqual(self.ld.floor(5), 'd')  # above all → last
        self.assertEqual(self.ld.floor(1), 'a')

    def test_ceiling(self):
        self.assertEqual(self.ld.ceiling(2.5), 'c')  # key=3 > 2.5
        self.assertEqual(self.ld.ceiling(3), 'c')  # exact match
        self.assertIsNone(self.ld.ceiling(5))  # above all
        self.assertEqual(self.ld.ceiling(0.5), 'a')  # below all → first
        self.assertEqual(self.ld.ceiling(4), 'd')

    def test_lower(self):
        self.assertEqual(self.ld.lower(2.5), 'b')  # key=2 < 2.5
        self.assertEqual(self.ld.lower(2), 'a')  # strictly less
        self.assertIsNone(self.ld.lower(1))  # nothing less
        self.assertEqual(self.ld.lower(5), 'd')
        self.assertIsNone(self.ld.lower(0.5))

    def test_higher(self):
        self.assertEqual(self.ld.higher(2.5), 'c')  # key=3 > 2.5
        self.assertEqual(self.ld.higher(2), 'c')  # strictly greater
        self.assertIsNone(self.ld.higher(4))  # nothing greater
        self.assertEqual(self.ld.higher(0.5), 'a')
        self.assertIsNone(self.ld.higher(5))

    def test_keys_view(self):
        keys = self.ld.keys()
        self.assertIsInstance(keys, type({}.keys()))
        self.assertEqual(list(keys), [1, 2, 3, 4])

    def test_values_view(self):
        values = self.ld.values()
        self.assertIsInstance(values, type({}.values()))
        self.assertEqual(list(values), ['a', 'b', 'c', 'd'])

    def test_items_view(self):
        items = self.ld.items()
        self.assertIsInstance(items, type({}.items()))
        self.assertEqual(list(items), [(1, 'a'), (2, 'b'), (3, 'c'), (4, 'd')])

    def test_repr(self):
        r = repr(self.ld)
        expected = "LookupDict({1: 'a', 2: 'b', 3.0: 'c', 4: 'd'})"
        self.assertEqual(r, expected)

    def test_copy(self):
        copy = self.ld.copy()
        self.assertIsNot(copy, self.ld)
        self.assertEqual(copy, self.ld)
        self.assertEqual(dict(copy), dict(self.ld))

    def test_eq_with_lookup_dict(self):
        other = LookupDict({1: 'a', 2: 'b', 3: 'c', 4: 'd'})
        self.assertEqual(self.ld, other)

    def test_eq_with_dict(self):
        other = {1: 'a', 2: 'b', 3: 'c', 4: 'd'}
        self.assertEqual(self.ld, other)

    def test_eq_with_different_order_dict(self):
        other = {4: 'd', 3: 'c', 2: 'b', 1: 'a'}
        self.assertEqual(self.ld, other)

    def test_eq_with_different_content(self):
        other = {1: 'a', 2: 'b', 3: 'c', 5: 'e'}
        self.assertNotEqual(self.ld, other)

    def test_eq_with_non_mapping(self):
        self.assertEqual(self.ld.__eq__("not a mapping"), NotImplemented)

    def test_empty_lookup_dict(self):
        empty: LookupDict[int, Any] = LookupDict({})
        self.assertEqual(len(empty), 0)
        self.assertEqual(list(empty), [])
        self.assertIsNone(empty.floor(1))
        self.assertIsNone(empty.ceiling(1))
        self.assertIsNone(empty.lower(1))
        self.assertIsNone(empty.higher(1))

    def test_with_strings(self):
        ld = LookupDict({'b': 2, 'a': 1, 'd': 4, 'c': 3})
        self.assertEqual(ld.floor('c'), 3)
        self.assertEqual(ld.ceiling('bb'), 3)
        self.assertIsNone(ld.lower('a'))
        self.assertIsNone(ld.higher('z'))

    def test_with_tuples(self):
        ld = LookupDict({(1, 2): 'A', (0, 1): 'B', (2, 0): 'C'})
        self.assertEqual(ld.floor((1, 1)), 'B')  # (0,1) < (1,1)
        self.assertEqual(ld.ceiling((1, 1)), 'A')  # (1,2) >= (1,1)

    def test_float_precision_edge(self):
        ld = LookupDict({1.0: 'one', 2.0: 'two', 3.0: 'three'})
        self.assertEqual(ld.floor(2.0000000001), 'two')
        self.assertEqual(ld.ceiling(1.9999999999), 'two')
        self.assertEqual(ld.lower(2.0), 'one')
        self.assertEqual(ld.higher(2.0), 'three')


if __name__ == '__main__':
    unittest.main()
