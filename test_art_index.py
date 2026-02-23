import random
import unittest

from art_index import AdaptiveRadixTree


class TestAdaptiveRadixTree(unittest.TestCase):
    def test_insert_and_contains(self):
        art = AdaptiveRadixTree()
        values = [0, 1, 2, 255, 256, 10_000, 2**32]
        for v in values:
            art.insert(v)

        for v in values:
            self.assertTrue(art.contains(v))

        self.assertFalse(art.contains(999_999_999))

    def test_bulk_insert(self):
        art = AdaptiveRadixTree()
        values = list(range(1000))
        art.bulk_insert(values)
        self.assertTrue(all(art.contains(v) for v in values))

    def test_range_query(self):
        art = AdaptiveRadixTree()
        values = [5, 10, 20, 30, 40, 100]
        art.bulk_insert(values)

        self.assertEqual(art.range_query(0, 4), [])
        self.assertEqual(art.range_query(0, 10), [5, 10])
        self.assertEqual(art.range_query(15, 40), [20, 30, 40])
        self.assertEqual(art.range_query(200, 100), [])

    def test_randomized_membership(self):
        random.seed(7)
        art = AdaptiveRadixTree()
        inserted = set(random.sample(range(1_000_000), 5000))
        art.bulk_insert(inserted)

        for v in list(inserted)[:1000]:
            self.assertTrue(art.contains(v))

        misses = set(random.sample(range(1_000_000, 2_000_000), 500))
        for v in misses:
            self.assertFalse(art.contains(v))


if __name__ == "__main__":
    unittest.main()
