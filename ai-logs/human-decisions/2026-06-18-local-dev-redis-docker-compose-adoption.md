# Human Decision Log

## 1. 概要

| 項目          | 内容                  |
| ------------- | --------------------- |
| Log ID        | `2026-06-18-local-dev-redis-docker-compose-adoption` |
| Log種別       | `human-decision`      |
| 件名          | Phase3b Task A5: Redis 限定 docker-compose 同梱を採用する（DB は Supabase CLI 維持） |
| 発生日時      | 2026-06-18            |
| 記録日時      | 2026-06-18            |
| 発生元Command | Phase3 環境再計画（plan） |
| 発生元Agent   | `orchestrator-ai`     |
| workstream_key | `local-dev-environment` |
| 関連Issue     | （Epic A 未起票）     |
| 関連PR        | （未作成）            |
| Definition    | Task A5 `redis-local-guide`（作成予定） |
| 重要度        | `medium`              |
| 状態          | `resolved`            |

---

## 2. 結論

**Redis 限定 docker-compose を Task A5 で採用する。** リポジトリ同梱の `docker-compose.dev.yml` に Redis サービスのみを定義し、`scripts/dev/` から起動補助する。

**DB（PostgreSQL）は Supabase CLI + Docker Desktop を正本のまま維持する。** Postgres を compose で二重管理しない。Neon は不採用。

---

## 3. human-decision として記録する理由

2026-06-07 の Human 判断（docker-compose 同梱なし）が Phase3a Task ③④ の正本として残存しており、Phase3b Epic A Task A5 着手前に Redis  compose の採否を確定する必要があるため。

### 3.1 記録対象理由

- 2026-06-07 判断の Redis 部分を Phase3b で方針変更する
- Task A5（`redis-local-guide`）の scope・out_of_scope を確定づける
- ローカル開発手順書 §3.2 / §7 の更新方針に影響する

### 3.2 通常作業ログではない理由

設計方針の選択であり、複数 docs・scripts・Task Definition に横断影響するため。正本は [AIログ運用ルール](../../docs/00_共通/AIエージェント運用/AIログ運用ルール.md) §13 とする。

---

## 4. 発生経緯

| 項目                  | 内容                                   |
| --------------------- | -------------------------------------- |
| 発生元                | `planning`（Phase3 環境再計画）        |
| 関連Task              | Epic A Task A5 `redis-local-guide`     |
| 関連Task Definition   | （A5 作成予定）                        |
| 関連Command           | `/start-epic` / `/start-task`（予定）  |

### 4.1 詳細

Phase3a（Epic #436 merge 済み）では Human 判断（2026-06-07）により docker-compose 同梱なし・DB/Redis 手動起動とした。Phase3b 再計画では、当時の意図が「Postgres を compose で Supabase CLI と二重管理しないこと」が主だったと整理し、Redis のみ compose 同梱する案を推奨した。Task A5 着手前に最終判断が必要だった。

---

## 5. 判断が必要な事項

- Task A5 で Redis 用 `docker-compose.dev.yml` をリポジトリ同梱するか
- DB 正本を Supabase CLI のまま維持するか（Postgres + Redis フル compose は採用しないか）

---

## 6. 背景

| 観点 | 現状（Phase3a 正本） | Phase3b 再計画 |
| ---- | -------------------- | -------------- |
| ローカル DB | Neon 記載あり / 手動 Postgres | **Supabase CLI + Docker Desktop**（マイグレーション方針書 §9、#591 merge 済み） |
| Redis | 手動 `docker run` 想定 | compose 同梱で起動簡素化を検討 |
| docker-compose | **同梱しない**（2026-06-07） | Redis のみ同梱を推奨 |

参照正本:

- [ローカル開発手順書 §3.2](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md)
- [マイグレーション方針書 §9.0](../../docs/06_実装設計/database/マイグレーション方針書.md)
- Phase3a Task Definition（`infra-scripts.yaml` / `local-dev-guide.yaml`）の 2026-06-07 記載

---

## 7. 選択肢

| 案  | 内容 | メリット | デメリット |
| --- | ---- | -------- | ---------- |
| A   | **現状維持**（Supabase CLI + Redis 手動 `docker run`） | Supabase 公式フローと完全一致 | Redis 起動が毎回手作業、手順が分散 |
| B   | **Redis 限定 compose**（`docker-compose.dev.yml` に Redis のみ） | `docker compose up -d redis` で一発起動、DB は Supabase CLI と役割分離 | compose ファイル追加・docs 更新が必要 |
| C   | **Postgres + Redis フル compose** | 単一 compose で DB/Cache 起動 | Supabase CLI の Storage/pgvector/migration 連携を失う、migration 正本と競合 |

---

## 8. AIの推奨

**案B（Redis 限定 compose）を採用。** DB は案Bの前提どおり Supabase CLI を維持し、案Cは不採用。

---

## 9. 人間に決めてほしいこと

Task A5 で Redis 限定 `docker-compose.dev.yml` を同梱し、DB は Supabase CLI 維持とする方針で確定してよいか。

---

## 10. 判断後に必要な対応

- Task A5 Definition（`redis-local-guide`）を作成し、本判断を `background` / `scope` に反映する
- Task A5 実装: `docker-compose.dev.yml`（Redis のみ）、`scripts/dev/start-redis.sh` 等、ローカル開発手順書 §3.2 / §7 更新
- Phase3a 正本（ローカル開発手順書 §3.2、scripts/dev/README.md 等）の 2026-06-07 記載は **Task A5 実装時** に更新する（本判断ログでは方針確定のみ）
- Postgres + Redis フル compose は out_of_scope として明示する

---

## 11. 確認した事実

- Phase3a Epic #436 / PR #584 は 2026-06-18 merge 済み
- マイグレーション方針書は Supabase CLI 確定（Human Review 2026-06-16、#591）
- `.env.example` の `REDIS_URL` デフォルトは `redis://localhost:6379/0`
- 2026-06-07 Human 判断は「docker-compose 同梱なし」を Phase3a Task ③④ に反映済み
- マイグレーション方針書 §9.0 は local 環境で `supabase start` + Redis（Docker）を記載済み

---

## 12. 推論

- 2026-06-07 判断の主目的は Postgres の compose 二重管理回避と解釈できる
- Redis のみ compose 化しても Supabase CLI 正本と競合しない
- Task A6/A7 の Redis 疎通確認を `docker compose up -d redis` で標準化できる

---

## 13. 関連情報

| 種別           | 参照                |
| -------------- | ------------------- |
| 関連docs       | `docs/00_共通/プロジェクト管理/実装フェーズ実行プロセス設計書.md` §8 |
| 関連docs       | `docs/06_実装設計/cross_cutting/ローカル開発手順書.md` |
| 関連docs       | `docs/06_実装設計/database/マイグレーション方針書.md` §9 |
| 関連Issue      | Epic A 未起票（#132 supersede 予定） |
| 関連PR         | （未作成）          |

---

## 14. 人間判断結果（記録時）

| 項目       | 内容                 |
| ---------- | -------------------- |
| 判断者     | ryo-chan-k6          |
| 判断日時   | 2026-06-18           |
| 採用案     | **案B**（Redis 限定 compose 採用）。DB は Supabase CLI + Docker Desktop 維持。案C 不採用 |
| 判断理由   | Redis 起動の標準化と Supabase CLI 正本の両立。Postgres compose 二重管理を避ける |
| 後続Task   | Epic A Task A5 `redis-local-guide` |
| supersede | 2026-06-07 判断の **Redis / docker-compose 部分**（DB 手動起動・Neon 記載は別 Task A3/A6 で Supabase CLI へ更新済み/予定） |
