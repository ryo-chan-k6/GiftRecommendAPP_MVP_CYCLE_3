# scripts/ai/

Task Definition 検証・プロンプト補助など、GitHub Actions に閉じない AI 運用補助を配置するディレクトリ。

正本: [プロジェクトディレクトリ構成定義書 §12.1](../../docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md)

## MVP（Task ③ / Human 判断 2026-06-07）

- **README のみ**。Python 実装（`validate_task_definition.py` 等）は Phase0 別 Task まで保留
- GitHub 連携スクリプトは `.github/scripts/` を正とする

## 配置予定（Phase0 / 別 Task）

| ファイル（例） | 役割 |
| -------------- | ---- |
| `validate_task_definition.py` | Task Definition schema 検証 |
| `render_prompt.py` | Command + Definition からプロンプト生成 |
| `check_prompt_refs.py` | Definition 内 docs 参照の存在確認 |
