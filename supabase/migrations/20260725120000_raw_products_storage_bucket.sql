-- Raw JSON Object Storage bucket（接続方針 A / Epic #1614 / Task #1616）
--
-- 製品: Supabase Storage
-- bucket 名正本: raw-products（OBJECT_STORAGE_BUCKET と一致）
-- 公開: private（public = false）。web / anon からの直アクセスを想定しない
-- アクセス: batch は S3 互換 API（OBJECT_STORAGE_*）。service_role 直結は主経路にしない
--
-- 適用前提: Supabase が提供する storage スキーマが存在する環境
-- （ローカル: supabase start、Hosted: Storage 有効プロジェクト）

INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES (
  'raw-products',
  'raw-products',
  false,
  52428800  -- 50MiB。supabase/config.toml [storage].file_size_limit と整合
)
ON CONFLICT (id) DO UPDATE
SET
  name = EXCLUDED.name,
  public = EXCLUDED.public,
  file_size_limit = EXCLUDED.file_size_limit;

-- MVP: storage.objects 向けの anon/authenticated Policy は追加しない。
-- Raw 操作は S3 互換キー経由（接続方針 A）。Storage RLS 詳細は将来 Task で検討可。
