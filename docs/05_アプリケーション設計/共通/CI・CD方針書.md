# CI・CD方針書

## 1. 目的

本方針書は、Gift Recommendation Service の開発・テスト・デプロイを自動化し、**品質と開発速度を両立するCI/CD方針**を定義する。

本方針書の目的は以下である。

```text
- 品質ゲートを自動化する
- リリースの安全性を担保する
- 手動作業を最小化する
- テスト方針・ブランチ戦略と整合させる
- docs正本と実装コードの整合性を維持する
- OpenAPIとOrval生成APIクライアントの整合性を維持する
- MVP開発に適した軽量CI/CDを構築する
```

---

## 2. 前提

| 項目                | 内容                          |
| ------------------- | ----------------------------- |
| 開発体制            | 個人開発                      |
| Repo                | monorepo                      |
| ブランチ戦略        | main / develop / feature      |
| 正本                | repo内 `docs/`                |
| API契約             | OpenAPI                       |
| APIクライアント生成 | Orval                         |
| コード定義          | `packages/code-definitions/`  |
| CI/CD               | GitHub Actions                |
| テスト方針          | 重点集中型                    |
| Observability       | MVPから重要                   |
| デプロイ            | Web / API / Reco / Batch 分離 |

---

## 3. CI/CD基本方針

### 3.1 基本方針

| 方針                                    | 内容                                                            |
| --------------------------------------- | --------------------------------------------------------------- |
| CIは品質ゲートとする                    | build / lint / test / typecheck / contract check を自動実行する |
| CDは安全にリリースするための制御とする  | MVPでは完全自動デプロイではなく、半自動方式を基本とする         |
| 自動化は最小構成から始める              | 個人開発で維持できる範囲に絞る                                  |
| 手動判断を完全には排除しない            | 本番反映・リリース判断は人間が行う                              |
| docs正本との整合を重視する              | 設計変更がある場合はdocs更新を前提とする                        |
| API契約の整合を重視する                 | OpenAPIと生成APIクライアントの乖離をCIで検知する                |
| Observability成立をリリース条件に含める | 出した後に追跡できる状態をデプロイ条件とする                    |

---

### 3.2 事実と推論

#### 事実

```text
- MVPではテストを完全網羅しない
- 個人開発である
- web / api / reco / batch が分離している
- API仕様とAPIクライアントを手動同期すると不整合が起きやすい
- レコメンド品質はObservabilityと評価データに依存する
```

#### 推論

```text
CI/CDは軽量でよいが、以下は必須とする。

- 壊れないこと
- API契約が破綻していないこと
- Orval生成物がOpenAPIと乖離していないこと
- 生成物を手動編集していないこと
- リリース後に観測できること
```

---

## 4. パイプライン全体像

```mermaid
flowchart TD
    A["Issue / Branch"] --> B["docs / code / OpenAPI 更新"]
    B --> C["Local Check"]
    C --> D["Pull Request"]
    D --> E["CI"]

    E --> E1["build"]
    E --> E2["lint / format"]
    E --> E3["typecheck"]
    E --> E4["unit test"]
    E --> E5["integration test"]
    E --> E6["OpenAPI check"]
    E --> E7["Orval generate check"]
    E --> E8["generated diff check"]
    E --> E9["code-definitions check"]
    E --> E10["Observability basic check"]

    E1 --> F["Review"]
    E2 --> F
    E3 --> F
    E4 --> F
    E5 --> F
    E6 --> F
    E7 --> F
    E8 --> F
    E9 --> F
    E10 --> F

    F --> G["develop merge"]
    G --> H["Integration Check"]
    H --> I["main merge"]
    I --> J["CD / Deploy"]
    J --> K["Post Deploy Check"]
```

---

## 5. CI（継続的インテグレーション）

## 5.1 目的

CIの目的は以下である。

```text
- コード品質を担保する
- 不具合を早期検知する
- API契約の破壊を検知する
- Orval生成物とOpenAPIの乖離を検知する
- code-definitionsの構文不備を検知する
- PRのマージ可否判断を支援する
```

---

## 5.2 実行タイミング

| タイミング        | 実行方針                   |
| ----------------- | -------------------------- |
| PR作成            | 実行                       |
| PR更新            | 実行                       |
| developマージ     | 実行                       |
| mainマージ        | 実行                       |
| workflow_dispatch | 必要に応じて手動実行       |
| schedule          | 定期バッチ・定期検証で利用 |

---

## 5.3 CI実行内容

### 5.3.1 build

| 対象            | 内容                                 |
| --------------- | ------------------------------------ |
| web             | Next.js build                        |
| api             | TypeScript build                     |
| reco            | Python import / package check        |
| batch           | Python import / package check        |
| shared packages | 共有パッケージのbuild / import check |

---

### 5.3.2 lint / format

| 対象       | 内容                                                   |
| ---------- | ------------------------------------------------------ |
| TypeScript | lint / format check                                    |
| Python     | lint / format check                                    |
| Markdown   | 必要に応じてlint                                       |
| YAML       | GitHub Actions / OpenAPI / code-definitions の構文確認 |

---

### 5.3.3 typecheck

| 対象             | 内容                             |
| ---------------- | -------------------------------- |
| web              | TypeScript typecheck             |
| api              | TypeScript typecheck             |
| generated client | Orval生成APIクライアントの型検証 |
| shared-types     | 共通型の型検証                   |

---

### 5.3.4 Unitテスト

| 対象         | 内容                                             |
| ------------ | ------------------------------------------------ |
| web          | UI部品、入力補助ロジック                         |
| api          | validation、response変換、error handling         |
| reco         | score計算、Feature処理、Ranking処理              |
| batch        | 変換処理、差分判定、ジョブ単位処理               |
| shared-logic | Feature / Semantic / Embedding関連の共通ロジック |

---

### 5.3.5 Integrationテスト

| 対象                 | 内容                              |
| -------------------- | --------------------------------- |
| api-db               | APIからDBへの保存・参照           |
| api-reco             | APIからRecoへの呼び出し           |
| reco-shared          | Recoからshared-logicへの呼び出し  |
| batch-shared         | Batchからshared-logicへの呼び出し |
| batch-db             | BatchからDBへの反映               |
| batch-object-storage | Raw保存・取得の確認               |

---

### 5.3.6 OpenAPI検証

OpenAPI定義をCIで検証する。

| 対象                                                | 内容                          |
| --------------------------------------------------- | ----------------------------- |
| `packages/contracts/openapi/public-api.yaml`        | web → api のPublic API契約    |
| `packages/contracts/openapi/internal-reco-api.yaml` | api → reco のInternal API契約 |

確認観点は以下とする。

```text
- OpenAPI構文が正しいこと
- path / method / request / response の定義が壊れていないこと
- enum定義が不正でないこと
- error response schema が定義されていること
- Orval生成に必要な形式を満たしていること
```

---

### 5.3.7 Orval生成検証

OpenAPIからOrvalでAPIクライアントを生成できることをCIで確認する。

| 生成対象         | 生成元                                              | 生成先                                |
| ---------------- | --------------------------------------------------- | ------------------------------------- |
| web用API client  | `packages/contracts/openapi/public-api.yaml`        | `apps/web/src/generated/api/`         |
| api用reco client | `packages/contracts/openapi/internal-reco-api.yaml` | `apps/api/src/generated/reco-client/` |

MVPでは、まず `web → api` の生成検証を必須とする。  
`api → reco` は導入時点でCI必須対象に追加する。

---

### 5.3.8 generated差分確認

Orval生成物がOpenAPIと乖離していないことを確認する。

方針は以下とする。

```text
- CI上で Orval generate を実行する
- 実行後に差分が発生する場合、生成物の更新漏れとしてCIを失敗させる
- generated配下の手動編集を禁止する
```

確認対象は以下である。

```text
apps/web/src/generated/api/
apps/api/src/generated/reco-client/
```

---

### 5.3.9 code-definitions検証

`packages/code-definitions/` 配下のコード定義をCIで検証する。

MVP初期では、まず構文チェックを対象とする。

| 対象        | 内容                             |
| ----------- | -------------------------------- |
| semantic    | Feature / Semantic関連コード定義 |
| application | mode / source type 等            |
| state       | status / phase 等                |
| batch       | batch job type 等                |
| error       | error_code 等                    |

確認観点は以下とする。

```text
- YAML / JSONの構文が正しいこと
- code値が重複していないこと
- 必須項目が欠落していないこと
- seed生成対象との関係に矛盾がないこと
```

高度な整合性チェックは、後続で段階的に追加する。

---

### 5.3.10 基盤チェック

| 対象     | 内容                                 |
| -------- | ------------------------------------ |
| 環境変数 | 必要な環境変数名が定義されていること |
| DB       | migration / connection check         |
| API      | ヘルスチェックまたは最低限の疎通     |
| Reco     | ヘルスチェックまたは最低限の疎通     |
| Batch    | dry-run可能なジョブの起動確認        |

---

### 5.3.11 Observability基本チェック

ObservabilityはMVPでも重要なため、基本チェックをCIまたは統合確認に含める。

| 対象                  | 内容                               |
| --------------------- | ---------------------------------- |
| trace_id / request_id | API処理を追跡できること            |
| run_id                | recommendation_runを追跡できること |
| phase log             | 推薦処理フェーズを追跡できること   |
| error log             | エラーを追跡できること             |
| batch log             | バッチ実行結果を追跡できること     |
| metrics               | 最低限の処理結果を確認できること   |

---

## 5.4 CI成功条件

CI成功条件は以下とする。

```text
- buildが成功している
- lint / format checkが成功している
- typecheckが成功している
- Unitテストが成功している
- 必須Integrationテストが成功している
- OpenAPI検証が成功している
- Orval generateが成功している
- generated差分確認が成功している
- code-definitions構文チェックが成功している
- 基盤チェックが成功している
- 必須Observability基本チェックが成功している
```

---

## 6. CD（継続的デリバリー / デプロイ）

## 6.1 方針

| 方針                              | 内容                                           |
| --------------------------------- | ---------------------------------------------- |
| 完全自動デプロイはMVPでは行わない | 本番反映は明示的な判断を挟む                   |
| 半自動方式を採用する              | CI成功後、手動承認または手動実行でデプロイする |
| developで統合確認する             | main反映前に統合確認を行う                     |
| mainは安定状態を保つ              | mainは本番相当として扱う                       |
| リリース後確認を必須とする        | デプロイ後に疎通・ログ・メトリクスを確認する   |

---

## 6.2 デプロイ対象

| コンポーネント | デプロイ方針                               |
| -------------- | ------------------------------------------ |
| Web            | Vercel等へ半自動または自動デプロイ         |
| API            | Render等へ半自動デプロイ                   |
| Reco           | Fly.io等へ半自動デプロイ                   |
| Batch          | GitHub Actionsで手動またはスケジュール実行 |
| Database       | migrationを明示的に実行                    |
| Object Storage | 設定変更時のみ反映                         |

---

## 6.3 環境構成

| 環境        | 用途     |
| ----------- | -------- |
| local       | 開発     |
| develop相当 | 統合確認 |
| production  | 本番     |

MVPでは、環境数を増やしすぎない。  
ただし、本番反映前の統合確認が必要な場合は、develop相当環境を利用する。

---

## 6.4 デプロイフロー

### develop反映フロー

```mermaid
flowchart TD
    A["feature branch"] --> B["PR"]
    B --> C["CI"]
    C --> D["Review"]
    D --> E["develop merge"]
    E --> F["develop CI"]
    F --> G["Integration Check"]
```

---

### main反映フロー

```mermaid
flowchart TD
    A["develop"] --> B["main PR"]
    B --> C["CI"]
    C --> D["Release Review"]
    D --> E["main merge"]
    E --> F["Production Deploy"]
    F --> G["Post Deploy Check"]
    G --> H["Release Complete"]
```

---

## 6.5 デプロイ条件

本番デプロイ条件は以下とする。

```text
- CIが成功している
- 対象Issueの完了条件を満たしている
- docs更新が必要な場合、更新済みである
- OpenAPI変更時、Orval生成物が更新済みである
- generated配下を手動編集していない
- DB変更時、migration確認済みである
- code-definitions変更時、関連実装・seed・テストへの影響確認済みである
- 主要導線確認が完了している
- Observabilityが成立している
- rollbackまたは復旧方針が明確である
```

---

## 7. Observability連携

## 7.1 位置づけ

ObservabilityはCDの品質ゲートの一部とする。

単にデプロイできるだけではなく、デプロイ後に以下を確認できることを重視する。

```text
- どのリクエストが実行されたか
- どのrunが生成されたか
- どのphaseで失敗したか
- どのerror_codeが発生したか
- バッチがどこまで進んだか
- 推薦品質の評価に必要な情報が残っているか
```

---

## 7.2 デプロイ後確認

必須確認項目は以下とする。

```text
- 主要APIが疎通する
- run_idを追跡できる
- APIログが出力される
- reco phase logが出力される
- batch logが出力される
- error logが出力される
- 必要なmetricsが取得できる
```

---

## 7.3 リリース不可条件

以下の場合はリリース不可、またはリリース完了扱いにしない。

```text
- run_idが欠落している
- error logが出力されない
- phase logが出力されない
- バッチ実行結果が追跡できない
- 主要APIが疎通しない
- OpenAPIと生成clientが乖離している
- generated配下が手動編集されている
```

---

## 8. ブランチ戦略との連携

## 8.1 feature / fix

| 項目 | 方針                                                                 |
| ---- | -------------------------------------------------------------------- |
| CI   | 実行                                                                 |
| CD   | 実行しない                                                           |
| 対象 | build / lint / test / typecheck / OpenAPI / Orval / code-definitions |
| 目的 | PR品質確認                                                           |

---

## 8.2 develop

| 項目 | 方針                           |
| ---- | ------------------------------ |
| CI   | 実行                           |
| CD   | 必要に応じて統合確認環境へ反映 |
| 対象 | 全体CI、統合確認               |
| 目的 | main反映前の統合確認           |

---

## 8.3 main

| 項目 | 方針                                 |
| ---- | ------------------------------------ |
| CI   | 実行                                 |
| CD   | 本番デプロイ対象                     |
| 対象 | 全体CI、本番デプロイ、デプロイ後確認 |
| 目的 | 安定状態の維持                       |

---

## 8.4 hotfix

| 項目   | 方針                         |
| ------ | ---------------------------- |
| branch | main起点                     |
| CI     | 最優先実行                   |
| CD     | 手動承認後に即デプロイ可能   |
| docs   | 必要最小限の修正を同時に行う |
| 目的   | 本番障害・緊急修正対応       |

---

## 9. docs正本との連携

## 9.1 方針

docsはrepo内を正本とする。

CI/CDでは、以下のような変更がある場合にdocs更新漏れを確認する。

```text
- API仕様変更
- DB構造変更
- バッチ仕様変更
- CI/CD workflow変更
- ディレクトリ構成変更
- code-definitions変更
- 運用ルール変更
```

---

## 9.2 チェック例

| 変更内容             | 確認するdocs                                       |
| -------------------- | -------------------------------------------------- |
| API仕様変更          | API設計関連docs、OpenAPI                           |
| Orval生成設定変更    | CI・CD方針書、DevOps方針書、ディレクトリ構成定義書 |
| DB構造変更           | DB設計関連docs                                     |
| バッチ仕様変更       | バッチ設計関連docs                                 |
| code-definitions変更 | Feature / Semantic / 状態 / エラーコード関連docs   |
| workflow変更         | DevOps方針書、CI・CD方針書                         |

MVPでは、docs差分の完全自動判定は必須としない。  
まずはPRテンプレートで、参照・更新docsを明示する運用を基本とする。

---

## 10. OpenAPI / Orval連携

## 10.1 方針

OpenAPIとOrvalは、API契約とAPIクライアント実装の整合性を保つためにCIへ組み込む。

```text
OpenAPI更新
  ↓
Orval generate
  ↓
generated API client更新
  ↓
typecheck
  ↓
test
```

---

## 10.2 CI対象

| 対象                                  | CI内容                            |
| ------------------------------------- | --------------------------------- |
| `packages/contracts/openapi/`         | OpenAPI lint / schema validation  |
| `orval.config.ts`                     | Orval設定の妥当性確認             |
| `apps/web/src/generated/api/`         | 生成物差分確認、typecheck         |
| `apps/api/src/generated/reco-client/` | 導入後に生成物差分確認、typecheck |

---

## 10.3 運用ルール

```text
- OpenAPIを変更したらOrval生成を行う
- Orval生成物は手動編集しない
- 生成物の更新漏れはCIで検知する
- 生成clientを利用する実装のtypecheckをCIで通す
- 外部API clientには原則Orvalを適用しない
```

---

## 11. code-definitions連携

## 11.1 方針

`packages/code-definitions/` は、Feature、Semantic、status、phase、error_code等のコード定義を管理する領域である。

CIでは、MVP初期は構文・重複・必須項目のチェックを中心に行う。

---

## 11.2 CI対象

| 対象                                     | CI内容                                 |
| ---------------------------------------- | -------------------------------------- |
| `packages/code-definitions/semantic/`    | Feature / Semantic関連コードの構文確認 |
| `packages/code-definitions/application/` | mode等のアプリケーションコード確認     |
| `packages/code-definitions/state/`       | status / phase等の状態コード確認       |
| `packages/code-definitions/batch/`       | batch job type等の確認                 |
| `packages/code-definitions/error/`       | error_codeの確認                       |

---

## 11.3 将来拡張

将来的には、以下のチェックを追加する。

```text
- code-definitions と DB seed の整合性チェック
- code-definitions と shared_logic の整合性チェック
- error_code と API error response の整合性チェック
- status / phase と状態遷移設計の整合性チェック
```

---

## 12. 自動化範囲

## 12.1 自動化する

| 項目                         | 内容                         |
| ---------------------------- | ---------------------------- |
| build                        | 必須                         |
| lint / format                | 必須                         |
| typecheck                    | 必須                         |
| Unitテスト                   | 必須                         |
| Integrationテスト            | 重点対象のみ必須             |
| OpenAPI検証                  | 必須                         |
| Orval生成検証                | 必須                         |
| generated差分確認            | 必須                         |
| code-definitions構文チェック | 必須                         |
| 一部Observability確認        | 必須                         |
| Batch定期実行                | GitHub Actionsで実行         |
| PR通知                       | GitHub Actions + Slackで実行 |
| Projects遅延通知             | GitHub Actions + Slackで実行 |

---

## 12.2 自動化しない

| 項目                       | 理由              |
| -------------------------- | ----------------- |
| UI見た目の最終確認         | 人間判断が必要    |
| レコメンド妥当性の最終判断 | 人間評価が必要    |
| 分布評価の解釈             | 人間判断が必要    |
| 本番リリース判断           | 影響判断が必要    |
| 大規模負荷試験             | MVP初期では対象外 |

---

## 13. GitHub Actions workflow方針

## 13.1 workflow配置

GitHub Actions workflowファイルは、`.github/workflows/` 直下に配置する。

サブディレクトリ配下のworkflowファイルはGitHub Actionsに認識されないため、分類はファイル名prefixで表現する。

```text
.github/workflows/
├─ ci-web.yml
├─ ci-api.yml
├─ ci-reco.yml
├─ ci-batch.yml
├─ ci-contracts.yml
├─ ci-code-definitions.yml
├─ cd-web.yml
├─ cd-api.yml
├─ cd-reco.yml
├─ batch-daily-parent.yml
├─ batch-weekly-parent.yml
├─ batch-manual-parent.yml
├─ notify-pr-created.yml
├─ notify-pr-updated.yml
└─ notify-projects-delay.yml
```

---

## 13.2 workflow分割方針

| 分類                     | 役割                   |
| ------------------------ | ---------------------- |
| `ci-*.yml`               | CI実行                 |
| `cd-*.yml`               | デプロイ実行           |
| `batch-*.yml`            | バッチ実行             |
| `notify-*.yml`           | Slack等の通知          |
| `pr-*.yml`               | PR自動作成・自動更新   |
| `tech-verify-*.yml`      | 技術検証               |
| `perf-feasibility-*.yml` | 性能フィジビリティ検証 |

---

## 13.3 親workflow / 子workflow方針

日次系、週次系、手動前提のバッチ処理は、親workflowで起動制御し、子workflowまたは再利用workflowで個別処理を実行する。

| 親workflow                | 用途                     |
| ------------------------- | ------------------------ |
| `batch-daily-parent.yml`  | 日次バッチの先行関係制御 |
| `batch-weekly-parent.yml` | 週次バッチの先行関係制御 |
| `batch-manual-parent.yml` | 手動実行バッチの起動制御 |

---

## 14. 失敗時の対応

## 14.1 CI失敗

| 失敗内容                 | 対応                                       |
| ------------------------ | ------------------------------------------ |
| build失敗                | 修正必須、マージ禁止                       |
| lint失敗                 | 修正必須、マージ禁止                       |
| typecheck失敗            | 修正必須、マージ禁止                       |
| test失敗                 | 修正必須、マージ禁止                       |
| OpenAPI検証失敗          | OpenAPI修正必須、マージ禁止                |
| Orval生成失敗            | OpenAPIまたはOrval設定修正必須、マージ禁止 |
| generated差分検出        | 生成物更新漏れとして修正必須、マージ禁止   |
| code-definitions検証失敗 | コード定義修正必須、マージ禁止             |

---

## 14.2 デプロイ失敗

| 失敗内容              | 対応                           |
| --------------------- | ------------------------------ |
| web deploy失敗        | ログ確認、修正、再実行         |
| api deploy失敗        | ログ確認、修正、再実行         |
| reco deploy失敗       | ログ確認、修正、再実行         |
| migration失敗         | ロールバックまたは復旧手順実施 |
| post deploy check失敗 | リリース完了扱いにしない       |

---

## 14.3 Observability不備

| 不備          | 対応                     |
| ------------- | ------------------------ |
| run_id欠落    | リリース停止、修正       |
| phase log欠落 | リリース停止、修正       |
| error log欠落 | リリース停止、修正       |
| batch log欠落 | リリース停止、修正       |
| metrics欠落   | リリース完了扱いにしない |

---

## 15. 将来拡張

将来、必要に応じて以下を導入する。

```text
- 自動デプロイ
- ステージング環境
- E2E自動化
- OpenAPI breaking change検知
- code-definitions と seed の自動整合性チェック
- generated clientの利用箇所影響分析
- カナリアリリース
- Blue-Green Deployment
- 専用監視基盤
```

---

## 16. 結論

本CI/CD方針は以下を採用する。

```text
軽量CI
  ×
半自動CD
  ×
OpenAPI契約検証
  ×
Orval生成検証
  ×
code-definitions検証
  ×
Observability確認
```

これにより、MVP開発において以下を実現する。

```text
- 壊さずに変更できる
- API契約とAPI clientの不整合を防げる
- 生成物の更新漏れを防げる
- コード定義の破綻を早期検知できる
- リリース後に追跡できる
```

---
