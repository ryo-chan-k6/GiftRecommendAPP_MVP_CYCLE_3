# local cron Phase1 無人観測結果

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | 運用手順・観測結果正本（Phase1 cron-ops-verify） |
| 作成日 | 2026-08-25 |
| 関連Issue | [#1885](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1885)（本記録） / 親Epic [#1811](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1811) |
| 手順正本 | [local_cron_Phase1_crontab運用手順](./local_cron_Phase1_crontab運用手順.md) |
| Decision | [2026-08-01-batch-local-cron-ops-next](../../../ai-logs/human-decisions/2026-08-01-batch-local-cron-ops-next.md) |
| 関連 | [#1813](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1813) runbook / [#1816](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1816) スケジュール / [#1818](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1818) Phase2（並行・分離） |
| 状態 | 観測結果を同期済み。**Epic #1811 完了判断は Human** |

secret・token・APIキー・egress IP・接続文字列の実値は記載しない。  
本記録作成にあたり、AI は `--live-rakuten` を実行していない（ログ読取・DB 集計・docs 同期のみ）。

---

## 2. 目的

- Human 登録済み local cron の **数日〜数週間無人観測**を再現可能な形で残す
- 親シェル経由のみ・個別 cron 禁止・GHA schedule 非混入を確認記録する
- 失敗の主因クラスタと、後続修正（#1877 等）・IP 再整合後の回復を整理する
- 親 Epic #1811 の完了判断材料を揃える（判断自体は Human）

---

## 3. 登録済み記録（着手ゲート）

| 項目 | 内容 |
| ---- | ---- |
| Phase1 手順・ノブ | #1813 / PR #1814・#1815 |
| スケジュール採択 | #1816（daily=火〜日 05:00 JST / weekly=月曜 05:00 JST） |
| 実 crontab | Human 登録。実行パスはリポジトリルート（`develop` チェックアウト運用） |
| Phase2 `--run-meaning` | 2026-08-24 Human 登録済み（[Phase2 crontab載せ替え手順 §6](./local_cron_Phase2_crontab載せ替え手順.md) / #1870） |
| live 実行主体 | Human（cron および手動 smoke）。AI は記録同期のみ |

確認観点（2026-08-25 時点）:

| 観点 | 結果 |
| ---- | ---- |
| 親シェル経由のみ | **OK**（`local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh` のみ） |
| 個別 Batch cron | **無し** |
| GHA `on.schedule` | **コメントのまま未有効化**（daily/weekly orchestrator） |
| `--live-rakuten` 明示 | **あり** |
| 定常ノブ | `--genre-ids 100005` / `--ranking-genre-ids 100005` / `--pages-per-run=60` / `--max-qps 1` |
| `--run-meaning` | 2026-08-24 以降 **追加済み**（Phase1 観測期間の後半〜cutover 後） |

---

## 4. 観測期間とログ正本

| 項目 | 内容 |
| ---- | ---- |
| 主観測窓 | **2026-08-03 〜 2026-08-25**（JST） |
| ログ | `scripts/batch/output-local-orchestrator/cron-daily.log` / `cron-weekly.log`（gitignored） |
| 実行ディレクトリ | リポジトリルート（cron 行と一致） |

欠測日（05:00 起動ログなし）はホスト停止・スキップ等の可能性があり、本記録では **未確認**として扱う（例: daily の 08-13/15/17/22〜24 など）。

---

## 5. 集計サマリ

### 5.1 local-daily（親シェル結果）

観測窓内で `scenario=local-daily` の終端が確認できた run を集計（手動 smoke 含む）。

| 区分 | 件数（概数） | 備考 |
| ---- | ------------: | ---- |
| SUCCEEDED | 4 | 08-04 / 08-07（`run_meaning=0`）、08-25 06:33 / 13:37（`run_meaning=1`） |
| FAILED | 多数 | 主因は後述クラスタ |
| 05:00 定時っぽい run | 08-04〜08-21 に複数 | 多くが FAILED |

### 5.2 local-weekly（親シェル結果）

| 日時（JST） | 結果 | `run_meaning` | 失敗段 |
| ----------- | ---- | ------------- | ------ |
| 2026-08-03 05:00 | SUCCEEDED | （ログに未出力の世代） | — |
| 2026-08-10 05:00 | FAILED | 0 | `item_apply` |
| 2026-08-17 / 08-24 | ログなし | — | 未確認（欠測） |

### 5.3 失敗クラスタ（事実）

| クラスタ | 代表失敗段 | 観測上の位置づけ |
| -------- | ---------- | ---------------- |
| A | `item_apply`（BATCH-007） | 08-05〜08-12 前後に頻発。後に UniqueViolation（主画像）として #1876 / PR #1877 で修正 |
| B | `ranking_snapshot`（BATCH-002） | 08-14〜08-21 および 08-25 13:06 等。`error_log` に楽天 HTTP 403 を確認（egress / 許可 IP 不整合の推論が有力） |
| C | cutover 直後の手動 smoke | 08-25 早朝〜昼は修正・IP 再整合の途中で失敗が混在。13:37 再実行で SUCCEEDED |

AI は本 Task で live 再実行していない。08-25 13:37 の成功は Human 再実行ログの評価に基づく。

---

## 6. cutover 後の確認（#1818 関連・分離記録）

Phase2 Epic は **#1818 で close 済み**。本 Phase1 記録では、親シェル継続観測の一部として次のみ残す。

| 確認 | 結果 |
| ---- | ---- |
| meaning chain 配線 | ログに `diff_batch_run_id=<import pipeline>`（#1881） |
| 同一 run 商品の meaning | 13:37 run で import 更新商品が meaning 成果物まで到達（品質レビュー済み） |
| `#1811` | **完了扱いにしない**（本記録は verify 材料。Epic close は別 Human 判断） |

---

## 7. 定着判定（AI 提案・Human 確定待ち）

| 観点 | AI 判定案 | 根拠 |
| ---- | --------- | ---- |
| 親シェル経由のみ | **充足** | crontab 2 行のみ・個別 cron なし |
| 手順・スケジュール正本 | **充足** | #1813 / #1816 |
| 無人で起動し続けること | **部分充足** | 定時起動の実績あり。欠測日・長期失敗期間あり |
| Phase1（001〜008）安定完走 | **部分充足→改善後に回復** | 初期は item_apply / Ranking 403 で失敗多い。修正・IP 再整合後に成功例あり |
| secret 非露出 | **充足** | 本 docs / Issue に実値なし |
| GHA schedule 非混入 | **充足** | workflow はコメントのまま |

**推論:** 「手順どおりの無人運用枠は定着した」一方、「観測期間全体を成功率で合格とする」には Human 判断が必要（失敗期間が長いため）。

---

## 8. Human 判断依頼

| No | 判断 | 選択肢例 |
| --: | ---- | -------- |
| 1 | 本観測結果をもって **#1811 を Done/close してよいか** | close / 追加観測（例: 連続 N 日成功）後に close |
| 2 | ジャンルローテ（手順上は 1 本ローテ）を **100005 固定のまま継続**するか | 現状維持 / ローテ開始 |
| 3 | weekly 欠測（08-17 / 08-24）を追加確認するか | 次回月曜のログ確認のみ / 追加調査 |
| 4 | develop へ #1816 スケジュール本文が未反映だった件を、本 Epic PR でまとめて反映してよいか | 反映する（推奨） / 分離 PR |

推奨案: **No.1 は「追加で数日の定時成功を見てから close」または「修正反映後の成功をもって close」を Human が明示**。No.4 は本 Task / Epic 反映で develop に揃える。

---

## 9. out of scope（本記録に含めていないもの）

- GHA `on.schedule` 有効化（#1792）
- #1607 本番 egress
- BATCH-018 / 019
- AI による `--live-rakuten` / crontab 変更
- `--live-embedding` 既定 ON

---

## 10. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-25 | 初版（#1885）。2026-08-03〜08-25 の無人/手動観測を同期 |
