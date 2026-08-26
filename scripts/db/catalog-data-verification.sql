-- catalog-data-verification.sql
-- local カタログ健全性スナップショット用。SELECT のみ。
-- 書き込み / TRUNCATE / DDL / 全件 UPDATE・DELETE は禁止。
-- secret・接続文字列・商品 URL・商品名の大量出力はしない。
-- 実行例（接続 URL は env から注入し、本ファイルへ書かない）:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/db/catalog-data-verification.sql

\pset pager off
\timing off

\echo '=== measured_at (JST) ==='
SELECT now() AT TIME ZONE 'Asia/Tokyo' AS measured_at_jst;

\echo '=== A. pipeline counts ==='
SELECT 'item_total' AS metric, count(*)::bigint AS n FROM item
UNION ALL
SELECT 'item_active', count(*) FROM item WHERE is_active IS TRUE
UNION ALL
SELECT 'item_active_status_active', count(*) FROM item WHERE active_status = 'active'
UNION ALL
SELECT 'staging_item_rows', count(*) FROM staging_item
UNION ALL
SELECT 'staging_item_distinct_codes', count(*) FROM (
  SELECT DISTINCT source, external_item_code FROM staging_item
) s
UNION ALL
SELECT 'raw_product_metadata_rows', count(*) FROM raw_product_metadata;

\echo '=== A. staging codes missing from item ==='
SELECT count(*)::bigint AS staging_codes_missing_from_item
FROM (
  SELECT DISTINCT source, external_item_code FROM staging_item
) s
WHERE NOT EXISTS (
  SELECT 1
  FROM item i
  WHERE i.source = s.source
    AND i.external_item_code = s.external_item_code
);

\echo '=== A. required field gaps ==='
SELECT
  count(*) FILTER (
    WHERE item_name IS NULL OR btrim(item_name) = ''
  )::bigint AS item_name_missing,
  count(*) FILTER (
    WHERE price IS NULL
  )::bigint AS price_missing,
  count(*) FILTER (
    WHERE item_url IS NULL OR btrim(item_url) = ''
  )::bigint AS item_url_missing,
  count(*) FILTER (
    WHERE external_genre_id IS NULL
  )::bigint AS external_genre_id_null
FROM item;

\echo '=== A. images ==='
SELECT
  count(*) FILTER (
    WHERE NOT EXISTS (
      SELECT 1 FROM item_image img WHERE img.item_id = i.item_id
    )
  )::bigint AS item_with_no_image,
  count(*) FILTER (
    WHERE NOT EXISTS (
      SELECT 1
      FROM item_image img
      WHERE img.item_id = i.item_id
        AND img.is_primary IS TRUE
    )
  )::bigint AS item_with_no_primary_image
FROM item i;

\echo '=== A. price distribution ==='
SELECT
  min(price) AS price_min,
  percentile_cont(0.01) WITHIN GROUP (ORDER BY price) AS p01,
  percentile_cont(0.05) WITHIN GROUP (ORDER BY price) AS p05,
  percentile_cont(0.50) WITHIN GROUP (ORDER BY price) AS p50,
  percentile_cont(0.95) WITHIN GROUP (ORDER BY price) AS p95,
  percentile_cont(0.99) WITHIN GROUP (ORDER BY price) AS p99,
  max(price) AS price_max,
  count(*) FILTER (WHERE price = 0)::bigint AS price_eq_0,
  count(*) FILTER (WHERE price > 0 AND price < 100)::bigint AS price_1_to_99,
  count(*) FILTER (WHERE price >= 100 AND price < 1000)::bigint AS price_100_to_999,
  count(*) FILTER (WHERE price >= 1000 AND price < 3000)::bigint AS price_1000_to_2999,
  count(*) FILTER (WHERE price >= 3000 AND price < 10000)::bigint AS price_3000_to_9999,
  count(*) FILTER (WHERE price >= 10000 AND price < 30000)::bigint AS price_10000_to_29999,
  count(*) FILTER (WHERE price >= 30000 AND price < 100000)::bigint AS price_30000_to_99999,
  count(*) FILTER (WHERE price >= 100000)::bigint AS price_100000_plus
FROM item;

\echo '=== B. meaning chain coverage ==='
SELECT 'item_with_semantic' AS metric, count(DISTINCT item_id)::bigint AS n FROM item_semantic
UNION ALL
SELECT 'item_with_feature', count(DISTINCT item_id) FROM item_feature
UNION ALL
SELECT 'item_with_feature_8axis', count(DISTINCT item_id) FROM (
  SELECT item_id
  FROM item_feature
  GROUP BY item_id, semantic_config_version_id
  HAVING count(DISTINCT feature_code) = 8
) f
UNION ALL
SELECT 'item_with_meaning', count(DISTINCT item_id) FROM item_meaning
UNION ALL
SELECT 'item_with_embedding', count(DISTINCT item_id) FROM item_embedding
UNION ALL
SELECT 'item_never_queued', count(*) FROM item i
WHERE NOT EXISTS (
  SELECT 1 FROM item_generation_queue q WHERE q.item_id = i.item_id
);

\echo '=== B. queue status ==='
SELECT generation_type, queue_status, count(*)::bigint AS n
FROM item_generation_queue
GROUP BY generation_type, queue_status
ORDER BY generation_type, queue_status;

\echo '=== B. latest queue per item ==='
SELECT q.generation_type, q.queue_status, count(*)::bigint AS n
FROM (
  SELECT DISTINCT ON (item_id)
    item_id, generation_type, queue_status
  FROM item_generation_queue
  ORDER BY item_id, queued_at DESC NULLS LAST, completed_at DESC NULLS LAST
) q
GROUP BY q.generation_type, q.queue_status
ORDER BY q.generation_type, q.queue_status;

\echo '=== B. failed queue error_message classes (truncated, no secrets) ==='
SELECT
  left(coalesce(error_message, '(null)'), 40) AS error_prefix,
  count(*)::bigint AS n
FROM item_generation_queue
WHERE queue_status = 'failed'
GROUP BY 1
ORDER BY n DESC
LIMIT 15;

\echo '=== B+. genre volume (top 25) ==='
SELECT
  i.external_genre_id,
  g.genre_name,
  count(*)::bigint AS n,
  round(avg(i.price))::bigint AS price_avg,
  min(i.price) AS price_min,
  max(i.price) AS price_max
FROM item i
LEFT JOIN external_genre g
  ON g.external_genre_id = i.external_genre_id
 AND g.source = i.source
GROUP BY i.external_genre_id, g.genre_name
ORDER BY n DESC
LIMIT 25;

\echo '=== B+. suspect genre name patterns ==='
SELECT
  i.external_genre_id,
  g.genre_name,
  count(*)::bigint AS n,
  round(avg(i.price))::bigint AS price_avg
FROM item i
LEFT JOIN external_genre g
  ON g.external_genre_id = i.external_genre_id
 AND g.source = i.source
WHERE g.genre_name ~ '(作業|工具|業務|工業|事務|DIY|カー用品|日用|衣料|シャツ|パンツ|靴下|下着|靴|サンダル)'
GROUP BY i.external_genre_id, g.genre_name
ORDER BY n DESC
LIMIT 20;

\echo '=== B+. sample item_id from suspect genres (no names/URLs) ==='
SELECT s.external_genre_id, s.genre_name, s.item_id, s.price
FROM (
  SELECT
    i.external_genre_id,
    g.genre_name,
    i.item_id,
    i.price,
    row_number() OVER (
      PARTITION BY i.external_genre_id
      ORDER BY i.price DESC, i.item_id
    ) AS rn
  FROM item i
  JOIN external_genre g
    ON g.external_genre_id = i.external_genre_id
   AND g.source = i.source
  WHERE g.genre_name ~ '(作業|工具|業務|工業|事務|DIY|カー用品|日用|衣料|シャツ|パンツ|靴下|下着|靴|サンダル)'
) s
WHERE s.rn <= 3
ORDER BY s.external_genre_id, s.rn
LIMIT 40;

\echo '=== B+. price outlier sample item_id ==='
(
  SELECT 'high'::text AS kind, item_id, price, external_genre_id
  FROM item
  ORDER BY price DESC, item_id
  LIMIT 8
)
UNION ALL
(
  SELECT 'low'::text, item_id, price, external_genre_id
  FROM item
  WHERE price > 0
  ORDER BY price ASC, item_id
  LIMIT 8
);

\echo '=== A. fixtures and reverse leak ==='
SELECT item_id, external_item_code, active_status
FROM item
WHERE external_item_code LIKE 'test-fixture-%'
   OR external_genre_id IS NULL
ORDER BY external_item_code;

SELECT 'item_not_in_staging' AS metric, count(*)::bigint AS n
FROM item i
WHERE NOT EXISTS (
  SELECT 1 FROM staging_item s
  WHERE s.source = i.source AND s.external_item_code = i.external_item_code
);

SELECT item_id, external_item_code, active_status, is_active
FROM item
WHERE is_active IS NOT TRUE OR active_status <> 'active'
ORDER BY item_id;

\echo '=== B+. その他 parent genre ==='
SELECT
  i.external_genre_id,
  g.genre_name,
  g.parent_external_genre_id,
  pg.genre_name AS parent_genre_name,
  count(*)::bigint AS n
FROM item i
JOIN external_genre g
  ON g.external_genre_id = i.external_genre_id AND g.source = i.source
LEFT JOIN external_genre pg
  ON pg.external_genre_id = g.parent_external_genre_id AND pg.source = g.source
WHERE i.external_genre_id IN (101954, 101856, 100292, 559275, 553282, 110552, 101384)
GROUP BY 1, 2, 3, 4
ORDER BY n DESC;
