# Supabase Storage S3 互換疎通検証結果（#1617）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 検証ID | Object Storage live（Epic #1614 / Task #1617） |
| 計画 | [Supabase_Storage_S3互換疎通検証計画](./Supabase_Storage_S3互換疎通検証計画.md) |
| 実施日 | 2026-07-25（初回 Block） / **再検証 2026-07-25（Go）** |
| client | `S3CompatibleObjectStorageClient`（#1612 相当を本 Task Branch に同期） |
| 接続方針 | A（製品=Supabase Storage / S3 互換） |
| 実行環境 | **local**（`supabase start` + Docker Desktop） |
| 判定 | **Go**（put/get + body 一致 + missing-key get） |

---

## 2. 実施サマリ

| 確認項目 | 結果 | 根拠 |
| -------- | ---- | ---- |
| 明示フラグなしで HTTP 拒否 | **pass** | `--live-object-storage` 未指定 → exit 3、HTTP なし（初回） |
| 資格情報不足で HTTP 拒否 | **pass** | `OBJECT_STORAGE_ENDPOINT` 欠落 → exit 2、HTTP なし（初回） |
| UT（httpx mock） | **pass** | `test_object_storage_http_client.py` 15 passed |
| live put/get | **pass** | `verdict=Go` success=3/3（再検証） |
| body 一致 | **pass** | `get_object.details.body_match=true` |
| missing-key get | **pass** | `returned_none=true` |
| secret 非露出 | **pass** | 本結果・ハーネス出力はマスク方針。実値を記載しない |

---

## 3. 実行ログ（実値なし）

### 3.1 フラグなし（初回）

```text
Refusing network calls: pass --live-object-storage explicitly
(or set BATCH_OBJECT_STORAGE_LIVE=1). No HTTP request was made.
exit=3
```

### 3.2 live 指定・ENDPOINT 欠落（初回）

```text
OBJECT_STORAGE_ENDPOINT are required for --live-object-storage.
Use --scaffold-demo for local/CI. No HTTP request was made.
exit=2
```

### 3.3 再検証（local Supabase・Docker 起動後）

前提（事実）:

| 項目 | 状態 |
| ---- | ---- |
| Docker daemon | 利用可 |
| `supabase` local | running（Storage S3 URL 表示あり） |
| migration | `20260725120000_raw_products_storage_bucket.sql` 適用済み |
| `OBJECT_STORAGE_BUCKET` | `raw-products` |
| `OBJECT_STORAGE_ENDPOINT` | host のみ: `http://127.0.0.1:54321/…`（path は S3 互換） |
| Access / Secret | 設定あり（値は記載しない） |
| region（実行時） | `local`（`--region local`。`supabase status` の Region 表示に合わせた） |

コマンド（計画書 §4.1 + region）:

```bash
set -a && source .env && set +a
cd apps/batch
uv run python ../../scripts/batch/object_storage_live_verify.py \
  --live-object-storage --probe-missing \
  --region local \
  --output-dir ../../scripts/batch/output-object-storage-live
```

ハーネス要約（Git 管理外 `summary.md` 相当・実値なし）:

```text
verdict=Go success=3 failure=0 endpoint=http://127.0.0.1:54321/… bucket=raw-products
```

| name | ok | おおよそ ms | 備考 |
| ---- | -- | ----------- | ---- |
| put_object | true | ~493 | key prefix `live-verify/1617/` |
| get_object | true | ~17 | body_match=true |
| get_object.missing_key | true | ~23 | returned_none=true |

補足（事実）: 同一環境で region 未指定（ハーネス既定 `us-east-1`）でも put/get は `verdict=Go` だった。local では `--region local` を推奨メモとする（status 表示との一致）。

---

## 4. 判定と次アクション

| ラベル | 本結果 |
| ------ | ------ |
| 判定 | **Go** |
| 理由（事実） | local Supabase Storage（S3 互換）へ明示 live で put/get が成立し、body 一致・missing-key も期待どおり |
| 案 B へのエスカレーション | **不要**。接続方針 A（path-style + SigV4）で疎通確認済み |

### 4.1 Human 向け残メモ

1. Hosted **dev** での再確認は任意（local で Go 済み。環境差が気になる場合のみ）
2. probe オブジェクトは bucket に残る（delete は out of scope）。必要なら手動削除
3. CI 既定 live は引き続き禁止

### 4.2 AI / リポジトリ側で完了したこと

- ハーネス `scripts/batch/object_storage_live_verify.py`
- #1612 相当 client / UT / `httpx` 依存の本 Branch 同期
- 計画・本結果・ローカル手順 §7.4 追記
- CI を live 必須にしていない
- 再検証で `verdict=Go` を確認し、本結果を更新

---

## 5. Human Review 確認事項（Issue 転記）

| 項目 | メモ |
| ---- | ---- |
| 疎通環境 | **local** `supabase start` で Go。Hosted dev 追加確認は任意 |
| 案 B | 不要（方針 A で put/get 成立） |

---

## 6. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-25 | 初版。Block（ENDPOINT 未設定・Docker 未起動）。ハーネス/UT は pass（#1617） |
| 2026-07-25 | 再検証。local Supabase で put/get/missing Go。判定を Go に更新 |
