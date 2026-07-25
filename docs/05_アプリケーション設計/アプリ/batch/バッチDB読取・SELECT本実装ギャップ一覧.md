# バッチDB読取・SELECT本実装ギャップ一覧

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | DB SELECT / 読取棚卸し正本（docs） |
| 対象 | BATCH-001〜017 中心のビジネスデータ SELECT・seed・claim（018/019 除外） |
| 作成日 | 2026-07-25 |
| 更新日 | 2026-07-25 |
| 関連 Epic | [#1623](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1623)（batch-db-select） |
| 関連 Task | [#1624](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1624)（T0） / [#1627](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1627)（T1） / [#1629](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1629)（Wave A: 005 SELECT） |
| 先行 | E2 [#1595](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1595) / E3 [#1598](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1598) MERGED |
| tip 根拠 | Epic tip（実 DB 疎通必須方針反映時点） |

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
| DB 読取 | **T1: `DbReader` 境界あり**。**Wave A: BATCH-005 は `list_eligible_raws` 本配線済み**。004/006 以降は未（in-memory + `seed_*`） |
| 外部 I/O | E3 完了（楽天 / Embedding / Object Storage。明示 live のみ） |
| 主ブロッカー | 005 以外のビジネスデータ SELECT 未配線 → 非 demo で多数が **exit 3** |
| Soft gap | 004（live 時）/ 006 は seed 空で **exit 0 可**（本線未開放） |

---

## 3. 重点 Batch（事実）

| Batch ID | 現状の事実 | 非 demo 挙動 | E3 で揃ったもの | 足りない読取 |
| -------- | ---------- | ------------ | --------------- | ------------ |
| **005** raw_staging | **Wave A: DbReader SELECT + Job 起動**（`DATABASE_URL` 必須。Storage は明示 live） | `DATABASE_URL` 無し → **exit 2**。有り → Job 実行 | Object Storage client | （本配線済み。staging 本番 UPSERT 詳細は別） |
| **004** item_recheck | 楽天 + Storage live 可。`seed_items` 未注入 | live 無し → exit 3（楽天フラグ）。live 有り → **0 件成功可** | 楽天 / Storage | `item` seed SELECT |
| **010** item_semantic | Rule-first adapter（LLM 非呼出） | **exit 3** | （外部 API 対象外） | queue / item SELECT |
| **015** item_embedding | `--scaffold-demo --live-embedding` で HTTP 煙可 | **exit 3** | Embedding client | queue / handoff SELECT |

### 3.1 根拠パス（事実）

| Batch | CLI | 根拠メッセージ / コメント |
| ----- | --- | ------------------------- |
| 005 | `apps/batch/src/batch/application/raw_staging/__main__.py` | `resolve_job_db_reader` + Job。`DATABASE_URL` 無しは exit 2 |
| 004 | `.../item_recheck/__main__.py` | `seed 空: 実 DB SELECT は未実装` |
| 010 | `.../item_semantic/__main__.py` | `real DB read path is not enabled yet` |
| 015 | `.../item_embedding/__main__.py` | 同上 |
| 006 | `.../product_diff/__main__.py` | `読取 SELECT は未実装のため seed 空で実行` |
| DB | `apps/batch/src/batch/infrastructure/db/reader.py` / `writer.py` | `DbReader` + `DbWriter` |

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
| **005** | Storage live | **metadata SELECT 本配線済み**（#1629）。staging UPSERT 本格化は別 |
| **015** | Embedding HTTP（demo 煙） | **queue/handoff SELECT** + 本番 CLI live |
| **010** | （外部対象外）Rule-first | **DB SELECT**（LLM 不要） |

**推論:** 「取って Storage に置く」側は進んだが、「DB から読んで次工程へ進める」側が未開放。

---

## 7. 推奨 Wave / Issue 化候補（推論）

Epic #1623 の子 Task 分割案。

| 優先 | Wave | 候補 Task | 内容 | 実 DB 疎通 | 依存 |
| ---- | ---- | --------- | ---- | ---------- | ---- |
| high | T0 | inventory（**#1624** MERGED） | 本正本 | **不要**（docs のみ） | — |
| high | T1 | reader-foundation（**#1627**） | `DbReader` Protocol / Scaffold / Postgres factory | **必須** | T0 |
| high | A | BATCH-005 SELECT（**#1629**） | `raw_product_metadata` + Storage GET 本実行 | **必須** | T1 |
| high | A' | BATCH-004 seed SELECT | `item` seed | **必須** | T1（A と並列可） |
| high | B | BATCH-006 SELECT | staging/item | **必須** | A |
| medium | C | 007 / 008 / 009 SELECT | 必要時は書込充実を分離 | **必須** | B |
| high | D | BATCH-010 SELECT | queue/item（Rule-first） | **必須** | C（009 後） |
| medium | E | 011〜014 SELECT | 連鎖 | **必須** | D |
| high | F | BATCH-015 SELECT | + 本番 CLI `--live-embedding` | **必須** | E |
| low | G | 016 / 017 SELECT | 監視・集計 | **必須** | F 後で可 |

### 7.1 実 DB 疎通確認ポリシー（Human 確定・事実）

Epic #1623（2026-07-25 Human 確定）: **実装 Wave（T0 以外）の子 Task は実 DB 疎通確認を完了条件に含む。**

| 項目 | 方針 |
| ---- | ---- |
| 対象 Wave | T1 および A 以降の実装 Task（T0 inventory は除外） |
| 環境 | **local / dev / staging** の Postgres（`DATABASE_URL` が `scaffold://` 以外） |
| 合格条件 | 対象 Wave の読取（`DbReader.fetch_rows` または Batch SELECT 経路）が **接続・クエリ実行に成功**すること。対象 0 件でも接続成功なら可 |
| 記録 | PR 本文（または `ai-logs/experiments/`）に手順・結果要約。**secret / URL 実値は書かない** |
| CI | **既定 off**（明示フラグ / 手動実行のみ） |
| 禁止 | production 無承認 live、CI 既定 live、接続実値の commit |

**追記（事実）:** T1（#1627）は方針確定前に UT 中心で MERGED。方針確定後は **follow-up 疎通**または Epic 完了前の補完を要する。Wave A（#1629）以降は Task Definition に必須として記載する。

---

## 8. out of scope / 今やらなくてよいもの（事実）

| 対象 | 理由 |
| ---- | ---- |
| #1607 本番 egress | E3 Backlog。Human: 現時点検討しない |
| Semantic LLM | E3 Human 確定「含めない」 |
| BATCH-018 / 019 | E3 除外・後回し |
| E4 観測横断 | 別 Epic |
| CI 既定 live | E3 / 本 Epic 方針: 既定 off（手動の実 DB 疎通とは別） |
| production 無承認 live | 本 Epic 禁止。疎通は local/dev/staging のみ |

---

## 9. 事実 / 推論 / 未確認

| 区分 | 内容 |
| ---- | ---- |
| **事実** | E2/E3 MERGED。T1 で `DbReader` 導入。実装 Wave の実 DB 疎通は Human 確定で必須（T0 除く） |
| **推論** | 次の最大ブロッカーは SELECT 本配線 + 疎通証拠（特に 005→パイプライン、004 seed、010/015） |
| **未確認** | 各環境のシードデータ有無、各 IF の列単位 SELECT 詳細、親 workflow dry-run |

---

## 10. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-25 | 初版（#1624 / Epic #1623） |
| 2026-07-25 | Human 確定: 実装 Wave の実 DB 疎通確認を必須化（§7.1） |
