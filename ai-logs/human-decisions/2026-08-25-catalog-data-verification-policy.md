# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-25-catalog-data-verification-policy` |
| Log種別 | `human-decision` |
| 件名 | 蓄積カタログデータ検証の方針（案B・localのみ・第一波合格ライン・本線#7非吸収） |
| 発生日時 | 2026-08-25 |
| 記録日時 | 2026-08-25 |
| 発生元Command | `/work-issue @prompts/definitions/tasks/catalog-data-verification/verification-policy-decision.yaml` |
| 発生元Agent | `worker-ai` |
| workstream_key | `catalog-data-verification` |
| 関連Issue | #1883（本Decision） / #1882（親Epic） / #1745（統括・並行レーン） / #1843（第1波収集） / #1798（本格収集） |
| 前提 | 親Epic #1882。Humanチャット採択 2026-08-25（案B / local DBのみ / 第一波合格ライン） |
| 重要度 | `high` |
| 状態 | **`decided`** |

本Logは、バッチ運用検証と並行して local に蓄積した楽天由来カタログを検証する範囲・合格ライン・本線#7との切り分けを正本化する。
スナップショット実行・reco実行・fetch_plan変更・crontab変更は含めない。
チャット上の同意だけでは正本とせず、本Log（`decided`）と [蓄積カタログデータ検証方針](../../docs/15_運用・改善/運用手順/蓄積カタログデータ検証方針.md) を正本とする。

---

## 2. 結論（Human採択）

| No | 論点 | 決定 |
| --: | ---- | ---- |
| 1 | 検証パッケージ | **案B**（パイプライン整合 + 意味連鎖カバレッジ + 贈答適否の観点定義と少数サンプリング。reco実行なし） |
| 2 | 対象環境 | **local DB のみ**。簡易stg投入（#1795）・production は触らない |
| 3 | 第一波合格ライン | 下表。閾値未設定の項目はスナップショット後に別判断 |
| 4 | 本線#7 | **吸収しない**。stgレコメンド品質評価は未起票のまま別レーン |
| 5 | バッチ運用検証 | **止めない**。cron live と並列してよい。本Epicでは crontab を変更しない |
| 6 | 意味連鎖 | 全件完了を第一波の完了条件にしない。カバレッジと失敗理由の可視化まで |

### 2.1 第一波合格ライン（採択）

| 項目 | 第一波の扱い |
| ---- | ------------ |
| staging にあって item に無い商品コード | **0 を維持** |
| `item_name` / `price` / `item_url` の欠損 | **0** |
| 画像なし item | **件数を監視**。閾値はスナップショット後に決める |
| `external_genre_id` NULL | **件数を監視**。閾値はスナップショット後に決める |
| 意味連鎖（semantic / feature / meaning / embedding） | **カバー率と queue 状態を記録**。全件完了は求めない |
| 贈答適否 | **観点定義 + 少数サンプリング**。最終ラベルは Human。収集方針の変更は本Logではしない |

### 2.2 3層境界（採択）

| 層 | 見るもの | 第一波 |
| --- | --- | --- |
| A. パイプライン整合 | Raw → Staging → Item の漏れ・必須項目・画像・ジャンル・価格外れ値 | **実施**（後続 snapshot Task） |
| B. 意味連鎖カバレッジ | queue / semantic / feature / meaning / embedding の充足 | **観測**（後続 snapshot Task。消化完了は待たない） |
| B+. 贈答適否サンプリング | ジャンル・価格帯の疑いリストと少数例 | **実施**（観点定義は本Log。実サンプリングは後続 Task。reco実行なし） |
| C. 贈答適合・推薦品質 | 理由の妥当性、stg人手評価、reco実行 | **本線#7。対象外** |

### 2.3 対象外の維持

| 項目 | 扱い |
| ---- | ---- |
| stgレコメンド品質評価（#1745 本線#7） | 本Logでは起票しない |
| reco / api / web からの推薦実行 | 禁止 |
| 簡易stgデータ投入（#1795） | 触らない |
| fetch_plan 変更・追加 live 収集 | 本Logではしない |
| AI `--live-rakuten` | 禁止 |
| 定常 crontab（#1811） | 変更しない |
| GHA 楽天 live / #1607 / #1792 | 対象外維持 |
| DB schema / 破壊的更新 | 禁止 |
| secret 実値 | docs / Issue / PR / 本Log に記載しない |

---

## 3. human-decision として記録する理由

検証の「完了」は件数確認ではなく、何を合格とするかの Human 判断である。カタログ検証 Epic は識別子未整備の領域単位例外であり、本線#7との境界を正本化しないと後続 snapshot が進められない。

### 3.1 記録対象理由

- 案A / 案B / 案C の採択は AI だけでは確定できない
- 合格ラインと本線#7非吸収は運用境界であり、チャット同意だけでは正本にならない

### 3.2 通常作業ログではない理由

通常作業ログをすべて `ai-logs/` に保存しない。
本Logは検証範囲・合格ライン・レーン切り分けの Human 採択を残すために記録する。正本は [AIログ運用ルール](../../docs/00_共通/AIエージェント運用/AIログ運用ルール.md) §13 とする。

---

## 4. 発生経緯

| 項目 | 内容 |
| ---- | ---- |
| 発生元 | Human依頼（バッチ運用検証と並行したデータ検証開始） |
| 関連Task | `catalog-data-verification:検証方針Human Decision Log化` |
| 関連Task Definition | `prompts/definitions/tasks/catalog-data-verification/verification-policy-decision.yaml` |
| 関連Command | `/start-epic` → `/start-task` → `/work-issue` |

### 4.1 詳細

local cron が `--live-rakuten --run-meaning` で稼働し、楽天実データが local `item` 正本へ蓄積されている。
第1波収集（#1847）で staging→item 漏れ 0 は記録済みだが、必須項目・画像・ジャンル・価格外れ値・意味カバレッジ・贈答適否は未検証だった。
Orchestrator が3案を提示し、Human が 2026-08-25 に案B・localのみ・第一波合格ラインを採択した。Epic #1882 起票後、本Taskで正本化する。

---

## 5. 判断が必要な事項（採択済み）

- 検証範囲は案A / 案B / 案C のいずれか
- 対象環境は local DB のみでよいか
- 第一波合格ライン案でよいか
- 作業順は Epic Definition → `/start-epic` でよいか

---

## 6. 背景

データ品質要件の正本は [データ管理要件](../../docs/03_ドメイン要件定義/非機能要件定義書/データ管理要件.md) §13（完全性・一貫性・再現性・比較可能性・鮮度）である。
バッチが「動いた」ことと、アプリデータとして「使える」ことは別である。
#1745 本線#7 は stgレコメンド品質評価であり、カタログ健全性の前提確認とは別物とする。

---

## 7. 選択肢

| 案 | 内容 | メリット | デメリット |
| --- | ---- | -------- | ---------- |
| A | パイプライン整合＋意味カバレッジのみ。贈答適否・レコメンド品質は本線#7 | すぐ始められる。運用検証と衝突しにくい | 「ギフトとして使えるか」は後回し |
| B | A に加え、ジャンル／価格帯の贈答適否をサンプリング（reco実行なし） | 収集の歪みを早く見つけられる | 適否の最終ラベルは Human が必要 |
| C | 今から stg レコメンド品質評価（本線#7）まで含める | 一気に品質まで見られる | 意味データが少ないと母集団不足。運用検証と混線 |

---

## 8. AIの推奨

案B。第一波は整合とカバレッジを測り、贈答適否は観点と少数サンプルに留める。reco実行と本線#7起票はしない。

---

## 9. 人間に決めてほしいこと

上記4点。2026-08-25 チャットで採択済み。本Logは再採択ではなく正本化である。

---

## 10. 判断後に必要な対応

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| 本Log | Human採択を `decided` として記録 | **本更新** |
| 検証方針docs | 本Logと同期した運用手順を新規作成 | 本PRで実施 |
| 後続 Task | `local-catalog-snapshot` | 本Log `decided` **かつ** Task #1883 の Human Review / merge（Projects Done）後に `/start-task` |
| #1745 | 並行レーン追跡（本線#7非吸収） | Epic起票時にコメント済み。本Logでも維持 |
| fetch_plan / crontab / 本線#7 | 本Logでは変更・起票しない | 対象外 |

---

## 11. 確認した事実

- 親Epic #1882 / Branch `chore/epic-1882-catalog-data-verification` が存在する
- 第1波収集結果（#1847）で staging→item 漏れ 0、genre cursor はスコープ10ID exhausted
- #1745 本線#7 `batch-stg-reco-quality` は未起票
- #1795 は簡易stg §6.11 データ投入であり、local蓄積データの検証ではない
- local cron は `--live-rakuten --run-meaning` 付きで稼働中（本Epicでは変更しない）

---

## 12. 推論

- 意味連鎖がカタログ全体に対して少数でも、第一波はカバー率の可視化で足りる
- 贈答不適ジャンルの混入は収集方針見直し材料になり得るが、本Logでは fetch_plan を変えない
- 画像なし・ジャンルなしの閾値は実測後に決めないと、根拠のない合格/不合格になる

---

## 13. 関連情報

| 種別 | 参照 |
| ---- | ---- |
| 関連docs | [蓄積カタログデータ検証方針](../../docs/15_運用・改善/運用手順/蓄積カタログデータ検証方針.md) / [データ管理要件](../../docs/03_ドメイン要件定義/非機能要件定義書/データ管理要件.md) / [第1波収集結果](../../docs/15_運用・改善/運用手順/fetch_plan拡大_第1波_段階収集結果_1847.md) / [楽天Fetch運用方針](../../docs/15_運用・改善/運用手順/楽天Fetch運用方針.md) |
| 関連Issue | #1883 / #1882 / #1745 / #1843 / #1798 / #1811 / #1795 |
| 関連Branch | `chore/task-1883-verification-policy-decision`（base: `chore/epic-1882-catalog-data-verification`） |
| Definition | `prompts/definitions/tasks/catalog-data-verification/verification-policy-decision.yaml` |

---

## 14. 人間判断結果（記録時）

| 項目 | 内容 |
| ---- | ---- |
| 判断者 | Human（チャット指示 2026-08-25） |
| 判断日時 | 2026-08-25 |
| 採用案 | **案B** |
| 判断理由 | 運用検証と並列でき、収集の歪みも早く見える。意味データ不足のまま本線#7へ進まない |
| 後続Issue | 親Epic #1882。snapshot は本Log `decided` 後に `/start-task` |
| 後続Task | `local-catalog-snapshot` |
| 本Log状態 | **`decided`** |

Human Review では、正本化した文面がチャット採択と一致しているかを確認する。
