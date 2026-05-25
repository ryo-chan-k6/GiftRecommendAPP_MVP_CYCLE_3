## 1. 概要

<!-- Task PRの目的と変更概要を記載 -->

| 項目 | 内容 |
| ---- | ---- |
| Task ID |  |
| Definition |  |
| 対象Issue |  |
| Parent Epic Issue |  |
| Source Branch |  |
| Target Branch |  |

## 2. 対象Issue

<!-- Task PRでは Related to を使用する。Task IssueのDone / closeはPR merge時workflowで制御する。 -->

Related to #

Task PRでは原則としてGitHubの自動close keywordを使用しない。

## 3. Branch / PR target確認

- [ ] Target Branch は Parent Epic Branch である
- [ ] Task Branch から `develop` へ直接PRしていない
- [ ] Source Branch と対象Issueが対応している

## 4. 対応内容

- 

## 5. scope / out_of_scope 確認

### scope

- 

### out_of_scope

- 

### scope外変更

| 項目 | 内容 |
| ---- | ---- |
| scope外変更 | なし / あり |
| 補足 |  |

## 6. 変更ファイル

| 区分 | ファイル |
| ---- | -------- |
| docs |  |
| source |  |
| tests |  |
| config / scripts |  |
| generated |  |

## 7. テスト・検証結果

### 実施済み

- [ ] 

### 実行コマンド

```bash

```

### 未実施

<!-- 未実施がある場合は、理由・代替確認・残リスクを記載 -->

- [ ] なし
- [ ] あり

## 8. CI結果

| 項目 | 内容 |
| ---- | ---- |
| CI実行有無 |  |
| CI結果 |  |
| 失敗Job |  |
| 補足 |  |

## 9. generated確認

| 項目 | 内容 |
| ---- | ---- |
| generated差分 | なし / あり |
| 手動編集有無 | なし / あり |
| 生成元 |  |
| 再生成コマンド |  |
| Contract Task要否 |  |

generatedファイルは手動編集しない。

## 10. API / DB / Contract / security 影響

| 観点 | 影響有無 | 補足 |
| ---- | -------- | ---- |
| API仕様 |  |  |
| OpenAPI |  |  |
| Orval |  |  |
| API client |  |  |
| DB schema |  |  |
| migration |  |  |
| CI/CD |  |  |
| security |  |  |

## 11. security確認

- [ ] secret、APIキー、access token、password、private keyを含んでいない
- [ ] `.env` 実値を含んでいない
- [ ] DB接続文字列の実値を含んでいない
- [ ] ログ出力に機密情報を含めていない

## 12. 完了条件チェック

- [ ] 

## 13. Review観点

- 

## 14. Human Reviewで確認してほしいこと

- なし

## 15. 未実施事項 / 残課題

- なし

## 16. Status更新意図

| 項目 | 内容 |
| ---- | ---- |
| 現在Status | `In Progress` |
| 次Status | `AI Review` |
| 更新意図 | `In Progress → AI Review` |
