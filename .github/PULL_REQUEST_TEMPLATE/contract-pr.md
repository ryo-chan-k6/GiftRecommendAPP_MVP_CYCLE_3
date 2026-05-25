## 1. 概要

<!-- Contract Task PRの目的と変更概要を記載 -->

| 項目 | 内容 |
| ---- | ---- |
| Contract ID |  |
| Contract種別 |  |
| Definition |  |
| 対象Issue |  |
| Parent Epic Issue |  |
| Source Branch |  |
| Target Branch |  |

## 2. 対象Issue

<!-- Contract Task PRでは Related to を使用する。Task IssueのDone / closeはPR merge時workflowで制御する。 -->

Related to #

Contract Task PRでは原則としてGitHubの自動close keywordを使用しない。

## 3. 契約変更内容

| 項目 | 内容 |
| ---- | ---- |
| API ID |  |
| API名 |  |
| API種別 |  |
| Method |  |
| Endpoint |  |
| 変更種別 |  |
| 破壊的変更 |  |
| 後方互換性 |  |

## 4. Branch / PR target確認

- [ ] Target Branch は Parent Epic Branch である
- [ ] Contract Task Branch から `develop` へ直接PRしていない
- [ ] Source Branch と対象Issueが対応している

## 5. 対応内容

- 

## 6. scope / out_of_scope 確認

### scope

- 

### out_of_scope

- 

### scope外変更

| 項目 | 内容 |
| ---- | ---- |
| scope外変更 | なし / あり |
| 補足 |  |

## 7. 変更ファイル

| 区分 | ファイル |
| ---- | -------- |
| docs |  |
| OpenAPI |  |
| Orval |  |
| generated |  |
| provider / consumer |  |
| tests |  |

## 8. 影響範囲

| 対象 | 影響有無 | 内容 |
| ---- | -------- | ---- |
| API設計書 |  |  |
| API一覧 |  |  |
| API仕様書 |  |  |
| OpenAPI |  |  |
| Orval |  |  |
| generated |  |  |
| provider |  |  |
| consumer |  |  |
| DB |  |  |
| security |  |  |

## 9. generated 方針

| 項目 | 内容 |
| ---- | ---- |
| generated発生 |  |
| 手動編集 | false |
| 生成元 |  |
| 再生成コマンド |  |
| 出力先 |  |
| 検証コマンド |  |

generatedファイルは手動編集しない。

## 10. テスト・検証結果

### 実施済み

- [ ] 

### 実行コマンド

```bash

```

### 未実施

<!-- 未実施がある場合は、理由・代替確認・残リスクを記載 -->

- [ ] なし
- [ ] あり

## 11. 互換性・rollout

| 項目 | 内容 |
| ---- | ---- |
| 破壊的変更 |  |
| 後方互換性 |  |
| rollout順 |  |
| 補足 |  |

## 12. security確認

- [ ] secret、APIキー、access token、password、private keyを含んでいない
- [ ] `.env` 実値を含んでいない
- [ ] DB接続文字列の実値を含んでいない
- [ ] 認証・認可への影響がある場合、影響範囲を明記している

## 13. Human Review観点

- 

## 14. 残課題

- なし

## 15. Status更新意図

| 項目 | 内容 |
| ---- | ---- |
| 現在Status | `In Progress` |
| 次Status | `AI Review` |
| 更新意図 | `In Progress → AI Review` |
