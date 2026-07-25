# Supabase Storage S3 互換疎通検証計画（#1617・最小）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 検証ID | Object Storage live（Epic #1614 / Task #1617） |
| 文書種別 | PoC 検証計画（最小） |
| 接続方針 | **A**（製品=Supabase Storage / S3 互換 + `OBJECT_STORAGE_*`） |
| client | `S3CompatibleObjectStorageClient`（#1612。本 Task Branch に同期可） |
| 関連 Epic / Task | [#1614](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1614) / [#1617](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1617) |
| 前提 | [#1615](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1615) docs / [#1616](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1616) `raw-products` |
| 結果 | [Supabase_Storage_S3互換疎通検証結果](./Supabase_Storage_S3互換疎通検証結果.md) |

---

## 2. 目的と切り分け

| 項目 | 内容 |
| ---- | ---- |
| 目的 | path-style + SigV4 での **最小 live put/get** と失敗形式・マスク挙動の確認 |
| client | `apps/batch` の `S3CompatibleObjectStorageClient`（明示 `--live-object-storage` のみ） |
| bucket | `raw-products`（正本。`OBJECT_STORAGE_BUCKET`） |
| out of scope | CI 必須ゲート、production 無承認 live、delete/list/multipart、大量 put、案 B/C、BATCH-005 DB SELECT |

---

## 3. 制約

| 制約 | 方針 |
| ---- | ---- |
| live 切替 | `--live-object-storage` または `BATCH_OBJECT_STORAGE_LIVE=1/true/yes/on`。**既定 off** |
| CI live | **禁止**（通常 PR CI の必須ゲートにしない） |
| secret | `OBJECT_STORAGE_ACCESS_KEY` / `OBJECT_STORAGE_SECRET_KEY` は env のみ。成果物はマスク |
| 件数 | put 1 + get 1（任意で missing-key get 1）。probe オブジェクトの delete はしない |
| 実行環境 | local（`supabase start` + migration）または Hosted **dev**（Human 承認のキー） |

---

## 4. 計測設計

| 項目 | 方針 |
| ---- | ---- |
| ハーネス | `scripts/batch/object_storage_live_verify.py` |
| モード | 明示 live 必須。未指定時は HTTP 非実行（exit 3） |
| 事前ゲート | `OBJECT_STORAGE_ENDPOINT` / Access / Secret 欠落時は HTTP せず中止（exit 2） |
| 指標 | wall-clock（ms）、成功可否、body 一致、エラー code（`GRS-RAW-*`）、endpoint host のみマスク表示 |
| 出力 | Git 管理外: `report.json` / `summary.md`（`scripts/batch/output-object-storage-live/`） |

### 4.1 実行コマンド（local）

```bash
set -a && source .env && set +a
# 必須: OBJECT_STORAGE_ENDPOINT / ACCESS_KEY / SECRET_KEY / BUCKET=raw-products
# 任意: OBJECT_STORAGE_REGION（未設定時 us-east-1）, BATCH_OBJECT_STORAGE_LIVE
# local Supabase: --region local を推奨（supabase status の Storage Region と一致）

cd apps/batch
uv run python ../../scripts/batch/object_storage_live_verify.py \
  --live-object-storage --probe-missing \
  --region local \
  --output-dir ../../scripts/batch/output-object-storage-live
```

**local Supabase 前提（Docker 要）**

1. `./scripts/db/start-local.sh`
2. `./scripts/db/migrate-up.sh`（`raw-products` 作成）
3. ローカル向け S3 互換 endpoint / キーを `.env` に設定（実値 commit 禁止。`supabase status` の Storage (S3) を参照）
4. 上記ハーネス実行

手順正本: [ローカル開発手順書 §7.4](../../06_実装設計/cross_cutting/ローカル開発手順書.md)

---

## 5. 判定枠

| ラベル | 意味 |
| ------ | ---- |
| Go | put/get 成功かつ body 一致。失敗形式を説明可能。致命制約なし |
| Adjust | 疎通は可能だが region / endpoint 形式 / content-type 等で設計調整が必要 |
| Block | 認証失敗・endpoint 未達・Docker 未起動・資格情報不足など、成立を妨げる制約がある |

Block の場合も、**失敗原因と次アクション**を結果 docs に残せば本 Task の完了条件を満たす。

---

## 6. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-25 | 初版（#1617） |
| 2026-07-25 | local 向け `--region local` をコマンド例に追記（再検証 Go） |
