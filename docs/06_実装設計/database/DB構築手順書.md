# DB構築手順書

## 1. 目的・スコープ

| 項目 | 内容 |
| ---- | ---- |
| 目的 | 開発者が **Supabase CLI + Docker Desktop** でローカル PostgreSQL を起動し、`supabase/migrations/` を適用できる手順を正本化する |
| 対象 OS | **Windows 11 + WSL2**（Ubuntu 等。worktree は Linux 側パス推奨） |
| ローカル DB 方針 | **Supabase CLI ローカルスタック**（Neon 等クラウド dev をローカル DB 正本としない） |
| Agent 運用 | Cloud Agent 上での `supabase start` 成功は **必須条件にしない**（Human 手元確認または optional） |

### 1.1 含めるもの

- Docker Desktop（WSL2 バックエンド）の前提
- Supabase CLI **バージョン pin**（`supabase/.cli-version`）
- `supabase start` → `supabase migration up` → master seed 投入までの手順
- `DATABASE_URL` 設定の目安（`.env` は Git 管理しない）
- [`scripts/db/`](../../../scripts/db/README.md) 補助 script

### 1.2 含めないもの（out_of_scope）

| 対象 | 正本 / 担当 |
| ---- | ----------- |
| `supabase/migrations/**` の DDL 内容変更 | Phase2 Epic |
| test seed（`supabase/seeds/test-data/`）の詳細 | Epic C C2 |
| Redis 起動 | Task A5 `redis-local-guide` |
| クラウド Supabase への link / `db push` | `infra/supabase/`（将来 Task） |
| apps 実装 | Phase4 |

---

## 2. 正本関係

| 情報 | 正本 | 本書の役割 |
| ---- | ---- | ---------- |
| migration ツール・適用正本 | [マイグレーション方針書](./マイグレーション方針書.md) | 手順の具体化 |
| Supabase 配置・クイックスタート | [`supabase/README.md`](../../../supabase/README.md) | CLI 配置の索引 |
| ローカルポート・DB バージョン | [`supabase/config.toml`](../../../supabase/config.toml) | 接続先の根拠 |
| Phase2 DDL スモーク（`db/ddl/` 直接適用） | [ローカルDB検証手順書](./ローカルDB検証手順書.md) | 別用途（migration 統合前の検証） |
| ローカル開発全体 | [ローカル開発手順書](../cross_cutting/ローカル開発手順書.md) §7 | PostgreSQL 節は本書へリンク |
| master seed SQL | [`supabase/seeds/masters/`](../../../supabase/seeds/masters/) + [`config.toml`](../../../supabase/config.toml) `[db.seed]` | 本書 §9 |
| 環境変数 | [環境設計書 §19](../cross_cutting/環境設計書.md) | `DATABASE_URL` 等 |

---

## 3. 前提（WSL2 + Docker Desktop）

### 3.1 リポジトリ配置

- worktree は **WSL の Linux ファイルシステム**（例: `/home/<user>/GitHub/...`）に置く（[worktree運用ルール](../../00_共通/AIエージェント運用/worktree運用ルール.md)）
- 作業前に確認する:

```bash
pwd
git branch --show-current
git status --short
git worktree list
```

### 3.2 Docker Desktop（Windows ホスト）

> **Human 作業**: GUI インストール・再起動が必要なため、Agent では実施しない。

1. [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) をインストールする
2. インストール時に **WSL2 バックエンド**を有効にする
3. Docker Desktop → **Settings → Resources → WSL Integration** → 利用中の Ubuntu ディストリビューションを **ON**
4. PowerShell で WSL を再起動する:

```powershell
wsl --shutdown
```

5. WSL を再度起動し、以下で確認する:

```bash
docker version
docker ps
```

**期待**: Client / Server ともにエラーなく表示され、`docker ps` が空リストまたはコンテナ一覧を返す。

### 3.3 Supabase ローカル設定（正本）

| 項目 | 値 | 根拠 |
| ---- | --- | ---- |
| DB port | `54322` | `supabase/config.toml` `[db] port` |
| PostgreSQL | 15 | `supabase/config.toml` `[db] major_version` |
| 既定 DB 名 | `postgres` | Supabase CLI ローカル既定 |
| migration 正本 | `supabase/migrations/` | [マイグレーション方針書](./マイグレーション方針書.md) §5.1 |

---

## 4. ツールチェーン

### 4.1 Supabase CLI バージョン pin

| 項目 | 内容 |
| ---- | ---- |
| 正本ファイル | [`supabase/.cli-version`](../../../supabase/.cli-version) |
| 形式 | セマンティックバージョン 1 行（例: `2.105.0`） |
| 確認 script | `./scripts/db/check-cli-version.sh` |

pin ファイルと異なる CLI を使うと、migration 挙動差分や CI 不整合の原因になる。アップデート時は **pin ファイル・本書・PR** をセットで更新する。

### 4.2 その他

| ツール | 用途 | インストール目安 |
| ------ | ---- | ---------------- |
| `psql` | 接続確認・手動 SQL | WSL: `sudo apt install -y postgresql-client` |
| Docker CLI | Supabase ローカルスタック | Docker Desktop 同梱 |

---

## 5. Supabase CLI のインストール

[Supabase CLI 公式手順](https://supabase.com/docs/guides/cli/getting-started) に従う。WSL では **Linux amd64 バイナリ**を `PATH` の通ったディレクトリに配置することを推奨する。

```bash
# 例: バージョン確認（pin と一致すること）
supabase --version

# repo 正本 pin との一致確認
./scripts/db/check-cli-version.sh
```

**期待**: `supabase --version` の表示が `supabase/.cli-version` と一致する。

`npx supabase` は一時利用のみとし、日常開発では pin 済みバイナリを使う。

---

## 6. ローカル DB 起動（`supabase start`）

リポジトリ worktree ルートで実行する。

```bash
cd <worktree-root>

./scripts/db/check-cli-version.sh
./scripts/db/start-local.sh
# または: supabase start
```

初回は Docker イメージのダウンロードで **数分**かかる場合がある。

起動後、状態を確認する:

```bash
./scripts/db/status.sh
# または: supabase status
```

**期待**: DB / Studio / API 等のローカルサービスが running と表示される。

停止する場合:

```bash
./scripts/db/stop-local.sh
# または: supabase stop
```

---

## 7. migration 適用（`supabase migration up`）

適用正本は **`supabase/migrations/`** のみとする（[マイグレーション方針書](./マイグレーション方針書.md) §5.1）。

```bash
cd <worktree-root>

# ローカルスタックが起動していること
./scripts/db/status.sh

./scripts/db/migrate-up.sh
# または: supabase migration up
```

**期待**: 未適用 migration が順次適用され、エラーなく完了する。

再検証で DB をクリーンにしたい場合（migration + master seed まで一発）:

```bash
./scripts/db/reset-local.sh
# または: supabase db reset
```

`db reset` は [`config.toml`](../../../supabase/config.toml) `[db.seed]` に従い `supabase/seeds/masters/*.sql` を自動投入する。

> **注意**: `supabase db reset` はローカル DB データを破棄する。prod / クラウドには実行しない。

---

## 8. 接続確認と `DATABASE_URL`

### 8.1 接続確認

`supabase status` の **DB URL** を使用する。ローカル既定の形式（Supabase CLI ローカル開発用の既知資格情報）:

```text
postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

```bash
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -c "SELECT version();"
```

**期待**: PostgreSQL 15.x のバージョン文字列が返る。

> **Secret 管理**: 上記はローカル CLI 既定値である。本番・クラウドの接続文字列を docs / Issue / PR / ログに記載しない。`.env` の実値も commit しない（[認証・認可方針書 §10](../../05_アプリケーション設計/基盤/認証・認可方針書.md)）。

### 8.2 `.env` の `DATABASE_URL`

1. `supabase status` で DB URL を確認する
2. リポジトリルート `.env` の `DATABASE_URL` を **ローカル Supabase の URL** に合わせる
3. [`.env.example`](../../../.env.example) の `DATABASE_URL` ダミーは Supabase CLI ローカル既定（port **54322**）に合わせている。実環境では `supabase status` の DB URL を `.env` に設定する

api / reco が DB に接続する前に:

```bash
./scripts/dev/check-env-names.sh --strict
psql "$DATABASE_URL" -c 'SELECT 1'
```

---

## 9. master seed 投入

### 9.1 正本

| 項目 | 正本 |
| ---- | ---- |
| master seed SQL | [`supabase/seeds/masters/*.sql`](../../../supabase/seeds/masters/) |
| CLI 設定 | [`supabase/config.toml`](../../../supabase/config.toml) → `[db.seed] sql_paths = ["./seeds/masters/*.sql"]` |
| 論理定義（投入順・固定 ID） | [初期データ定義書](./初期データ定義書.md) |

`supabase/seed.sql` 単体正本は採用しない。

### 9.2 フルリセット（migration + master seed）

```bash
./scripts/db/reset-local.sh
# または: supabase db reset
```

**期待**: migration 適用後、master seed 9 ファイルがエラーなく投入される。

### 9.3 master seed のみ再投入

migration 済みでデータのみ再投入する場合:

```bash
./scripts/db/seed-masters.sh
```

`psql` が必要（§4.2）。`DATABASE_URL` は `supabase status` の DB URL またはローカル既定を使用する。

### 9.4 `scripts/db/` 補助 script 一覧

| script | 用途 |
| ------ | ---- |
| [`check-cli-version.sh`](../../../scripts/db/check-cli-version.sh) | `supabase/.cli-version` と CLI 実バージョンの一致確認 |
| [`start-local.sh`](../../../scripts/db/start-local.sh) | バージョン確認後に `supabase start` |
| [`migrate-up.sh`](../../../scripts/db/migrate-up.sh) | `supabase migration up` |
| [`reset-local.sh`](../../../scripts/db/reset-local.sh) | `supabase db reset`（migration + master seed） |
| [`seed-masters.sh`](../../../scripts/db/seed-masters.sh) | master seed のみ再投入 |
| [`status.sh`](../../../scripts/db/status.sh) | `supabase status` |
| [`stop-local.sh`](../../../scripts/db/stop-local.sh) | `supabase stop` |

詳細は [`scripts/db/README.md`](../../../scripts/db/README.md) を参照。

---

## 10. クイックスタート（チェックリスト）

Human 手元での再現確認用。Agent の acceptance criteria には **必須としない**。

- [ ] Docker Desktop 起動、WSL Integration ON
- [ ] `./scripts/db/check-cli-version.sh` 成功
- [ ] `./scripts/db/start-local.sh` 成功
- [ ] `./scripts/db/migrate-up.sh` 成功
- [ ] `./scripts/db/reset-local.sh` または `./scripts/db/seed-masters.sh` 成功（optional）
- [ ] `psql "$DATABASE_URL" -c 'SELECT 1'` 成功（`.env` 設定後）

---

## 11. トラブルシュート

| 症状 | 想定原因 | 対処 |
| ---- | -------- | ---- |
| `Cannot connect to the Docker daemon` | Docker Desktop 未起動 / WSL Integration OFF | Windows で Docker Desktop 起動、Integration ON、`wsl --shutdown` 後に再起動 |
| `check-cli-version.sh` 失敗 | CLI 未インストール / pin 不一致 | §5 に従い pin 版をインストール、または pin 更新を別 PR で検討 |
| `port 54322 is already allocated` | 他 Postgres / 旧 supabase プロセス | `supabase stop`、競合プロセス停止、`supabase/config.toml` の `[db] port` 確認 |
| `supabase start` が長時間停止 | 初回イメージ DL | ネットワーク・ディスク容量確認、再実行 |
| `psql: connection refused` | `supabase start` 未完了 | `./scripts/db/status.sh` で DB が running か確認 |
| migration 失敗 | DDL 不整合 / 二重適用 | ログ確認。再検証時は §7 の `db reset` を検討 |

---

## 12. 関連ドキュメント

| ドキュメント | 関係 |
| ------------ | ---- |
| [マイグレーション方針書](./マイグレーション方針書.md) | migration 正本・コマンド一覧 |
| [ローカルDB検証手順書](./ローカルDB検証手順書.md) | Phase2 `db/ddl/` スモーク検証 |
| [ローカル開発手順書](../cross_cutting/ローカル開発手順書.md) | 全体セットアップ・Redis 等 |
| [環境設計書 §19](../cross_cutting/環境設計書.md) | 環境変数正本 |
| [supabase/README.md](../../../supabase/README.md) | Supabase ディレクトリ索引 |

---

## 13. 変更履歴

| 日付 | 変更内容 | Task |
| ---- | -------- | ---- |
| 2026-06-19 | 初版作成（Supabase CLI + Docker Desktop、CLI pin、`scripts/db/`） | #658 |
| 2026-06-19 | §9 master seed（`supabase/seeds/masters` + `config.toml` [db.seed]） | #660 |
