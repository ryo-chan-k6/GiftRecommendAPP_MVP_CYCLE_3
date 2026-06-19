# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| --- | --- |
| Log ID | `2026-06-19-seed-canonical-supabase-seeds` |
| Log種別 | `human-decision` |
| 件名 | master seed 正本を `supabase/seeds/masters` + `config.toml` [db.seed] に移行する |
| 発生日時 | 2026-06-19 |
| 関連Issue | #660 |
| 関連Epic | #651 |
| 状態 | `resolved` |

---

## 2. 結論

- **master seed SQL 正本**: `supabase/seeds/masters/*.sql`
- **CLI 設定**: `supabase/config.toml` → `[db.seed] sql_paths = ["./seeds/masters/*.sql"]`
- **`supabase/seed.sql` 単体正本**: **非採用**
- **`db/seeds/`**: 移行完了のため **削除**（正本は `supabase/seeds/`）
- **`db/ddl/`**: Phase2 設計参照として **維持**（Option A。適用正本ではない）

---

## 3. 背景

Phase3b Task A4（Issue #660）で、`supabase/seed.sql` vs `db/seeds/` の未決定を解消する。Supabase CLI 採用（#591）後は CLI 管理下の modular seeds を正とする方が自然。

---

## 4. 影響

- docs 正本（DB構築手順書、マイグレーション方針書、初期データ定義書、ディレクトリ構成定義書等）
- `scripts/db/reset-local.sh` / `seed-masters.sh`
- Epic C C2（test-fixtures-seed）の前提

---

## 5. out_of_scope

- `supabase/migrations/**` DDL 変更
- `supabase/seeds/test-data/` 本体（Epic C）
- Phase2 完了 Task Definition の履歴表記一括更新
