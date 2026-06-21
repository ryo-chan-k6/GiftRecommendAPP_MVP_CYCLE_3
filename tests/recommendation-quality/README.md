# tests/recommendation-quality/

レコメンド品質評価テスト（Epic C C4 `test-reco-quality.yml`）の実行コード配置先。

固定評価ケースの正本は `tests/fixtures/evaluation/cases.json` とする。C4 Task で workflow と自動メトリクス出力を実装する。

## C4 からの参照

| 参照先 | 用途 |
| ------ | ---- |
| `tests/fixtures/evaluation/cases.json` | 固定評価ケース |
| `tests/fixtures/external-api/openai/` | OpenAI mock |
| `tests/fixtures/manifest.json` | item UUID 対応 |

人手評価の最終判定は Human scope（テスト定義書 §9.7.3）。
