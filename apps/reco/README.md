# apps/reco

## 1. 役割

`apps/reco` は Gift Recommendation Service のレコメンドエンジンである。

主な責務は以下とする。

- 候補取得
- 特徴量処理
- スコア計算
- ランキング
- レコメンド結果生成
- レコメンド過程の観測可能性確保

---

## 2. 責務境界

### 実施してよいこと

- retrieval
- scoring
- ranking
- recommendation 結果生成
- semantic config / model version 参照
- score breakdown 生成
- Reco過程のログ・メトリクス出力

### 実施してはいけないこと

- UI都合の整形
- APIルーティング処理
- Batch専用のETL処理
- DBテーブルの生構造露出
- Web都合のロジック混入

---

## 3. 参照すべき設計書

Reco設計・実装前に、少なくとも以下を参照すること。

- `docs/.../レコメンドアーキテクチャ設計書.md`
- `docs/.../論理ER.md`
- `docs/.../テーブル一覧.md`
- `docs/.../カラム定義表.md`
- `docs/.../Observability方針書.md`
- `docs/.../テスト方針書.md`
- `docs/.../テスト計画書.md`

必要に応じて以下も参照すること。

- `docs/.../特徴量分布監視設計書.md`
- `docs/.../正規化統計量管理設計書.md`
- `docs/.../オフライン評価設計書.md`

---

## 4. 想定ディレクトリ構成

```text
apps/reco/
├─ src/
│  ├─ api/
│  ├─ usecases/
│  ├─ modules/
│  ├─ retrievers/
│  ├─ scorers/
│  ├─ rankers/
│  ├─ feature_store/
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

| ディレクトリ        | 役割                         |
| ------------------- | ---------------------------- |
| `src/api`           | Recoサービス入口             |
| `src/usecases`      | レコメンド処理全体の流れ制御 |
| `src/modules`       | ドメイン別処理               |
| `src/retrievers`    | 候補取得                     |
| `src/scorers`       | スコア計算                   |
| `src/rankers`       | 順位決定                     |
| `src/feature_store` | 特徴量取得・参照             |
| `src/repositories`  | 永続化アクセス               |
| `src/schemas`       | I/O定義                      |
| `src/lib`           | 共通処理                     |
| `src/config`        | 設定                         |

---

## 6. 実装ルール

- Social × Symbolic モデルを前提にする
- conformity は使用しない
- retrieval / scoring / ranking を分離する
- `semantic_config` / `semantic_config_version` / `model_version` を考慮する
- `recommendation_run` 単位で追跡可能にする
- score breakdown を説明可能性の観点で意識する
- Reco内部で API / UI / Batch 都合を混ぜない

---

## 7. テスト観点

最低限、以下を確認すること。

- スコア計算の正しさ
- 条件分岐
- 境界値
- retrieval / ranking の成立
- version参照整合
- runId追跡可能性
- ログ / メトリクス / 分布確認可能性

---

## 8. 補足

このディレクトリは「おすすめを返す場所」ではなく、

**意味ベース推薦ロジックを一貫性ある構造で実装する場所** として扱うこと。
