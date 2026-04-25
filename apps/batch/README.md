# apps/batch

## 1. 役割

`apps/batch` は Gift Recommendation Service の Batch / ETL / 定期処理アプリケーションである。

主な責務は以下とする。

- 外部データ取得
- データ変換
- 正本更新
- 派生データ再計算
- 集計
- 評価用データ生成
- 定期メンテナンス
- Batch処理の追跡可能性確保

---

## 2. 責務境界

### 実施してよいこと

- collector / transformer / loader / job の実装
- データ取得
- ETL
- 正本更新
- 派生再計算
- 評価系バッチ
- job実行履歴管理
- Batchログ / メトリクス出力

### 実施してはいけないこと

- UI導線依存処理
- OL同期レスポンス前提処理
- API責務の実装
- Recoのオンライン業務処理実装
- 取得 / 変換 / 反映の責務混在

---

## 3. 参照すべき設計書

Batch設計・実装前に、少なくとも以下を参照すること。

- `docs/.../バッチ仕様書.md`
- `docs/.../OL-BT責務整理表.md`
- `docs/.../データ供給前提整理表.md`
- `docs/.../テーブル一覧.md`
- `docs/.../カラム定義表.md`
- `docs/.../テーブル設計方針書.md`
- `docs/.../ログ設計書.md`
- `docs/.../Observability方針書.md`
- `docs/.../テスト方針書.md`
- `docs/.../テスト計画書.md`

---

## 4. 想定ディレクトリ構成

```text
apps/batch/
├─ src/
│  ├─ jobs/
│  ├─ collectors/
│  ├─ transformers/
│  ├─ loaders/
│  ├─ repositories/
│  ├─ schemas/
│  ├─ lib/
│  ├─ config/
│  └─ main.py
├─ tests/
└─ README.md
```

---

## 5. ディレクトリ責務

| ディレクトリ       | 役割                     |
| ------------------ | ------------------------ |
| `src/jobs`         | 処理単位の開始・順序制御 |
| `src/collectors`   | 外部データ取得           |
| `src/transformers` | 内部形式への変換         |
| `src/loaders`      | DB反映                   |
| `src/repositories` | 永続化アクセス           |
| `src/schemas`      | I/O定義                  |
| `src/lib`          | 共通処理                 |
| `src/config`       | 設定                     |

---

## 6. 実装ルール

- collector / transformer / loader / job を分離する
- 冪等性を考慮する
- 再実行性を考慮する
- どこまで処理できたか追跡可能にする
- `pipeline_job_run` 等の実行履歴と整合する
- 正本 / 派生 / ログ / 評価 の区分を崩さない
- `semantic_config_version` / `model_version` を意識する

---

## 7. テスト観点

最低限、以下を確認すること。

- 冪等性
- 再実行性
- 入力 / 変換 / 反映の整合
- 正本更新結果
- 失敗時ログ
- job実行履歴
- メトリクス出力

---

## 8. 補足

このディレクトリは「定期的に回す処理を書く場所」ではなく、

**運用に耐える取得・変換・反映パイプラインを構築する場所** として扱うこと。
