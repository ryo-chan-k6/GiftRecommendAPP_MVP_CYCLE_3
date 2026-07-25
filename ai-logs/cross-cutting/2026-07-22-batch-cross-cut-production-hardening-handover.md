# Cross-Cutting Impact Log — BATCH 横串・本実装向け改修 引継ぎメモ

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-07-22-batch-cross-cut-production-hardening-handover` |
| Log種別 | `cross-cutting` |
| 件名 | BATCH 全体横串チェック／横断整合性／本実装向け改修のエージェント引継ぎ |
| 発生日時 | 2026-07-22 |
| 記録日時 | 2026-07-22 |
| 発生元 | Human 依頼（BATCH 縦串レーン完了後の次フェーズ） |
| 関連会話 | Cursor agent transcript（BATCH-014〜019 縦串 → develop、worktree/remote 整理、初期 WBS Issue クローズ） |
| 重要度 | `high` |
| 状態 | `ready`（Human 方針確定済み。E0/E1 から Epic 起票可） |

> **本メモは作業計画の正本ではない。** Issue / Task Definition / `docs/` を正とする。チャット履歴は正本にしない。

---

## 2. 30秒サマリ

| 項目 | 内容 |
| ---- | ---- |
| いま終わっていること | **BATCH-001〜019 の識別子単位縦串**（仕様→実装→UT→Epic PR→`develop`）が一通り完了 |
| `develop` tip（記録時点） | `6135965c` … `[Epic]BATCH-019:Feedback分析Batch (#1531)` |
| いまの焦点 | **全体横串チェック・横断整合性・本実装向け改修**（個別 BATCH 新規縦串ではない） |
| 最大ギャップ | **親 workflow オーケストレーション未実装**（日次／週次／手動）。子 19 本は独立 `workflow_call` + `workflow_dispatch` |
| MVP 区分 | 001〜017 = ○、018・019 = △（scaffold-first）。**本レーンでは 018/019 本格化は後回し** |
| Epic 方針 | **テーマ分割**（1 巨大 Epic にしない）。着手順は §6.1 |
| 棚卸し成果物 | **`docs/` に正本として残す**（`ai-logs` のみで終わらせない） |
| やってはいけないこと | `main`/`develop` 直 push、PR merge、secret 露出、generated 手動編集、スコープ不明の広範リファクタ、Human 未承認の破壊的 DDL／契約変更 |

---

## 3. 必読（この順）

1. [AGENTS.md](../../AGENTS.md)
2. [バッチ設計方針書](../../docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md)
3. [バッチ処理一覧](../../docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md) … MVP ○/△、入出力、モジュール
4. [バッチ依存関係図](../../docs/05_アプリケーション設計/アプリ/batch/バッチ依存関係図.md)
5. [バッチ実行スケジュール設計書](../../docs/05_アプリケーション設計/アプリ/batch/バッチ実行スケジュール設計書.md) … **親/子 workflow 正本**
6. 個別正本: `docs/06_実装設計/batch/BATCH-NNN_*.md`（特に各 §18 Human 確定）
7. モジュール一覧の `MOD-BATCH-*`（評価・改善の △: 042〜044）
8. 関連 DB: `docs/06_実装設計/database/`（テーブル定義・migration・初期データ）
9. 運用: Issue / Projects / Branch / worktree Rules（`.cursor/rules/`）

補助:

- `apps/batch/src/batch/application/**`（実装）
- `.github/workflows/batch-*.yml`（子 19 本。親 orchestrator は **未作成**）
- `prompts/definitions/epics/batch-*/` / `prompts/definitions/tasks/batch-*/`
- Machine account: `.github/ai-bot-account.json` / `node .github/scripts/gh-bot-auth.cjs print-setup`

---

## 4. 完了済み（事実）

### 4.1 縦串

| 範囲 | 状態 |
| ---- | ---- |
| BATCH-001〜019 | 仕様書 + application パッケージ + 子 workflow + UT（件数は Batch により異なる）が `develop` に存在 |
| Epic | 識別子単位 Epic は CLOSED（例: BATCH-019 = #1522 / PR #1531 MERGED） |
| 子 workflow | `.github/workflows/batch-*.yml` **19 本**（独立 cron なしが原則。`workflow_call` / `workflow_dispatch`） |

### 4.2 実装配置（`apps/batch/src/batch/application/`）

代表ディレクトリ（記録時点）:

`genre_sync` / `ranking_snapshot` / `item_pseudo_diff` / `item_recheck` / `raw_staging` / `product_diff` / `item_apply` / `item_active_status` / `item_generation_queue` / `item_semantic` / `feature_input_hash` / `item_feature` / `feature_normalization` / `embedding_input_hash` / `item_embedding` / `distribution_metrics` / `import_summary` / `offline_evaluation` / `feedback_analysis`  
＋共通: `runner.py` / `stages.py` / `job_run` / `_scaffold.py` 等

### 4.3 運用整理（同レーンで実施済み）

| 作業 | 結果 |
| ---- | ---- |
| BATCH-014〜019 worktree | 削除済み |
| マージ済み remote Branch | 大量削除済み（残は open PR・残 worktree・未確認分） |
| 初期 WBS Issue（領域単位） | 重複分を `not planned` クローズ（例: #110/#115/#118/#120/#128〜#131 等）。**物理削除ではない** |

---

## 5. 現状ギャップ（事実と推論を分離）

### 5.1 事実（リポジトリで確認可能）

| ギャップ | 根拠 |
| -------- | ---- |
| 親 orchestrator 未作成 | `batch-daily-orchestrator.yml` / `batch-weekly-orchestrator.yml` / `batch-manual-orchestrator.yml` が workflows に無い。スケジュール設計書 §3 では必須方針 |
| 子は独立起動前提 | 各子は `workflow_call` + `workflow_dispatch`。親 `jobs.needs` 接続は各 BATCH 仕様 §18 で「後続／Epic 外」とされたものが多い |
| MVP △（018 / 019） | 一覧上 △。018 は IF-SHARED-004 **mock**、評価系 INSERT 契約あり。019 は出力物理 DDL を持たない scaffold、IF-DB-BATCH-019 stub、metric を JSON 内包、など Human 確定あり |
| MOD-BATCH-043 / 044 | モジュール一覧 MVP △。BATCH-019 縦串では **out of scope** |
| DB 系 OPEN Issue 残 | 例: #102 / #109 / #133 / #136（DDL・migration 系。初期 WBS。完了度は要再判定） |
| 分析系 OPEN Issue 残 | 例: #149 / #150 / #151 / #154（サービス分析設計。BATCH-016/018/019 と重複しうる） |

### 5.2 推論（横串で見ると起きやすい問題）

| 推論 | 内容 |
| ---- | ---- |
| I/F・命名の揺れ | Batch ID / IF-DB-BATCH-NNN / MOD-BATCH-* / workflow 名 / env prefix（`BATCH_*`）の横断不一致が残りうる |
| stub 深度のバラつき | 楽天・OpenAI・Reco・DB の mock/stub 度合いが Batch ごとに異なる。本実装優先度の棚卸しが必要 |
| ログ／メトリクス | `batch_run_log` / `phase_log` / `error_log` / `item_import_summary` の書式・必須列・部分成功（GRS-BAT-*）の扱いが揃っていない可能性 |
| Config／version | `semantic_config_version_id` 等の解決が stub UUID のままの箇所がある（018 仕様でも明示） |
| テスト | 単体は厚い Batch と薄い Batch が混在。横串の契約テスト／workflow dry-run は未整備の可能性が高い |

---

## 6. Human 確定方針（2026-07-22）

| # | 論点 | 確定 |
| - | ---- | ---- |
| 1 | Epic 粒度 | **テーマ分割**（1 巨大 Epic にしない） |
| 2 | 親 workflow | **最優先で実装してよい** |
| 3 | BATCH-018 / 019 | **△ のまま後回し**（本レーンの本実装バックログに含めない） |
| 4 | OPEN Issue（#102/#109/#133/#136/#149〜#154） | **未確定**（棚卸し Epic で突合し、取込／別扱い／クローズ案を docs に書いて Human 確認） |
| 5 | 棚卸し成果物 | **`docs/` に正本として残す** |

### 6.1 Epic 分割案（推奨・着手順）

新規作業は **必ず Task Definition → Issue → Branch/worktree → PR**。各 Epic は独立 Branch／独立 PR。並列は worktree 分離必須。

| 順 | 推奨 Epic タイトル | 主成果 | in scope | out of scope（明示） |
| -- | ----------------- | ------ | -------- | -------------------- |
| **E0** | `[Epic]batch-cross-cut-inventory:横串棚卸し・整合性` | **docs 正本**（ギャップ表・stub 深度・§18 後続一覧・OPEN Issue 突合案） | 調査・差分表・docs 追記／新規。実装の大規模変更はしない | 親 workflow 実装、DDL、mock 解除、018/019 本格化 |
| **E1** | `[Epic]batch-parent-orchestrators:親workflow実装` | `batch-daily/weekly/manual-orchestrator.yml` + 必要ならスケジュール設計書の実装差分追記 | 親 3 本、`jobs.needs`、cron は親のみ、concurrency／失敗方針 | 子 Batch の業務ロジック改修、018/019 を本線に載せる変更、DDL |
| **E2** | `[Epic]batch-db-ddl-hardening:IF・DB・DDL本実装` | IF-DB stub 解除計画の実行、不足 DDL/migration、001〜017 中心の実 DB 接続 | DB／migration／IF-DB、関連 UT。#109/#133/#136 との関係整理 | 親 workflow 新規、外部 API 本接続、018/019 出力物理 DDL 本格整備 |
| **E3** | `[Epic]batch-external-integration:外部接続本実装` | 楽天・Embedding 等の mock／stub 解除（001〜017 範囲） | 外部 API client、retry／rate limit、env 名の docs 反映 | Reco IF-SHARED-004（018）、019 本格化、親 workflow |
| **E4** | `[Epic]batch-observability-standard:観測横断標準化` | `batch_run_log` / phase / error / import_summary 等の横断契約・実装揃え | ログ／メトリクス契約、必要なら共通 runner 改修 | 業務計算ロジックの刷新、018/019 本格化 |

**後続（本レーン外・起票保留）:**

```text
[Epic]batch-018-019-production:評価・Feedback本格化  （△ 解除時。Human が別途開始）
```

- E0 → **E1 を最優先**（Human 確定）。E0 の docs が薄くても、スケジュール設計書が正本として揃っているため **E1 先行着手可**。
- E2〜E4 の順序は E0 の棚卸し結果で調整してよい（並列候補は E2∥E3、観測は依存が少ない場合 E4 を前倒し可）。
- 識別子規約は既存どおり `[Epic]` 直後スペースなし。最終タイトルは Task Definition / Issue 起票時に微調整可。

### 6.2 E0 — 横串棚卸し（docs 正本）

確認観点:

- [ ] BATCH-001〜019 と `application/*`・`batch-*.yml`・仕様書パスの 1:1
- [ ] 依存関係図 vs 親 schedule 設計書 vs 実装（子のみ）の差分表
- [ ] 各 §18 Human 確定の「後続」「Epic 外」「stub」一覧化（018/019 は「後回し」と明記）
- [ ] env / secrets **名**の一覧（`.env` 実値は出さない）
- [ ] UT カバレッジの Batch 別サマリ
- [ ] OPEN の #102/#109/#133/#136/#149〜#154 と E2 以降の関係（案を docs に書く）

**成果物配置（推奨）:**

| 成果物 | 推奨パス |
| ------ | -------- |
| 横串ギャップ・整合表 | `docs/05_アプリケーション設計/アプリ/batch/バッチ横串整合・本実装ギャップ一覧.md`（新規） |
| 既存正本への追記 | 必要なら一覧／スケジュール／依存関係図に「実装状況」節を追加（重複しすぎない） |

棚卸し中の下書きは `ai-logs/cross-cutting/` に置いてよいが、**完了時は docs へ昇格**する。

### 6.3 E1 — 親 orchestrator 実装（最優先）

正本: [バッチ実行スケジュール設計書](../../docs/05_アプリケーション設計/アプリ/batch/バッチ実行スケジュール設計書.md)

| 親 | 役割 |
| -- | ---- |
| `batch-daily-orchestrator.yml` | 日次本線 + `jobs.needs` |
| `batch-weekly-orchestrator.yml` | 週次（日次相当を内包する設計） |
| `batch-manual-orchestrator.yml` | 再実行・評価など手動シナリオ |

制約:

- cron は原則親のみ。子の独立 cron を復活させない
- concurrency・失敗時方針は設計書に従う
- **018/019 は本線に載せない**（△ 後回し。手動シナリオに載せる場合も Human 確認）
- 週次に載せる Batch 集合は設計書どおり。設計書と実装差が出たら停止して報告

### 6.4 E2〜E4 — 本実装向け（018/019 除外）

| Epic | 含める | 含めない（Human 確定） |
| ---- | ------ | ---------------------- |
| E2 DB/DDL | 001〜017 の IF-DB・不足 DDL、config version 実解決のうち DB 側 | 019 出力物理 DDL、018 評価系テーブル本格化 |
| E3 外部接続 | 楽天・Embedding 等（一覧 MVP ○） | IF-SHARED-004（018）、Feedback 本格分析パイプライン |
| E4 観測 | 共通ログ／メトリクス契約 | MOD-BATCH-043/044 本格実装 |

### 6.5 回帰（各 Epic 共通）

- `apps/batch` の unit（当該差分範囲）
- 必要なら `workflow_dispatch` の dry-run
- AI Review → Human Review → **merge は Human のみ**

---

## 7. 作業ガード

| # | 条件 |
| - | ---- |
| 1 | base は原則 `develop` 起点の **新 Epic Branch**（既存 BATCH 縦串 worktree は片付け済み） |
| 2 | Task PR は親 Epic Branch 向け。`develop` 直 Task PR 禁止 |
| 3 | commit / push / PR は `okuri-ai-bot`（`gh-bot-auth.cjs print-setup`） |
| 4 | secret・`.env` 実値を Issue/PR/docs/logs に出さない |
| 5 | 正本矛盾（一覧 vs 仕様 vs 実装）は独断解消せず Human へ停止報告 |
| 6 | DDL / OpenAPI / 破壊的変更は Human 承認必須 |
| 7 | PoC（#1532/#1535 等）や web/reco 本線を無断で巻き込まない |
| 8 | 018/019 本格化・親本線への組込は本レーン外（Human が別 Epic 開始するまで触らない） |
| 9 | 1 巨大 Epic に戻さない。E0〜E4 の境界をまたぐ変更は別 Epic／Human 確認 |

---

## 8. 参考 Issue（OPEN・要突合）

| Issue | タイトル | 引継ぎ上の扱い（推論） |
| ----- | -------- | ---------------------- |
| #102 | アプリ機能実装設計（db） | 初期 WBS。DDL 親と関係。完了判定は横串で再確認 |
| #109 | DDL作成 | 本実装 DDL と直結しうる |
| #133 | DB構築 | 同上 |
| #136 | マイグレーションファイル作成 | migrations は一部存在。差分棚卸し要 |
| #149〜#154 | サービス分析設計一式 | BATCH-016/018/019 と重複しうる。閉じる／統合は Human |
| #127 | 環境変数定義書作成 | `（未作成）環境変数定義書.md` あり。batch env 横断と関係 |

PoC 系（#1532 / #1535 / #1536）は **本レーン外**。触らない。

---

## 9. 開始時チェックコマンド

```bash
pwd
git fetch origin
git checkout develop && git pull --ff-only origin develop
git log -1 --oneline
ls .github/workflows/batch-*.yml | wc -l   # 期待: 19
ls .github/workflows/ | rg 'orchestrator' || true  # 期待: 親なし
cd apps/batch && uv run python -m pytest tests/unit -q --tb=line
```

認証:

```bash
eval "$(node .github/scripts/gh-bot-auth.cjs print-setup)"
export GH_TOKEN="$GH_BOT_TOKEN"
```

---

## 10. 残 Human 判断（未確定）

1. OPEN の #102 / #109 / #133 / #136 / #149〜#154 を **E2（DB）に取り込むか／別扱い／クローズするか**（E0 棚卸しで案を docs に書き、Human が確定）
2. E2 / E3 / E4 の着手順・並列可否（E0 結果後で可。デフォルトは E1 完了後に E2）
3. E0 新規 docs の正式ファイル名（§6.2 推奨名でよいか）

---

## 11. 関連リンク（記録時点）

| 種別 | 例 |
| ---- | -- |
| 直近 Epic PR | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/pull/1531 （BATCH-019） |
| スケジュール正本 | `docs/05_アプリケーション設計/アプリ/batch/バッチ実行スケジュール設計書.md` |
| 一覧正本 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` |
| 本引継ぎ | `ai-logs/cross-cutting/2026-07-22-batch-cross-cut-production-hardening-handover.md` |

---

## 12. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-22 | 初版作成（縦串完了後の横串・本実装フェーズ引継ぎ） |
| 2026-07-22 | Human 確定反映: Epic 分割、親 workflow 最優先、018/019 後回し、棚卸しは docs 正本。§6 を E0〜E4 に再構成 |
