# tests/recommendation-quality/

レコメンド品質評価テスト（Epic C C4 `test-reco-quality.yml`）の実行コード配置先。

固定評価ケースの正本は `tests/fixtures/evaluation/cases.json` とする。

## 実行

| 区分 | コマンド / パス |
| ---- | --------------- |
| GHA workflow | `.github/workflows/test-reco-quality.yml`（`workflow_dispatch`） |
| ローカル / CI ランナー | `node tests/recommendation-quality/run-evaluation.mjs` |
| 出力 | `tests/recommendation-quality/output/`（artifact 正本） |

### ローカル実行例

```bash
node tests/recommendation-quality/run-evaluation.mjs \
  --pipeline-mode skeleton \
  --openai-mode mock
```

## C4 からの参照

| 参照先 | 用途 |
| ------ | ---- |
| `tests/fixtures/evaluation/cases.json` | 固定評価ケース |
| `tests/fixtures/evaluation/mock-results/` | skeleton モード用 mock パイプライン結果 |
| `tests/fixtures/external-api/openai/` | OpenAI mock |
| `tests/fixtures/manifest.json` | item UUID 対応 |
| `scripts/db/seed-test-data.sh` | Layer2 test seed 投入 |

## OpenAI 方針

| `openai_mode` | 扱い |
| ------------- | ---- |
| `mock`（既定） | fixture mock。secret 不要 |
| `secrets` | `secrets.OPENAI_API_KEY` 注入。Human 判断後の限定利用 |

人手評価の最終判定は Human scope（テスト定義書 §9.7.3）。Agent は自動メトリクス + artifact 出力まで。
