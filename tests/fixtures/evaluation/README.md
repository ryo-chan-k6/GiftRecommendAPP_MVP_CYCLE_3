# tests/fixtures/evaluation/

レコメンド品質評価（Epic C C4 `test-reco-quality.yml`）向け固定ケース。

- **正本**: `cases.json`
- **入力**: `cases[].requestFixture` が指す `tests/fixtures/api-input/*.json`
- **期待観点**: `expectedObservations` / `autoMetrics`（人手評価は §9.7.3 必須）

C4 workflow は `cases.json` を artifact 出力し、Human が最終判定する。
