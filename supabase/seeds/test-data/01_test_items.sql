-- Test seed: fixture items for Layer2 system/quality tests
-- Issue: #674 | Epic C C2
-- Prerequisite: master seed (semantic_config_version a1111111-1111-4111-8111-111111111102)
-- NOT applied by supabase db reset — use scripts/db/seed-test-data.sh

BEGIN;

INSERT INTO item (
  item_id,
  source,
  external_item_code,
  item_name,
  item_caption,
  catchcopy,
  price,
  item_url,
  shop_code,
  normalized_hash,
  active_status,
  is_active,
  first_fetched_at,
  last_checked_at
)
VALUES
  (
    'b1111111-1111-4111-8111-111111111001',
    'rakuten',
    'test-fixture-001',
    '上品な焼き菓子ギフトセット',
    '職場の上司へのお礼に適した焼き菓子ギフト。格式と安心感を重視。',
    '感謝の気持ちを込めて',
    4320,
    'https://example.com/test/item/001',
    'test-shop-001',
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'active',
    true,
    timestamptz '2026-06-17 12:00:00+00',
    timestamptz '2026-06-17 12:00:00+00'
  ),
  (
    'b1111111-1111-4111-8111-111111111002',
    'rakuten',
    'test-fixture-002',
    'カジュアル雑貨セット',
    '友人向けのカジュアルな雑貨。格式は低め。',
    '気軽な贈り物',
    2800,
    'https://example.com/test/item/002',
    'test-shop-002',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    'active',
    true,
    timestamptz '2026-06-17 12:00:00+00',
    timestamptz '2026-06-17 12:00:00+00'
  ),
  (
    'b1111111-1111-4111-8111-111111111003',
    'rakuten',
    'test-fixture-003',
    'プレミアムワインギフト',
    'ワインとグラスのギフトセット。アルコールを含む（NG 回避テスト用）。',
    '特別な夜に',
    4500,
    'https://example.com/test/item/003',
    'test-shop-003',
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
    'active',
    true,
    timestamptz '2026-06-17 12:00:00+00',
    timestamptz '2026-06-17 12:00:00+00'
  )
ON CONFLICT (source, external_item_code) DO UPDATE SET
  item_name = EXCLUDED.item_name,
  item_caption = EXCLUDED.item_caption,
  catchcopy = EXCLUDED.catchcopy,
  price = EXCLUDED.price,
  item_url = EXCLUDED.item_url,
  shop_code = EXCLUDED.shop_code,
  normalized_hash = EXCLUDED.normalized_hash,
  active_status = EXCLUDED.active_status,
  is_active = EXCLUDED.is_active,
  last_checked_at = EXCLUDED.last_checked_at;

INSERT INTO item_image (
  item_id,
  image_url,
  image_size_type,
  display_order,
  is_primary,
  fetched_at
)
VALUES
  (
    'b1111111-1111-4111-8111-111111111001',
    'https://example.com/test/item/001-medium.jpg',
    'medium',
    0,
    true,
    timestamptz '2026-06-17 12:00:00+00'
  ),
  (
    'b1111111-1111-4111-8111-111111111002',
    'https://example.com/test/item/002-medium.jpg',
    'medium',
    0,
    true,
    timestamptz '2026-06-17 12:00:00+00'
  ),
  (
    'b1111111-1111-4111-8111-111111111003',
    'https://example.com/test/item/003-medium.jpg',
    'medium',
    0,
    true,
    timestamptz '2026-06-17 12:00:00+00'
  )
ON CONFLICT (item_id, image_url) DO UPDATE SET
  image_size_type = EXCLUDED.image_size_type,
  display_order = EXCLUDED.display_order,
  is_primary = EXCLUDED.is_primary,
  fetched_at = EXCLUDED.fetched_at;

INSERT INTO item_review_summary (
  item_id,
  review_average,
  review_count,
  fetched_at
)
VALUES
  ('b1111111-1111-4111-8111-111111111001', 4.5, 128, timestamptz '2026-06-17 12:00:00+00'),
  ('b1111111-1111-4111-8111-111111111002', 3.8, 42, timestamptz '2026-06-17 12:00:00+00'),
  ('b1111111-1111-4111-8111-111111111003', 4.2, 89, timestamptz '2026-06-17 12:00:00+00')
ON CONFLICT (item_id) DO UPDATE SET
  review_average = EXCLUDED.review_average,
  review_count = EXCLUDED.review_count,
  fetched_at = EXCLUDED.fetched_at;

COMMIT;
