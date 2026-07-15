# item_active_status_candidate Retention cleanup 運用手順

## 1. ドキュメント情報

| 項目 | 内容 |
| ---- | ---- |
| 対象 | `item_active_status_candidate` |
| 関連 Task | #1235（T7） / 親 Epic #1227 |
| 制約正本 | BATCH-004 §18.1.1 / テーブル定義書 §13 / BATCH-008 §11 |
| 作成日 | 2026-07-15 |

---

## 2. 方針

| 候補 status | Retention | 基準時刻 |
| ----------- | --------- | -------- |
| `detected` | **削除しない** | — |
| `applied` | 14 日後に物理 DELETE | `applied_at` |
| `superseded` / `discarded` | 14 日後に物理 DELETE | `updated_at` |

- BATCH-008 Applier 成功直後の即時削除はしない
- Online / api / reco から実行しない（batch / 運用のみ）
- 日数変更は Human 再判断

---

## 3. 実装入口（scaffold）

```bash
cd apps/batch
uv run --extra dev python -m batch.application.item_active_status \
  --retention-cleanup --scaffold-demo --job-run-id local-retention
```

- 本番 DB adapter は未配線。unit / scaffold は in-memory
- コード: `apps/batch/src/batch/application/item_active_status/retention.py`

---

## 4. 手動 SQL 手順（MVP 代替）

**注意**: 本番適用前に dry-run（SELECT）で件数確認。`detected` を WHERE に含めない。

### 4.1 dry-run（削除候補件数）

```sql
-- applied（14日超）
SELECT count(*) AS applied_due
FROM item_active_status_candidate
WHERE candidate_status = 'applied'
  AND applied_at IS NOT NULL
  AND applied_at <= (now() AT INTERVAL '14 days');

-- superseded / discarded（14日超）
SELECT count(*) AS terminal_due
FROM item_active_status_candidate
WHERE candidate_status IN ('superseded', 'discarded')
  AND updated_at <= (now() AT INTERVAL '14 days');

-- 安全確認: detected は 0 件になるべきクエリ例（意図的に除外）
SELECT count(*) AS detected_must_stay
FROM item_active_status_candidate
WHERE candidate_status = 'detected';
```

### 4.2 DELETE

```sql
BEGIN;

DELETE FROM item_active_status_candidate
WHERE candidate_status = 'applied'
  AND applied_at IS NOT NULL
  AND applied_at <= (now() AT INTERVAL '14 days');

DELETE FROM item_active_status_candidate
WHERE candidate_status IN ('superseded', 'discarded')
  AND updated_at <= (now() AT INTERVAL '14 days');

-- detected 行数が変わっていないことを確認してから COMMIT
COMMIT;
```

---

## 5. テスト観点

| 観点 | 期待 |
| ---- | ---- |
| detected 非削除 | 古い `detected` も残る |
| applied 14日超 | 削除 |
| applied 14日未満 | 保持 |
| superseded/discarded | `updated_at` 基準 |
| dry-run | 削除予定件数のみ計上、実 DELETE なし |

---

## 6. 関連資料

| 資料 | パス |
| ---- | ---- |
| テーブル定義書 §13 | `docs/06_実装設計/database/item_active_status_candidate_テーブル定義書.md` |
| BATCH-008 §11 | `docs/06_実装設計/batch/BATCH-008_商品有効状態更新バッチ仕様書.md` |
| BATCH-004 §18.1.1 | `docs/06_実装設計/batch/BATCH-004_楽天既存商品再確認バッチ仕様書.md` |
