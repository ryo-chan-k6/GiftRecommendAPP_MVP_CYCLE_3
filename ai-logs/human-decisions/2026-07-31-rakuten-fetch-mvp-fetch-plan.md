# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-07-31-rakuten-fetch-mvp-fetch-plan` |
| Log種別 | `human-decision` |
| 件名 | 楽天Fetch MVP対象ジャンルの具体的 `fetch_plan`（local live実行ゲート） |
| 発生日時 | 2026-07-31 |
| 記録日時 | 2026-07-31 |
| 発生元Command | `/work-issue @prompts/definitions/tasks/batch-live-rakuten-fetch/rakuten-fetch-local-live.yaml` |
| 関連Issue | #1765（BATCH-001〜004 local live実装） / #1763（楽天Fetch live切替） / #1749（運用方針） |
| 前提決定 | `2026-07-30-rakuten-fetch-ops-policy`（No.1でfetch_planを保留） |
| 重要度 | `high` |
| 状態 | `decided` |

本Logは、`2026-07-30-rakuten-fetch-ops-policy` No.1（MVP対象ジャンル保留）を解消し、
local live 実行前ゲートである具体的 `fetch_plan` をHuman承認するものである。

---

## 2. 結論（承認された fetch_plan）

| 項目 | 決定 |
| ---- | ---- |
| MVP対象ジャンルID | **`100000` / `100003` / `100004` / `100005`** |
| BATCH-001 起点 | 上記4 IDを起点とする |
| BATCH-001 階層展開 | **直下 `children` まで**同期する |
| BATCH-001 初回実行 | 4 IDのうち1 ID（例: `100000`）で開始 |
| BATCH-002 対象 | 上記4 IDすべて。初回smokeは1 ID × `max_pages=1` |
| BATCH-003 genre スコープ | 上記4 ID。初回smokeは1 ID |
| keyword route | **なし**（明示指定がある場合のみ実行する運用のまま、当面は使わない） |
| update_sort route | **初回オフ**。通常継続からオンにしてよい |
| ranking_supplement route | **オン**（backlogがある場合のみ消化。BATCH-002先行時に有効） |
| 初回低値条件 | 1ジャンル / 1 route × 1 cursor × 1ページ / `hits=3` |

---

## 3. 運用上の境界

- 本 `fetch_plan` は **local live（登録egress IPのlocalのみ）** に適用する。GHA楽天HTTPは当面禁止のまま（`2026-07-30` No.7）。
- 具体的ジャンルIDは設定正本／CLI入力（`--genre-ids`）で扱う。コードの placeholder（`DEFAULT_TARGET_GENRE_IDS`）を承認済み値として扱わない。
- Run予算（`pages_per_run=60` 等）、BATCH-004=100件開始、安全側QPS=1、paused/failed手動再開は `2026-07-30` の採択を継続する。本Logはそれらを変更しない。
- 対象拡大（keyword追加 / update_sort常用 / ジャンル追加）は継続取得の総量を増やすため、監視のうえ段階的に判断する。
- 実 local live の実行タイミング・secret投入・監視閾値抵触時の打ち切りは、引き続き実行時Human判断とする。

---

## 4. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| #1765 | 本 `fetch_plan` を用いた local live smoke（1ジャンル / hits=3）から段階実行 | 実行可（Human環境） |
| local live | 4 IDへ拡大 → 通常継続（Run予算・QPS遵守） | 段階 |
| BATCH-004 | 100件smoke → 3回連続正常後に段階拡張 | 後続 |
| update_sort / keyword | 必要時に採否を再判断 | 後続 |
| GHA楽天live / #1607 / schedule | 本Task外。別Issueで判断 | 対象外 |

---

## 5. 参照

- `ai-logs/human-decisions/2026-07-30-rakuten-fetch-ops-policy.md`
- `docs/15_運用・改善/運用手順/楽天Fetch運用方針.md`（§5.2 / §5.4 / §5.5）
- `docs/15_運用・改善/運用手順/楽天Fetch_local_live検証結果_1765.md`
- Issue #1763 / #1765
