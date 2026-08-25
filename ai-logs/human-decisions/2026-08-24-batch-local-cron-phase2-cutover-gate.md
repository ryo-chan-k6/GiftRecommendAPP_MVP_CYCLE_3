# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-24-batch-local-cron-phase2-cutover-gate` |
| Log種別 | `human-decision` |
| 件名 | Phase2 cron-cutover 着手ゲート: Human 明示承認（選択肢 B） |
| 発生日時 | 2026-08-24 |
| 記録日時 | 2026-08-24 |
| 発生元 | Human チャット指示（#1818 次アクション提案への回答） |
| 関連Issue | #1870（本 Task） / #1818（親Epic） / #1811（Phase1・完了扱いにしない） / #1824（dry-run完了） |
| 前提決定 | `2026-08-01-batch-local-cron-ops-next` / Phase2 dry-run 検証結果（#1824） |
| 重要度 | `high` |
| 状態 | **`decided`** |

---

## 2. 結論（Human採択）

| No | 論点 | 決定 |
| --: | ---- | ---- |
| 1 | cutover 着手ゲート | **選択肢 B: Human 明示承認**により、Phase1 観測完了（#1811 verify）を待たず **cron-cutover を先行**する |
| 2 | Phase1 #1811 | **完了扱いにしない**。観測・`item_apply` 再確認は継続。本 Decision は cutover 着手のみを許可する |
| 3 | 載せ替え内容（方針） | 既存 Phase1 cron 行へ **`--run-meaning` を追加**する。親シェル経由のみ・個別 cron 禁止を維持 |
| 4 | 変更しないもの | 案B `--genre-ids` の定常反映、`--live-embedding` の既定ON、GHA schedule / #1607、AI による crontab 編集・`--live-rakuten` |
| 5 | 実施分担 | **crontab 実編集は Human**。AI は手順正本・チェックリスト・登録済み記録の docs 同期のみ |

### 2.1 想定 crontab 差分（方針・実値は Human 登録時に確定）

```text
# 変更前（Phase1）
... local_daily_orchestrator.sh --live-rakuten --genre-ids 100005 --ranking-genre-ids 100005 ...

# 変更後（Phase2 opt-in）
... local_daily_orchestrator.sh --live-rakuten --run-meaning --genre-ids 100005 --ranking-genre-ids 100005 ...
```

weekly 行も同様に `--run-meaning` を追加する（詳細は載せ替え手順 docs）。

---

## 3. 境界

- AI は `crontab -e` / 実ファイル編集を行わない
- AI は `--live-rakuten` を実行しない
- `#1811` を Done / CLOSED にしない
- secret 実値を docs / Issue / PR に書かない

---

## 4. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| 本Log | 明示承認（B）を `decided` で記録 | **本更新** |
| cron-cutover Task | Issue 起票・手順 docs・Human チェックリスト | 着手 |
| Human | 実 crontab へ `--run-meaning` 追加 | **完了**（2026-08-24 15:06:22 JST・#1870） |
| AI | 登録済み記録の docs 同期（Human 登録後） | 着手（載せ替え手順 §6） |
| #1811 | Phase1 観測継続（本 Decision で完了にしない） | 継続 |

---

## 5. 参照

- `prompts/definitions/tasks/batch-local-cron-phase2/cron-cutover.yaml`
- `docs/15_運用・改善/運用手順/local_cron_Phase2_dry-run検証結果.md`
- `docs/15_運用・改善/運用手順/local_cron_Phase1_crontab運用手順.md`
- Issue #1818 / #1811 / #1824
