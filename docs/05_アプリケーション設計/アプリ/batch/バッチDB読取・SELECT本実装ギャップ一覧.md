# バッチDB読取・SELECT本実装ギャップ一覧

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | DB SELECT / 読取棚卸し正本（docs） |
| 対象 | BATCH-001〜017 中心のビジネスデータ SELECT・seed・claim（018/019 除外） |
| 作成日 | 2026-07-25 |
| 更新日 | 2026-07-25 |
| 関連 Epic | [#1623](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1623)（batch-db-select） |
| 関連 Task | [#1624](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1624)（T0 棚卸し） / [#1627](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1627)（T1 DbReader 基盤） |
| 先行 | E2 [#1595](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1595) / E3 [#1598](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1598) MERGED |
| tip 根拠 | Epic tip（T1 実装時点） |

### 1.1 目的

実 DB SELECT 未配線・CLI exit 3・seed 空実行の現状を突合し、Epic #1623 配下 Task 分割の Human 判断材料を正本化する。

### 1.2 本ドキュメントでやらないこと

| out of scope | 理由 |
| ------------ | ---- |
| 各 Batch の SELECT 本配線・exit 3 解除 | Wave A 以降（T1 は読取境界のみ） |
| E4 観測横断実装 | 別 Epic |
| Semantic LLM 本接続 | Human 確定どおり Rule-first 維持 |
| #1607 本番 egress | Backlog |
| BATCH-018 / 019 本格化 | E3 除外・後回し |

---

## 2. 30秒サマリ（事実）

| 項目 | 状態 |
| ---- | ---- |
| DB 書込 | `DbWriter` + 代表 UPSERT（E2）。`apps/batch/.../infrastructure/db/writer.py` |
| DB 読取 | **T1: `DbReader` 境界あり**（`reader.py` / factory）。各 Batch repositories の SELECT 本配線は未（in-memory + `seed_*`） |
| 外部 I/O | E3 完了（楽天 / Embedding / Object Storage。明示 live のみ） |
| 主ブロッカー | ビジネスデータ SELECT 未配線 → 非 demo で多数が **exit 3** |
| Soft gap | 004（live 時）/ 006 は seed 空で **exit 0 可**（本線未開放） |

---

## 3. 重点 Batch（事実）

| Batch ID | 現状の事実 | 非 demo 挙動 | E3 で揃ったもの | 足りない読取 |
| -------- | ---------- | ------------ | --------------- | ------------ |
| **005** raw_staging | Storage live まで到達可。直後に読取未配線 | **exit 3** | Object Storage client | `raw_product_metadata` SELECT → Storage GET |
| **004** item_recheck | 楽天 + Storage live 可。`seed_items` 未注入 | live 無し → exit 3（楽天フラグ）。live 有り → **0 件成功可** | 楽天 / Storage | `item` seed SELECT |
| **010** item_semantic | Rule-first adapter（LLM 非呼出） | **exit 3** | （外部 API 対象外） | queue / item SELECT |
| **015** item_embedding | `--scaffold-demo --live-embedding` で HTTP 煙可 | **exit 3** | Embedding client | queue / handoff SELECT |

### 3.1 根拠パス（事実）

| Batch | CLI | 根拠メッセージ / コメント |
| ----- | --- | ------------------------- |
| 005 | `apps/batch/src/batch/application/raw_staging/__main__.py` | `real DB read path is not enabled yet` |
| 004 | `.../item_recheck/__main__.py` | `seed 空: 実 DB SELECT は未実装` |
| 010 | `.../item_semantic/__main__.py` | `real DB read path is not enabled yet` |
| 015 | `.../item_embedding/__main__.py` | 同上 |
| 006 | `.../product_diff/__main__.py` | `読取 SELECT は未実装のため seed 空で実行` |
| DB | `apps/batch/src/batch/infrastructure/db/writer.py` | `DbWriter` のみ（Reader なし） |

---

## 4. 同パターン一覧（事実）

メッセージ共通: `DbWriter backend=... is resolved, but real DB read path is not enabled yet.`

| Batch | 主な未配線読取（推論: repositories の load/list が in-memory） |
| ----- | -------------------------------------------------------------- |
| 007 item_apply | diff / staging |
| 008 item_active_status | candidate / diff / item |
| 009 item_generation_queue | diff / item |
| 011 feature_input_hash | queue / item / semantic |
| 012 item_feature | queue / semantic / hash handoff |
| 013 feature_normalization | queue / raw features |
| 014 embedding_input_hash | queue / item |
| 016 distribution_metrics | feature / meaning / embedding |
| 017 import_summary | 集計入力 |

### 4.1 exit 3 だが DB 読取ではないもの（事実）

| Batch | 理由 |
| ----- | ---- |
| 001〜004 | `--live-rakuten` / `BATCH_RAKUTEN_LIVE` 未指定（既定 off） |
| 018 / 019 | Real DB client off（本線後回し） |

---

## 5. E2 / E3 / E4 との切り分け

| 区分 | スコープ | 本一覧での扱い |
| ---- | -------- | -------------- |
| **E2** | IF-DB stub 解除・`DbWriter` / 代表 UPSERT | 完了前提。読取は「後続」と E2 正本に明記 |
| **E3** | 外部 API client | 完了。SELECT は対象外だった |
| **本 Epic #1623** | ビジネスデータ SELECT / seed / claim | **本線** |
| **E4** | `batch_run_log` / phase / error / import_summary の横断揃え | **混ぜない**（別 Epic） |

出典: [バッチIF-DB・DDL本実装ギャップ一覧](./バッチIF-DB・DDL本実装ギャップ一覧.md) / [バッチ外部API本実装ギャップ一覧](./バッチ外部API本実装ギャップ一覧.md) / [バッチ横串整合・本実装ギャップ一覧](./バッチ横串整合・本実装ギャップ一覧.md) §10

---

## 6. 「外部APIは来たが後続が足りない」（事実 + 推論）

| Batch | E3 で揃ったもの（事実） | 足りない後続 |
| ----- | ----------------------- | ------------ |
| 001〜003 | 楽天 + Storage live | （推論）主ブロッカーは SELECT ではない |
| **004** | 楽天 + Storage | **item seed SELECT** |
| **005** | Storage live | **metadata SELECT**（exit 3） |
| **015** | Embedding HTTP（demo 煙） | **queue/handoff SELECT** + 本番 CLI live |
| **010** | （外部対象外）Rule-first | **DB SELECT**（LLM 不要） |

**推論:** 「取って Storage に置く」側は進んだが、「DB から読んで次工程へ進める」側が未開放。

---

## 7. 推奨 Wave / Issue 化候補（推論）

Epic #1623 の子 Task 分割案。

| 優先 | Wave | 候補 Task | 内容 | 依存 |
| ---- | ---- | --------- | ---- | ---- |
| high | T0 | inventory（**#1624** MERGED） | 本正本 | — |
| high | T1 | reader-foundation（**#1627**） | `DbReader` Protocol / Scaffold / Postgres factory | T0 |
| high | A | BATCH-005 SELECT | `raw_product_metadata` + Storage GET 本実行 | T1 |
| high | A' | BATCH-004 seed SELECT | `item` seed | T1（A と並列可） |
| high | B | BATCH-006 SELECT | staging/item | A |
| medium | C | 007 / 008 / 009 SELECT | 必要時は書込充実を分離 | B |
| high | D | BATCH-010 SELECT | queue/item（Rule-first） | C（009 後） |
| medium | E | 011〜014 SELECT | 連鎖 | D |
| high | F | BATCH-015 SELECT | + 本番 CLI `--live-embedding` | E |
| low | G | 016 / 017 SELECT | 監視・集計 | F 後で可 |

---

## 8. out of scope / 今やらなくてよいもの（事実）

| 対象 | 理由 |
| ---- | ---- |
| #1607 本番 egress | E3 Backlog。Human: 現時点検討しない |
| Semantic LLM | E3 Human 確定「含めない」 |
| BATCH-018 / 019 | E3 除外・後回し |
| E4 観測横断 | 別 Epic |
| CI 既定 live | E3 方針: 既定 off |

---

## 9. 事実 / 推論 / 未確認

| 区分 | 内容 |
| ---- | ---- |
| **事実** | E2/E3 MERGED。`DbWriter` のみ。005/010/015 等は非 demo で読取メッセージ + exit 3。004/006 は空 seed で実行可。010 は Rule-first |
| **推論** | 次の最大ブロッカーは SELECT Epic（特に 005→パイプライン、004 seed、010/015）。E4 や LLM を先にやっても本線は開かない |
| **未確認** | production 実データ有無、各 IF の列単位 SELECT 詳細、親 workflow dry-run |

---

## 10. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-25 | 初版（#1624 / Epic #1623） |
