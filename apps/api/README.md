# apps/api

## 1. 役割

`apps/api` は Gift Recommendation Service の API アプリケーションである。

主な責務は以下とする。

- HTTPリクエスト受付
- バリデーション
- 認証認可
- ユースケース起動
- Reco / DB / 外部サービスとの調停
- レスポンス返却
- APIレベルのObservability成立

---

## 2. 責務境界

### 実施してよいこと

- APIエンドポイント定義
- request / response の制御
- 入力バリデーション
- 業務ユースケース起動
- Reco / Repository / Client 呼び出し
- エラー変換
- runId / ログ / メトリクス出力

### 実施してはいけないこと

- UIロジックの実装
- Recoコアアルゴリズムの実装
- DBテーブル都合をそのまま外部IFへ露出
- Batch処理の直接実装
- routes / controllers への複雑業務ロジック埋め込み

---

## 3. 参照すべき設計書

API設計・実装前に、少なくとも以下を参照すること。

- `docs/.../API仕様書.md`
- `docs/.../API設計方針書.md`
- `docs/.../テーブル一覧.md`
- `docs/.../カラム定義表.md`
- `docs/.../エラーコード-エラーメッセージ設計書.md`
- `docs/.../Observability方針書.md`
- `docs/.../テスト方針書.md`
- `docs/.../テスト計画書.md`

---

## 4. 想定ディレクトリ構成

```text
apps/api/
├─ src/
│  ├─ routes/
│  ├─ controllers/
│  ├─ usecases/
│  ├─ services/
│  ├─ repositories/
│  ├─ clients/
│  ├─ middlewares/
│  ├─ schemas/
│  ├─ lib/
│  ├─ config/
│  └─ index.ts
├─ tests/
├─ openapi/
└─ README.md
```

---

## 5. ディレクトリ責務

| ディレクトリ       | 役割                            |
| ------------------ | ------------------------------- |
| `src/routes`       | ルーティング定義                |
| `src/controllers`  | request / response 制御         |
| `src/usecases`     | 業務処理の流れ制御              |
| `src/services`     | 再利用可能な内部処理            |
| `src/repositories` | DBアクセス                      |
| `src/clients`      | 外部サービス接続                |
| `src/middlewares`  | 認証認可・共通制御              |
| `src/schemas`      | request / response / validation |
| `src/lib`          | 汎用処理                        |
| `src/config`       | 設定                            |

---

## 6. 実装ルール

- API仕様書を正本として実装する
- request / response / error を明確に分離する
- Reco内部ロジックをAPI層に持ち込まない
- recommendation_run / runId を追跡可能にする
- API成功・失敗を観測可能にする
- API変更時は docs を更新する

---

## 7. テスト観点

最低限、以下を確認すること。

- request バリデーション
- response 形式
- 正常系
- 代表異常系
- エラーコード / ステータス
- DB / Reco 連携
- runId / ログ / メトリクス

---

## 8. 補足

このディレクトリは「ルーティングを書く場所」ではなく、

**業務入口としてのAPI境界を正しく維持する場所** として扱うこと。
