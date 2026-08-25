# local cron Phase2 crontab 載せ替え手順（cron-cutover）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | 運用手順正本（Phase2 crontab 載せ替え） |
| 作成日 | 2026-08-24 |
| 関連Issue | [#1870](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1870) / 親Epic [#1818](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1818) |
| 前提Decision | [Phase2 cutover ゲート明示承認](../../../ai-logs/human-decisions/2026-08-24-batch-local-cron-phase2-cutover-gate.md)（`decided`・選択肢 B） |
| 前提検証 | [Phase2 dry-run 検証結果](./local_cron_Phase2_dry-run検証結果.md)（#1824） |
| Phase1 正本 | [Phase1 crontab運用手順](./local_cron_Phase1_crontab運用手順.md)（#1813） |
| 親シェル設計 | [local薄いオーケストレータ設計・運用手順](./local薄いオーケストレータ設計・運用手順.md) §11〜§15 |
| 状態 | 手順正本化済み。**Human が 2026-08-24 に `--run-meaning` 登録済み**（§6）。AI は登録実行・`--live-rakuten` しない |

secret・token・APIキー・接続文字列・`.env` 実値は記載しない。

---

## 2. 目的と非目的

### 2.1 目的

- Phase1 定常 cron 行へ **`--run-meaning`** を追加し、BATCH-009〜016 を親シェル経由で opt-in する
- Human 向け登録チェックリストと、登録後の記録欄を正本化する

### 2.2 非目的

| 対象 | 扱い |
| ---- | ---- |
| AI による `crontab` 実編集 | **禁止** |
| AI による `--live-rakuten` | **禁止** |
| Phase1 #1811 の完了判断 | **しない**（分離維持） |
| 案B `--genre-ids` の定常反映 | **本手順外**（別承認） |
| `--live-embedding` の既定 ON | **本手順では入れない**（課金・別 Human 判断） |
| GHA schedule / #1607 / GHA 楽天 live | 対象外維持 |
| 子 Batch の個別 cron | **禁止** |

---

## 3. 着手ゲート（満た済み）

| 条件 | 状態 |
| ---- | ---- |
| (A) Phase1 観測完了 | 未充足（#1811 OPEN） |
| (B) Human 明示承認 | **充足**（[2026-08-24 Decision](../../../ai-logs/human-decisions/2026-08-24-batch-local-cron-phase2-cutover-gate.md)） |

本載せ替えは **(B)** により先行する。

---

## 4. 載せ替え内容（採択方針）

### 4.1 変更するフラグ

| 項目 | 変更前（現行 Phase1） | 変更後（Phase2） |
| ---- | -------------------- | ---------------- |
| `--run-meaning` | **なし**（009〜016 スキップ） | **追加**（009〜016 実行） |
| `--live-rakuten` | あり | **維持** |
| `--genre-ids` | `100005`（例） | **維持**（案B 非反映） |
| `--ranking-genre-ids` | `100005` | **維持** |
| `--pages-per-run` / `--max-qps` | `60` / `1` | **維持** |
| `--live-embedding` | なし | **追加しない**（必要時は別判断） |

### 4.2 行の例（参考・パスは環境に合わせる）

```cron
# daily（火〜日 05:00 JST の例。曜日は現行 crontab を正とする）
0 5 * * 0,2-6  cd /home/ryo-c/GitHub/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_daily_orchestrator.sh --live-rakuten --run-meaning --genre-ids 100005 --ranking-genre-ids 100005 --pages-per-run=60 --max-qps 1 >> scripts/batch/output-local-orchestrator/cron-daily.log 2>&1

# weekly（月曜 05:00 JST の例）
0 5 * * 1      cd /home/ryo-c/GitHub/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_weekly_orchestrator.sh --live-rakuten --run-meaning --genre-ids 100005 --ranking-genre-ids 100005 --pages-per-run=60 --max-qps 1 >> scripts/batch/output-local-orchestrator/cron-weekly.log 2>&1
```

差分は実質 **`--run-meaning` の挿入のみ**。時刻・パス・他ノブは現行行を壊さない。

### 4.3 実行コードの前提

- cron の `cd` 先は **develop 取り込み済み**であること（#1869 反映後の pull 推奨）
- 親シェルは `local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh` のみ

---

## 5. Human 登録チェックリスト

実施前:

| No | 確認 | 実施 |
| --: | ---- | ---- |
| 1 | cutover ゲート Decision（B）が `decided` | Human |
| 2 | develop が pull 済み（修正バッチ・`--run-meaning` 配線） | Human |
| 3 | 他の楽天 live（手動・キャンペーン）が動いていない | Human |
| 4 | 現行 `crontab -l` をバックアップ（ローカルメモ可。secret なし） | Human |
| 5 | 変更は daily / weekly の親シェル行のみ（個別 Batch cron を増やさない） | Human |

実施:

| No | 作業 | 実施 |
| --: | ---- | ---- |
| 6 | `crontab -e` で daily / weekly に `--run-meaning` を追加 | **Human のみ** |
| 7 | `crontab -l` で意図どおりか確認 | Human |
| 8 | 初回は翌日 05:00 観測、または Human が手動 smoke（AI は live しない） | Human |

実施後（docs 同期用・AI へ共有してよい情報）:

| No | 共有してよい | 共有禁止 |
| --: | ------------ | -------- |
| 9 | 登録日時（JST）、対象行が daily/weekly か、`--run-meaning` 有無 | secret・`.env`・token・接続文字列 |
| 10 | 初回 Run の成功/失敗（`item_apply` / meaning 段の有無）の要約 | 生の認証情報 |

---

## 6. 登録済み記録（Human 登録後に更新）

| 項目 | 内容 |
| ---- | ---- |
| 状態 | **登録済み** |
| 登録者 | Human（`ryo-chan-k6`） |
| 登録日時（JST） | **2026-08-24 15:06:22 JST**（[#1870 コメント](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1870#issuecomment-5391345229)） |
| 実行パス | `/home/ryo-c/GitHub/GiftRecommendAPP_MVP_CYCLE_3`（`develop` チェックアウト） |
| daily 行 | `--run-meaning` **追加済み**（火〜日 05:00、`--live-rakuten` / `--genre-ids 100005` / `--ranking-genre-ids 100005` / `--pages-per-run=60` / `--max-qps 1` 維持） |
| weekly 行 | `--run-meaning` **追加済み**（月曜 05:00、同上ノブ維持） |
| 備考 | 案B genre・`--live-embedding` 既定 ON は未反映。#1811 は完了扱いにしない。初回観測は次回 05:00 JST 以降 |

---

## 7. ロールバック

問題時は Human が crontab から `--run-meaning` を削除し、Phase1 互換（009〜016 スキップ）に戻す。  
コードの revert は不要（フラグ opt-in）。

---

## 8. 関連

| 資料 | 用途 |
| ---- | ---- |
| [cutover ゲート Decision](../../../ai-logs/human-decisions/2026-08-24-batch-local-cron-phase2-cutover-gate.md) | 明示承認 B |
| [Phase1 crontab運用手順](./local_cron_Phase1_crontab運用手順.md) | Phase1 正本・ノブ |
| [Phase2 dry-run 検証結果](./local_cron_Phase2_dry-run検証結果.md) | 配線検証 |
| Epic #1818 / Phase1 #1811 | 親・並行観測 |

---

## 9. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-24 | 初版。Human 明示承認 B に基づく載せ替え手順・チェックリスト。登録記録は未実施 |
| 2026-08-24 | §6。Human 登録（15:06:22 JST・daily/weekly に `--run-meaning`）を同期 |
