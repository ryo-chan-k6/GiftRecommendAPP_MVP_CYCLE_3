# ローカル DB 検証手順書

## 1. 目的・スコープ

| 項目 | 内容 |
| ---- | ---- |
| 目的 | Phase2 DDL（`db/ddl/*.sql`）の **実 DB スモーク検証** に必要な、WSL2 上の最小ツールチェーンと手順を定義する |
| 対象 OS | **Windows 11 + WSL2**（Ubuntu 等。リポジトリ worktree は Linux 側パス推奨） |
| 主な利用 Task | D01 拡張/enum 型 DDL（#611）、以降の D02〜 DDL バッチ |
| 正本参照 | [マイグレーション方針書](./マイグレーション方針書.md) §5.1・§13、[supabase/config.toml](../../../supabase/config.toml) |

### 1.1 含めるもの

- Docker Desktop（WSL2 バックエンド）+ WSL Integration
- WSL 内: `postgresql-client`（`psql`）
- WSL 内: Supabase CLI
- `supabase start` によるローカル Postgres 15 + pgvector
- `db/ddl/*.sql` の **直接適用**（`psql -f`）と検証 SQL

### 1.2 含めないもの（out_of_scope）

| 対象 | 理由 |
| ---- | ---- |
| Phase3 全体の環境構築（Epic #436） | Epic #435 `out_of_scope` |
| Redis / apps `.env` 整備 | 本手順は DB 検証のみ |
| `supabase/migrations/` への統合 | Task ⑤ scope |
| 本番 / クラウド Supabase への link・適用 | ローカル検証のみ |

---

## 2. 前提

### 2.1 リポジトリ配置

- worktree は **WSL の Linux ファイルシステム**（例: `/home/<user>/GitHub/...`）に置く（[worktree運用ルール](../../00_共通/AIエージェント運用/worktree運用ルール.md)）
- 作業前に必ず確認する:

```bash
pwd
git branch --show-current
git status --short
git worktree list
```

### 2.2 Supabase ローカル設定（正本）

| 項目 | 値 | 根拠 |
| ---- | --- | ---- |
| DB port | `54322` | `supabase/config.toml` `[db] port` |
| PostgreSQL | 15 | `supabase/config.toml` `[db] major_version` |
| 既定 DB 名 | `postgres` | Supabase CLI ローカル既定 |

### 2.3 DDL 適用方針

[マイグレーション方針書](./マイグレーション方針書.md) §5.1 に従い、`db/ddl/` は **設計参照用**であり、現時点では `supabase/migrations/` が空のため **検証時は `psql -f` で直接適用**する。Task ⑤ で migration 統合後は `supabase migration up` を正とする。

---

## 3. Docker Desktop のインストール（Windows ホスト）

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

---

## 4. WSL 内: postgresql-client（`psql`）

```bash
sudo apt update
sudo apt install -y postgresql-client
psql --version
```

**期待**: `psql (PostgreSQL) 14.x` 以上が表示される（クライアント版はサーバ 15 と接続可能）。

---

## 5. WSL 内: Supabase CLI

[Supabase CLI 公式手順](https://supabase.com/docs/guides/cli/getting-started) に従う。WSL では以下のいずれかを推奨する。

### 5.1 バイナリ（推奨）

公式リリースの Linux amd64 バイナリを `PATH` の通ったディレクトリに配置する。

### 5.2 npx（代替）

```bash
npx supabase --version
```

頻繁に使う場合はバイナリインストールを推奨する。

```bash
supabase --version
```

**期待**: CLI バージョンが表示される。

---

## 6. 動作確認コマンド一覧

リポジトリ worktree ルートで実施する。

```bash
cd <worktree-root>

# 1) ツールチェーン version 確認
docker version
supabase --version
psql --version

# 2) ローカル Supabase スタック起動（初回はイメージ DL で数分かかる場合あり）
supabase start

# 3) 接続情報の確認
supabase status
```

`supabase status` の **DB URL** を控える。ローカル既定の例（secret はローカル開発用の既知値）:

```text
postgresql://postgres:postgres@127.0.0.1:54322/postgres
```

> **注意**: 上記は Supabase CLI ローカル開発の既定資格情報である。本番・クラウドの接続文字列を docs / PR / Issue に記載しない。

### 6.1 D01 適用前チェック（接続のみ）

`supabase/migrations/` が空でも、空 DB への接続確認は可能である。

```bash
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -c "SELECT version();"
```

**期待**: PostgreSQL 15.x のバージョン文字列が返る。

### 6.2 検証結果の PR 記録テンプレート

PR 本文の Test plan に以下を貼り付け、実際の出力を記載する（secret なし）。

```markdown
### ローカル DB スモーク（#612）

- [ ] `docker version` 成功
- [ ] `supabase --version` 成功
- [ ] `psql --version` 成功
- [ ] `supabase start` 成功
- [ ] `supabase status` で DB URL 確認

#### コマンド出力（抜粋）

\`\`\`text
（ここに version / status の出力を貼る。パスワード・トークンはマスク）
\`\`\`
```

---

## 7. D01 適用・検証 SQL（#611 共通）

本手順は #611（`db/ddl/d01_extensions_and_enums.sql`）の段階 C でも使用する。

### 7.1 DDL 適用

```bash
cd <worktree-root>
supabase start
supabase status   # DB URL を確認

psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" \
  -f db/ddl/d01_extensions_and_enums.sql
```

### 7.2 検証 SQL

```bash
psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" <<'SQL'
\dx vector
SELECT count(*) AS enum_count FROM pg_type t
  JOIN pg_namespace n ON n.oid = t.typnamespace
  WHERE t.typtype = 'e' AND n.nspname = 'public';
SELECT typname FROM pg_type t
  JOIN pg_namespace n ON n.oid = t.typnamespace
  WHERE t.typtype = 'e' AND n.nspname = 'public'
  ORDER BY typname;
SQL
```

| 確認項目 | 期待値 |
| -------- | ------ |
| `vector` 拡張 | `\dx vector` で 1 行 |
| enum 型件数 | `26` |
| 型名 | `recommendation_run_status` / `batch_run_status` 等が別名で存在 |
| `evaluation_run_phase_name` | **存在しない**（out_of_scope） |

### 7.3 再検証時の DB リセット

同一 DB に DDL を **再実行**すると `CREATE TYPE` は失敗する（`IF NOT EXISTS` 非対応）。再検証時はクリーン DB を使う。

```bash
supabase db reset
# または
supabase stop && supabase start
```

---

## 8. トラブルシュート

| 症状 | 想定原因 | 対処 |
| ---- | -------- | ---- |
| `Cannot connect to the Docker daemon` | Docker Desktop 未起動 / WSL Integration OFF | Windows で Docker Desktop 起動、WSL Integration を ON、`wsl --shutdown` 後に再起動 |
| `port 54322 is already allocated` | 他 Postgres / 旧 supabase プロセス | `supabase stop`、競合プロセス停止、`supabase/config.toml` の `[db] port` 確認 |
| `supabase start` が長時間停止 | 初回イメージ DL | ネットワーク確認、再実行。Docker のディスク容量確認 |
| `psql: connection refused` | `supabase start` 未完了 | `supabase status` で DB が running か確認 |
| DDL 適用で `type already exists` | 同一 DB へ再適用 | §7.3 のリセット手順でクリーン DB を用意 |

---

## 9. 関連ドキュメント

| ドキュメント | 関係 |
| ------------ | ---- |
| [マイグレーション方針書](./マイグレーション方針書.md) | DDL / migration の正本方針 |
| [DDLバッチ分割表](./DDLバッチ分割表.md) | D01〜 バッチ順序 |
| [supabase/README.md](../../../supabase/README.md) | Supabase CLI 配置・クイックスタート |
| [db/README.md](../../../db/README.md) | `db/ddl/` と `supabase/migrations/` の役割 |

---

## 10. 変更履歴

| 日付 | 変更内容 | Task |
| ---- | -------- | ---- |
| 2026-06-17 | 初版作成 | #612 |
