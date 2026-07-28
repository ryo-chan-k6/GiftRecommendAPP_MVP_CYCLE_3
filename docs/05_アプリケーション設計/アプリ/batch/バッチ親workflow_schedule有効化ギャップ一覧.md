# バッチ親workflow schedule 有効化ギャップ一覧

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | #1637 Wave 0 棚卸し正本（docs） |
| 対象 | 親 / 複合 batch orchestrator の `on.schedule` / `workflow_dispatch` 検証 |
| 作成日 | 2026-07-28 |
| 関連 Epic | [#1637](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1637)（batch-parent-schedule） |
| 先行 | E1 [#1554](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1554)（親 YAML 実装。Phase1 schedule 無効） |
| 関連完了 | E4 [#1636](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1636)（観測横断。schedule は E4 out of scope） |

### 1.1 目的

E1 残（schedule 無効・親／複合の手動検証未実施）を docs 正本化し、後続 Wave 分割と **Human 判断材料**を残す。  
**本 Task（Wave 0）では schedule コメント解除・本番定期開始は行わない。**

### 1.2 out of scope

| out of scope | 理由 |
| ------------ | ---- |
| production 無承認の定期実行開始 | Epic #1637 / 本正本の禁止事項 |
| SELECT / 書込 IF の再実装 | #1623 / #1632〜#1635 |
| E4 観測の再実装 | #1636 完了 |
| #1607 本番 egress | 別 Issue |
| BATCH-018 / 019 を本線 schedule に載せる | スケジュール設計書 §16.4 |
| 子 workflow への schedule 付与 | 設計方針（子は schedule なし） |

### 1.3 区分

| 区分 | 意味 |
| ---- | ---- |
| 事実 | 正本 docs・YAML・Issue から確認できる内容 |
| 推論 | 事実から導いた影響・推奨（断定しない） |
| Human 判断待ち | 本ドキュメントでは確定扱いにしない |

---

## 2. 30秒サマリ（事実）

| 項目 | 状態 |
| ---- | ---- |
| 親 YAML | daily / weekly / manual **作成済み**（E1） |
| 複合子 | item-import / meaning / retry / existing-item-pipeline **作成済み** |
| daily / weekly `on.schedule` | **コメントアウト（Phase1 無効）** |
| manual | schedule なし（設計どおり） |
| 親 `dry_run` input | **なし**（018/019 独立子のみ `dry_run` あり） |
| 親／複合の workflow_dispatch 実ランタイム検証 | **未実施**（E1 は YAML 確認で代替） |
| concurrency | 親 daily/weekly は `batch-mainline` 共有 |
| E4 観測 | develop 統合済み。本線実行時の観測前提は揃っている |

---

## 3. 対象 workflow 現状（事実）

| ファイル | 種別 | schedule | cron（コメント内） | workflow_dispatch | concurrency |
| -------- | ---- | -------- | ------------------ | ----------------- | ----------- |
| `batch-daily-orchestrator.yml` | 親 | **無効** | `"10 16 * * 0-5"`（JST 月〜土 01:10） | あり（`max_items`, `run_retry_after`） | `batch-mainline` |
| `batch-weekly-orchestrator.yml` | 親 | **無効** | `"10 16 * * 6"`（JST 日 01:10） | あり（`max_items`, `run_offline_evaluation`） | `batch-mainline` |
| `batch-manual-orchestrator.yml` | 親 | なし | — | あり（`scenario` 必須等） | `batch-manual-${{ inputs.scenario }}` |
| `batch-rakuten-item-import.yml` 等 複合4本 | 複合 | なし | — | あり | 専用 group |

出典: `.github/workflows/*.yml` / [バッチ実行スケジュール設計書](./バッチ実行スケジュール設計書.md) §6・§16・§19

---

## 4. 正本 Phase 方針（事実）

正本: [バッチ実行スケジュール設計書](./バッチ実行スケジュール設計書.md)

| Phase | 節 | 内容 |
| ----- | -- | ---- |
| **1** | §16.1 / §19.4 | 親 `on.schedule` **無効**。`workflow_dispatch` で検証 |
| **2** | §16.2 | **daily** cron 有効化（基本処理安定後） |
| **3** | §16.3 | **weekly** cron 有効化（鮮度維持が必要になったら） |
| **4** | §16.4 | 018/019 または manual シナリオ（本線外） |

設計 cron（§6）は YAML コメントと一致。

---

## 5. E1 残ギャップとの対応（事実）

[バッチ横串整合・本実装ギャップ一覧](./バッチ横串整合・本実装ギャップ一覧.md) §2 / §4.3 / §10:

| 残ギャップ | #1637 での扱い |
| ---------- | -------------- |
| Phase1 schedule 無効のまま | Wave 0 で現状固定。有効化は Human 確定後 Wave |
| 親／複合 workflow_dispatch dry-run 未実施 | 手動検証 Wave。定義は §8 Human 判断 |

---

## 6. 推奨 Wave 分割（推論）

| 優先 | Wave | 内容 | Human 必須 |
| ---- | ---- | ---- | ---------- |
| high | **0** | 本正本（inventory） | 不要（docs のみ） |
| high | **gate** | §8 案 A/B/C・dry-run 定義・失敗通知の確定 | **必須** |
| high | **1** | 手動検証（低 `max_items` の `workflow_dispatch`）+ 結果記録 | 実行環境・コスト承認 |
| medium | **2** | 案 B 以降: daily schedule コメント解除 | 有効化承認 |
| medium | **3** | 案 C 時: weekly schedule 有効化 | 有効化承認 |
| low | **docs** | 横串ギャップ / §19.4 を Phase 進行に合わせて更新 | レビュー |

---

## 7. dry-run 定義の整理（事実 + Human 判断待ち）

| 方式 | 事実 | 含意 |
| ---- | ---- | ---- |
| **D1** | 親 YAML に `dry_run` input **なし**。低 `max_items` で `workflow_dispatch` し本線ジョブを短く回す | コスト・外部 API は発生しうるが追加実装が少ない |
| **D2** | 親／複合に `dry_run` を新規追加し、子へ伝播して DB/API を抑止 | 実装・契約変更が必要。真の dry-run に近い |

**推論:** Wave 1 の第一候補は D1（E1 残の「未実施」解消が主目的）。D2 は別 Task 化を推奨。

---

## 8. Human 判断点 — **未確定**

### 8.1 schedule 有効化方針

| 案 | 内容 | メリット | デメリット |
| -- | ---- | -------- | ---------- |
| **A** | Phase1 維持。schedule は触らず、dispatch 手動検証＋docs 記録のみ | 定期実行なしで安全。検証ギャップを先に解消 | 定期運用は先送り |
| **B** | §16 どおり Phase2 のみ（**daily** cron 有効化。weekly は無効のまま） | 設計正本と一致。同日 daily+weekly 競合を避けやすい | 本線 API/DB コスト。失敗通知方針が要る |
| **C** | Phase2+3 同時、または週次優先 | 鮮度メンテを早く回せる | 段階的有効化と乖離。`batch-mainline` 共有下の運用リスク |

**推奨（推論・未確定）:** まず **案 A** で手動検証を完了し、安定確認後に **案 B**。案 C は観測・コスト確認後。

### 8.2 dry-run 定義

| 案 | 内容 |
| -- | ---- |
| **D1** | 低 `max_items` の親 `workflow_dispatch` を「手動検証」として記録する（input 追加なし） |
| **D2** | 親／複合に `dry_run` input を追加する |

**推奨（推論・未確定）:** **D1**

### 8.3 失敗時通知 / タイムゾーン

| 項目 | 現状（事実） | Human 判断 |
| ---- | ------------ | ---------- |
| cron TZ | UTC cron で JST 01:10 相当（設計 §6 / YAML コメント） | 変更要否 |
| 失敗通知 | YAML 上の専用 notify job は未確認（Actions 標準 UI / 別運用） | Slack / GitHub 通知の要否と担当 |

### 8.4 production 定期開始

Epic out_of_scope: **無承認の production 定期開始は禁止**。  
案 B/C で schedule を有効化する PR でも、**対象環境・Secret・リポジトリ設定**が本番定期を意味する場合は別途 Human 明示承認が必要。

---

## 9. 完了条件（Wave 0）

- [x] 親／複合の schedule / dispatch 現状表
- [x] §16 Phase 対応と E1 残ギャップの突合
- [x] Human 判断点（§8）の整理
- [x] 後続 Wave 分割案
- [ ] Human による §8 確定（後続 Wave の前提）

---

## 10. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-28 | 初版（#1637 Wave 0 inventory） |
