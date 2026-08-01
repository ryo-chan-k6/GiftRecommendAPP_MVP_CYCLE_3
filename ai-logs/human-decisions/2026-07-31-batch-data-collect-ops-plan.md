# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-07-31-batch-data-collect-ops-plan` |
| Log種別 | `human-decision` |
| 件名 | 本格収集運用枠（B-0下 local・ジャンル段階・期間/Run数・予算ノブ・停止・監視見直し） |
| 発生日時 | 2026-07-31 |
| 記録日時 | 2026-07-31 |
| 発生元Command | `/work-issue @prompts/definitions/tasks/batch-data-collect-ops/ops-plan-decision.yaml` |
| 関連Issue | #1799（本Decision） / #1798（親Epic・本線#6） / #1745（統括） / #1789（B-0） / #1763（local live経路） |
| 前提決定 | `2026-07-30-rakuten-fetch-ops-policy` / `2026-07-31-rakuten-fetch-mvp-fetch-plan` / `2026-07-31-batch-daily-schedule-enable-b0` |
| 重要度 | `high` |
| 状態 | `decided` |

本Logは、統括#1745本線#6（#1798）の着手ゲートとして、B-0下の local 本格収集について
「何を・どこまで・いつ止めるか」を Human 採択するものである。
収集実行本体・schedule有効化・GHA楽天live・#1607・secret変更は含めない。

---

## 2. 結論

案A（段階拡大・期間上限付き本格収集）を採択する。期間/Run数上限は Human 補足どおり **最大7日** とする。

| No | 論点 | 決定 |
| --: | ---- | ---- |
| 1 | パッケージ | **案A**（段階拡大。加速ノブ `pages_per_run=100` は本Epicでは使わない） |
| 2 | ジャンル段階 | **段階1→2→3→4**（下表）。常に楽天liveは1本のみ |
| 3 | 期間 / Run数 | **最大7日、または BATCH-003 の累計 Run 20回**（どちらか先）。到達で一旦停止し、Epic内で継続可否を再判断 |
| 4 | Run予算ノブ | 段階1=初期live。段階2以降=通常継続。既存 §5.3.4 採択値を変更しない |
| 5 | BATCH-001/002/004 | 既存採択を維持（下表）。本Decisionで件数・深さ方針は変更しない |
| 6 | 停止 / エスカレーション | §5.3.5ハード・同日429再発・egress不一致・secret漏えい疑い・同時live検知・期間/Run上限到達 → 追加Run停止＋Human通知。恒久のカタログ深さ打ち切りはしない |
| 7 | §5.3.5見直し計画 | 段階2完了時点、または本格収集開始から7日経過のどちらか早い時点で実測レビュー（維持も可）。結果は後続 `local-collect-and-monitor` でdocs反映 |
| 8 | 実行場所境界 | **localのみ**。GHA楽天HTTP禁止・B-0（schedule無効）・#1607外・secret実値非記載を維持 |

### 2.1 ジャンル段階

| 段階 | 内容 | Run予算（BATCH-003） | 進行条件 |
| ---- | ---- | -------------------- | -------- |
| 1 | 1ジャンル（例: `100000`） | 初期live相当: `pages_per_run=10` / `cursors_per_run=1` / route 1 / `hits=30` / wall-clock 20分 | 2〜3 Run。429なし・失敗なし・ログ追跡可能 |
| 2 | 同1ジャンルで通常継続 | 通常継続: `pages_per_run=60` / `cursors_per_run=1` / route 1 / `hits=30` / 45分 | 3 Run以上・429なしを確認 |
| 3 | 残り3ジャンル（`100003` / `100004` / `100005`）へ順次拡大 | 各ジャンルは段階1→2を短縮してよい（Human実行時判断） | 1ジャンルずつ。同時liveは禁止 |
| 4 | 4ジャンル運用 | 通常継続ノブ | **並列liveはしない**。常に楽天live 1本 |

承認済み fetch_plan（`100000` / `100003` / `100004` / `100005`・直下 children・keywordなし）は変更しない。

### 2.2 BATCH-001 / 002 / 004

| Batch | 扱い |
| ----- | ---- |
| BATCH-001 | 段階3前に必要なら承認済み4 ID起点。初回は1 ID |
| BATCH-002 | smoke後に4 ID × `max_pages=1` |
| BATCH-004 | 100件開始。3回連続正常後の段階拡張は既存採択どおり（本Decisionで変更しない） |

### 2.3 停止条件（本格収集キャンペーン）

以下のいずれかで **追加の本格収集 Run を停止**し Human へ通知する（cursor position は保持。カタログ深さ方針の撤回ではない）。

1. §5.3.5 ハード閾値到達
2. 同一日に429再発、または同一Runで429再発
3. egress IP照合不一致・未確認
4. secret漏えいの疑い
5. 想定外の同時楽天live検知
6. **期間上限（開始から最大7日）または BATCH-003 累計 Run 20回**（どちらか先）

期間/Run上限到達後の継続は、Epic #1798 内で別途 Human 再判断する（本Logだけでは無期限継続を許可しない）。

### 2.4 §5.3.5 監視閾値見直し計画

| 項目 | 決定 |
| ---- | ---- |
| 見直し時点 | 段階2完了、または本格収集開始から7日経過のどちらか早い方 |
| 対象 | [楽天Fetch運用方針](../../docs/15_運用・改善/運用手順/楽天Fetch運用方針.md) §5.3.5 の警告/ハード |
| 採否 | 実測に基づく見直し、または維持。最終採択は後続 Task（`local-collect-and-monitor`）で Human 確認 |
| 非対象 | 本Taskでの閾値実測そのもの（実行は後続） |

---

## 3. 運用上の境界

- 本枠は **B-0下の local 本格収集**に限定する。daily/weekly `on.schedule` 有効化（#1792 / B-1）は含めない。
- GHA / GitHub-hosted からの楽天HTTP live、#1607（固定egress）は含めない。
- 常用QPS=2・ハードキャップ10・安全側QPS=1（長時間/003・004/429後）は既存決定を維持する。
- Run予算到達での停止は1 Runのチャンク終端であり、本格収集キャンペーンの期間/Run上限とは別概念である。
- secret・接続文字列・token実値は docs / Issue / PR / 本Log に記載しない。
- チャット上の同意だけでは正本とせず、本Log（`decided`）と運用方針同期を正本とする。

---

## 4. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| #1799 | 本Decision Log・楽天Fetch運用方針同期・後続Task着手ゲート反映 | 実施対象 |
| `local-collect-and-monitor` | 本枠に従い local 継続収集＋§5.3.5実測見直し | 本Decision `decided` 後に着手可 |
| #1798 | 期間/Run上限到達後の継続可否再判断 | 条件到達時 |
| #1792 / #1607 / GHA楽天live | 本Decision外 | 対象外 |
| #1745 | 本線#6追跡（Epic側で更新） | 後続 |

---

## 5. 参照

- `docs/15_運用・改善/運用手順/楽天Fetch運用方針.md`
- `ai-logs/human-decisions/2026-07-30-rakuten-fetch-ops-policy.md`
- `ai-logs/human-decisions/2026-07-31-rakuten-fetch-mvp-fetch-plan.md`
- `ai-logs/human-decisions/2026-07-31-batch-daily-schedule-enable-b0.md`
- Issue #1799 / #1798 / #1745 / #1789 / #1763
