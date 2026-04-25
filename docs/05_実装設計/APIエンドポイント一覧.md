## 1. 位置づけ

本一覧は **API仕様書の前段成果物** として、公開すべきエンドポイントを業務単位で整理したものである。

ここでは以下を定義する。

- エンドポイント名
- HTTPメソッド
- URL
- 主用途
- 主な利用者
- 主な入力
- 主な出力
- 認証要否
- 主な記録対象

JSON Schema、項目の型、制約、詳細な認可制御、エラー詳細は後続のAPI仕様書で定義する。

---

## 2. APIエンドポイント一覧（統合版）

[無題](https://www.notion.so/346ccad73e6080398644cceb195d1cce?pvs=21)

---

## 3. 補足

### 3-1. 一般ユーザー向け履歴API

一般ユーザーのレコメンド履歴画面を想定し、以下を一般APIとして追加する。

- `GET /api/v1/recommendation-runs`
- `GET /api/v1/recommendation-runs/{runId}`
- `GET /api/v1/recommendation-runs/{runId}/result`

これらは認可により **自分のrunのみ参照可能** とする。

---

### 3-2. 管理向け履歴API

管理者向けには、一般ユーザー向けAPIと同一リソースを扱いつつも、以下の目的で別API群とする。

- 全件参照
- 調査用メタ情報参照
- 実行イベント確認
- 分析・運用用途

---

### 3-3. 状態変更APIの一本化

`semantic_config` および `model_version` の状態変更は、個別の `activate / deactivate` を分けず、以下のように一本化する。

- `POST /api/v1/admin/semantic-configs/{configId}/status`
- `POST /api/v1/admin/model-versions/{modelVersionId}/status`

入力例：

```
{
  "targetStatus":"active"
}
```

または

```
{
  "targetStatus":"inactive"
}
```

この方式により、API本数を抑えつつ、`GET + POST中心` の設計思想と整合を取る。

---

### 3-4. 実験割当判定API

A/Bテストの割当は、単純な完全ランダムではなく、

- ユーザー属性
- レコメンド検索条件パターン

を踏まえて判定する前提とする。

そのため、`GET /current` ではなく **`POST /resolve`** により判定材料を明示入力する。

主な入力の意味：

| 入力項目       | 内容                                                   |
| -------------- | ------------------------------------------------------ |
| experimentKey  | 対象実験の識別子                                       |
| userId         | 割当対象ユーザー                                       |
| userAttributes | 性別、会員種別、新規/既存など                          |
| requestContext | relationship, occasion, budget帯, 検索条件パターンなど |

主な出力の意味：

| 出力項目          | 内容                               |
| ----------------- | ---------------------------------- |
| assignmentPattern | 割当方式や判定結果種別             |
| experimentGroup   | A / B / control など               |
| isTarget          | 実験対象かどうか                   |
| reason            | 対象外理由または割当根拠の簡易情報 |

---

## 4. エンドポイント設計の基本ルール

| ルール           | 適用                    |
| ---------------- | ----------------------- |
| 単純参照         | GET + Query             |
| 複雑検索         | POST + Body + `/search` |
| 実行             | POST                    |
| 状態変更業務操作 | POST + `/{id}/status`   |
| 単一識別         | Path Parameter          |
| 削除             | 提供しない              |

---

## 5. 次工程で詰める項目

API仕様書では、上記各エンドポイントについて以下を定義する。

| 項目            | 内容                                              |
| --------------- | ------------------------------------------------- |
| Request Header  | Authorization, X-Request-Id, Idempotency-Key など |
| Path Parameter  | 型、必須、意味                                    |
| Query Parameter | 絞り込み、ソート、ページング                      |
| Request Body    | フィールド、型、制約                              |
| Response Body   | フィールド、型、意味                              |
| エラー          | 4xx / 5xx、業務コード                             |
| 認可            | 利用者種別、ロール制御                            |
| ログ            | どのログをどの粒度で記録するか                    |

---

## 6. 一言まとめ

```
利用者向けは「推薦実行」「行動記録」「自分の履歴参照」を公開し、
管理・評価・内部連携は用途別にエンドポイントを分離する。
単純参照は GET、複雑検索・実行・状態変更は POST を採用する。
```
