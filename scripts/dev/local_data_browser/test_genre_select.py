#!/usr/bin/env python3
"""genre_select.py の DB 不要単体テスト。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from genre_select import (
    VIRTUAL_ROOT_ID,
    build_children_map,
    child_parent_clause,
    descendant_counts,
    expand_descendants,
    load_selection,
    merge_visible_selection,
    parse_genre_id,
    parse_genre_ids,
    pick_closest_parents,
    save_selection,
)


class ParseTests(unittest.TestCase):
    def test_parse_genre_id(self) -> None:
        self.assertEqual(parse_genre_id("100227"), 100227)
        self.assertIsNone(parse_genre_id("x"))
        self.assertIsNone(parse_genre_id(-1))

    def test_parse_genre_ids_skips_root_and_dup(self) -> None:
        self.assertEqual(parse_genre_ids([0, "100227", 100227, "x"]), [100227])


class MergeTests(unittest.TestCase):
    def test_keeps_other_levels(self) -> None:
        merged = merge_visible_selection(
            [100227, 101381],
            visible=[100228, 100236],
            checked=[100228],
        )
        self.assertEqual(merged, [100227, 100228, 101381])

    def test_uncheck_visible(self) -> None:
        merged = merge_visible_selection(
            [100227, 100228],
            visible=[100227, 100228],
            checked=[],
        )
        self.assertEqual(merged, [])


class TreeHelperTests(unittest.TestCase):
    def test_virtual_root_clause(self) -> None:
        sql, params = child_parent_clause(None)
        self.assertIn("parent_external_genre_id IS NULL", sql)
        self.assertEqual(params, (VIRTUAL_ROOT_ID,))

    def test_parent_clause(self) -> None:
        sql, params = child_parent_clause(100227)
        self.assertIn("parent_external_genre_id = %s", sql)
        self.assertEqual(params, (100227,))

    def test_expand_descendants(self) -> None:
        children = {100227: [100228, 100236], 100228: [100232]}
        expanded = expand_descendants([100227], children)
        self.assertEqual(expanded, {100227, 100228, 100236, 100232})

    def test_pick_closest_parents_prefers_deeper(self) -> None:
        parent_of = pick_closest_parents(
            [
                (100276, 100227, 1),
                (100276, 100275, 3),
                (100262, 100227, 1),
                (100227, 0, 0),
            ]
        )
        self.assertEqual(parent_of[100276], 100275)
        self.assertEqual(parent_of[100262], 100227)
        self.assertEqual(parent_of[100227], 0)

    def test_build_children_and_descendant_counts(self) -> None:
        parent_of = {100227: 0, 100262: 100227, 110502: 100262}
        children = build_children_map(parent_of)
        self.assertEqual(children[0], [100227])
        self.assertEqual(children[100227], [100262])
        self.assertEqual(children[100262], [110502])
        counts = descendant_counts(children)
        self.assertEqual(counts[100227], 2)
        self.assertEqual(counts[100262], 1)
        self.assertEqual(counts[110502], 0)


class CacheTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "okuri_target_genres.json"
            saved = save_selection([100227, 0, "101381"], filter_mode="exact", path=path)
            self.assertNotIn(0, saved["genre_ids"])
            loaded = load_selection(path)
            self.assertEqual(loaded["genre_ids"], [100227, 101381])
            self.assertEqual(loaded["filter_mode"], "exact")
            self.assertTrue(loaded["updated_at"])


if __name__ == "__main__":
    unittest.main()
