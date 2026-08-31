#!/usr/bin/env python3
"""ranking.py の DB / 実楽天API 不要単体テスト。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ranking
from ranking import (
    RankingFetchError,
    RankingItem,
    RankingSlice,
    all_slices,
    aggregate_items,
    credentials_status,
    extract_keywords,
    fetch_and_cache_many,
    get_slice,
    load_slice_cache,
    mask_text,
    parse_ranking_payload,
    resolve_fetch_targets,
    save_slice_cache,
    slices_for_pattern,
)


def _item(**overrides: object) -> RankingItem:
    base = dict(
        rank=1,
        item_code="giftshop:sku-1",
        item_name="【ホワイトデー】チョコレートギフト 詰め合わせ",
        catchcopy="本命向け",
        shop_code="giftshop",
        shop_name="ギフト店",
        genre_id="100283",
        price=3000,
        review_count=12,
        review_average=4.5,
        image_url="https://example.invalid/a.jpg",
        item_url="https://item.rakuten.co.jp/giftshop/sku-1/",
        slice_id="overall",
        page=1,
    )
    base.update(overrides)
    return RankingItem(**base)  # type: ignore[arg-type]


class SliceParamTests(unittest.TestCase):
    def test_eighteen_slices_without_genre(self) -> None:
        slices = all_slices()
        self.assertEqual(len(slices), 1 + 5 + 2 + 10)
        for slice_ in slices:
            self.assertNotIn("genreId", slice_.query_params())
            self.assertNotIn("period", slice_.query_params())

    def test_overall_sends_no_age_or_sex(self) -> None:
        self.assertEqual(get_slice("overall").query_params(), {})

    def test_age_only_does_not_default_sex(self) -> None:
        params = get_slice("age-20").query_params()
        self.assertEqual(params, {"age": "20"})
        self.assertNotIn("sex", params)

    def test_sex_only_does_not_send_age(self) -> None:
        self.assertEqual(get_slice("sex-1").query_params(), {"sex": "1"})

    def test_age_sex_sends_both(self) -> None:
        self.assertEqual(
            get_slice("age-20-sex-1").query_params(),
            {"age": "20", "sex": "1"},
        )

    def test_pattern_groups(self) -> None:
        self.assertEqual(len(slices_for_pattern("overall")), 1)
        self.assertEqual(len(slices_for_pattern("age")), 5)
        self.assertEqual(len(slices_for_pattern("sex")), 2)
        self.assertEqual(len(slices_for_pattern("age_sex")), 10)

    def test_resolve_fetch_targets(self) -> None:
        one = resolve_fetch_targets(pattern="age", slice_id="age-30", fetch_scope="slice")
        self.assertEqual([s.slice_id for s in one], ["age-30"])
        ages = resolve_fetch_targets(pattern="age", slice_id="", fetch_scope="pattern")
        self.assertEqual(len(ages), 5)
        all_ = resolve_fetch_targets(pattern="overall", slice_id="overall", fetch_scope="all")
        self.assertEqual(len(all_), 18)


class ParseTests(unittest.TestCase):
    def test_format_version_2_flat(self) -> None:
        payload = {
            "title": "総合",
            "lastBuildDate": "Mon, 31 Aug 2026 12:00:00 +0900",
            "Items": [
                {
                    "rank": 1,
                    "itemCode": "shop-a:item-1",
                    "itemName": "紅茶ギフト",
                    "catchcopy": "贈答用",
                    "shopCode": "shop-a",
                    "shopName": "茶店",
                    "genreId": 100316,
                    "itemPrice": 1980,
                    "reviewCount": 3,
                    "reviewAverage": 4.2,
                    "mediumImageUrls": [{"imageUrl": "https://example.invalid/m.jpg"}],
                    "itemUrl": "https://item.rakuten.co.jp/shop-a/item-1/",
                }
            ],
        }
        title, last_build, items = parse_ranking_payload(payload, slice_id="overall")
        self.assertEqual(title, "総合")
        self.assertTrue(last_build)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].shop_code, "shop-a")
        self.assertEqual(items[0].genre_id, "100316")
        self.assertEqual(items[0].image_url, "https://example.invalid/m.jpg")

    def test_nested_item_and_shop_from_item_code(self) -> None:
        payload = {
            "lastBuildDate": "x",
            "Items": [
                {
                    "Item": {
                        "rank": 2,
                        "itemCode": "from-code:sku",
                        "itemName": "石鹸",
                    }
                }
            ],
        }
        _, _, items = parse_ranking_payload(payload, slice_id="age-20")
        self.assertEqual(items[0].shop_code, "from-code")
        self.assertEqual(items[0].slice_id, "age-20")

    def test_missing_items_raises(self) -> None:
        with self.assertRaises(RankingFetchError):
            parse_ranking_payload({"title": "x"}, slice_id="overall")


class KeywordAndAggregateTests(unittest.TestCase):
    def test_extract_keywords_keeps_gift_words(self) -> None:
        tokens = extract_keywords("【ホワイトデー】チョコレートギフト 詰め合わせ 送料無料")
        self.assertIn("ホワイトデー", tokens)
        self.assertIn("チョコレートギフト", tokens)
        self.assertIn("詰め合わせ", tokens)
        self.assertNotIn("送料無料", tokens)

    def test_aggregate_sorts_by_slice_coverage(self) -> None:
        items = [
            _item(slice_id="age-20", genre_id="100", shop_code="a", shop_name="A"),
            _item(
                slice_id="age-30",
                genre_id="100",
                shop_code="a",
                shop_name="A",
                item_code="giftshop:sku-2",
            ),
            _item(
                slice_id="age-20",
                genre_id="200",
                shop_code="b",
                shop_name="B",
                item_code="other:sku-3",
                item_name="石鹸",
            ),
        ]
        agg = aggregate_items(items)
        self.assertEqual(agg["genres"][0].key, "100")
        self.assertEqual(len(agg["genres"][0].slice_ids), 2)
        self.assertEqual(agg["shops"][0].key, "a")


class SecurityTests(unittest.TestCase):
    def test_mask_secret_in_error_text(self) -> None:
        secret = "pk_live_secret_value_example"
        masked = mask_text(f"failed applicationId={secret}", secrets=(secret,))
        self.assertNotIn(secret, masked)
        self.assertIn("REDACTED", masked)

    def test_credentials_status_does_not_echo_values(self) -> None:
        status = credentials_status(
            {
                "RAKUTEN_APPLICATION_ID": "real-app-id-should-not-leak",
                "RAKUTEN_ACCESS_KEY": "real-access-key-should-not-leak",
            }
        )
        dumped = str(status)
        self.assertTrue(status["ready"])
        self.assertNotIn("real-app-id", dumped)
        self.assertNotIn("real-access-key", dumped)


class CacheAndFetchTests(unittest.TestCase):
    def test_cache_roundtrip_without_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(ranking, "CACHE_DIR", Path(tmp)):
                cache = ranking.SliceCache(
                    slice_id="overall",
                    pattern="overall",
                    age=None,
                    sex=None,
                    fetched_at="2026-08-31 12:00:00 JST",
                    title="総合",
                    last_build_date="Mon",
                    page_count=1,
                    items=[_item()],
                )
                path = save_slice_cache(cache)
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("applicationId", text)
                self.assertNotIn("accessKey", text)
                loaded = load_slice_cache("overall")
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.items[0].item_code, "giftshop:sku-1")

    def test_fetch_and_cache_uses_injected_client(self) -> None:
        payload = {
            "title": "総合",
            "lastBuildDate": "Mon",
            "Items": [
                {
                    "rank": 1,
                    "itemCode": "s:1",
                    "itemName": "花束ギフト",
                    "shopCode": "s",
                    "genreId": "101",
                }
            ],
        }

        def fake_get(extra: dict[str, str], page: int) -> dict:
            self.assertEqual(extra, {})
            self.assertEqual(page, 1)
            return payload

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(ranking, "CACHE_DIR", Path(tmp)):
                ok, errors = fetch_and_cache_many(
                    [RankingSlice("overall", "overall")],
                    application_id="dummy-app",
                    access_key="dummy-key",
                    pages=1,
                    get_json=fake_get,
                    sleep_fn=lambda _: None,
                )
                self.assertEqual(ok, ["overall"])
                self.assertEqual(errors, [])
                loaded = load_slice_cache("overall")
                self.assertEqual(loaded.items[0].item_name, "花束ギフト")


if __name__ == "__main__":
    unittest.main()
