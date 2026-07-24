# Supabase Storage S3 互換疎通検証結果（#1617）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 検証ID | Object Storage live（Epic #1614 / Task #1617） |
| 計画 | [Supabase_Storage_S3互換疎通検証計画](./Supabase_Storage_S3互換疎通検証計画.md) |
| 実施日 | 2026-07-25 |
| client | `S3CompatibleObjectStorageClient`（#1612 相当を本 Task Branch に同期） |
| 接続方針 | A（製品=Supabase Storage / S3 互換） |
| 判定 | **Block**（HTTP live 未達。原因と次アクションは §4） |

---

## 2. 実施サマリ

| 確認項目 | 結果 | 根拠 |
| -------- | ---- | ---- |
| 明示フラグなしで HTTP 拒否 | **pass** | `--live-object-storage` 未指定 → exit 3、HTTP なし |
| 資格情報不足で HTTP 拒否 | **pass** | `OBJECT_STORAGE_ENDPOINT` 欠落 → exit 2、HTTP なし |
| UT（httpx mock） | **pass** | `test_object_storage_http_client.py` 15 passed |
| live put/get | **未実施** | endpoint 未設定 + local Supabase（Docker）未起動 |
| secret 非露出 | **pass** | 本結果・ハーネス出力はマスク方針。実値を記載しない |

---

## 3. 実行ログ（実値なし）

### 3.1 フラグなし

```text
Refusing network calls: pass --live-object-storage explicitly
(or set BATCH_OBJECT_STORAGE_LIVE=1). No HTTP request was made.
exit=3
```

### 3.2 live 指定・ENDPOINT 欠落（実施環境の .env）

```text
OBJECT_STORAGE_ENDPOINT are required for --live-object-storage.
Use --scaffold-demo for local/CI. No HTTP request was made.
exit=2
```

| env | 実施時の状態（値は書かない） |
| --- | ---------------------------- |
| `OBJECT_STORAGE_BUCKET` | 設定あり |
| `OBJECT_STORAGE_ACCESS_KEY` | 設定あり |
| `OBJECT_STORAGE_SECRET_KEY` | 設定あり |
| `OBJECT_STORAGE_ENDPOINT` | **未設定** |

### 3.3 local Supabase

| 項目 | 状態 |
| ---- | ---- |
| Docker daemon | 接続不可（`Cannot connect to the Docker daemon`） |
| `supabase start` / migrate | 未実施（Docker 前提） |

---

## 4. 判定と次アクション

| ラベル | 本結果 |
| ------ | ------ |
| 判定 | **Block** |
| 理由（事実） | (1) `OBJECT_STORAGE_ENDPOINT` が未設定のため live ゲートで停止 (2) local Storage 起動に必要な Docker が利用不可 |
| 案 B へのエスカレーション | **不要（推奨）**。失敗は資格情報・実行環境不足であり、S3 互換 client 自体の欠陥は未確認 |

### 4.1 Human 向け次アクション

1. **Hosted dev** または **local（Docker 起動後）** のいずれかで S3 互換 endpoint を確定し、`.env` に `OBJECT_STORAGE_ENDPOINT` を設定する（形式例: 環境設計書 §19.7。実値は commit しない）
2. `raw-products` が対象プロジェクトに存在することを確認（migration #1616）
3. Access / Secret Key が S3 互換用であることを確認（`SUPABASE_SERVICE_ROLE_KEY` ではない）
4. 計画書 §4.1 のコマンドを再実行し、`verdict=Go`（put/get + body 一致）を確認する
5. 成功時は本結果 docs の判定を Go/Adjust に更新する（別 PR または本 PR 追記。secret なし）

### 4.2 AI / リポジトリ側で完了したこと

- ハーネス `scripts/batch/object_storage_live_verify.py`
- #1612 相当 client / UT / `httpx` 依存の本 Branch 同期
- 計画・本結果・ローカル手順 §7.4 追記
- CI を live 必須にしていない

---

## 5. Human Review 確認事項（Issue 転記）

| 項目 | メモ |
| ---- | ---- |
| 疎通環境 | local `supabase start` / Hosted **dev** のどちらで再実施するか |
| 案 B | 本結果だけでは案 B 再検討は不要。再 live で SigV4/path-style が成立しない場合に再検討 |

---

## 6. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-25 | 初版。Block（ENDPOINT 未設定・Docker 未起動）。ハーネス/UT は pass（#1617） |
