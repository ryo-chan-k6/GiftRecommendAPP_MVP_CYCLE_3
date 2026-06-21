# tests/

横断的なテストコード、E2E、非機能テスト、品質評価テスト、Layer2 GHA 用 fixture を配置する。

正本: [プロジェクトディレクトリ構成定義書 §11](../docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md)

## 構成

| パス | 役割 |
| ---- | ---- |
| `fixtures/` | Layer2 システム/品質テスト共通 fixture（Epic C C2 正本） |
| `e2e/` | End-to-End テスト（Epic C C3 `test-system.yml` で利用） |
| `recommendation-quality/` | レコメンド品質評価テスト（Epic C C4 `test-reco-quality.yml` で利用） |
| `integration/` | 横断結合テスト（後続 Task） |
| `tech-verification/` | 技術検証スクリプト（後続 Task） |
| `non-functional/` | 非機能テスト（後続 Task） |

## Layer2 fixture（C2）

- **JSON / mock 正本**: `fixtures/`（`manifest.json` が索引）
- **DB test seed 正本**: `supabase/seeds/test-data/`（master seed とは分離）
- **投入**: `./scripts/db/seed-test-data.sh`（`supabase db reset` では投入しない）

C3 `test-system.yml` / C4 `test-reco-quality.yml` は、workflow 内で上記パスを checkout 後に参照する。

OpenAI / Embedding の Layer2 注入方針は [テスト定義書 §8.1](../docs/05_アプリケーション設計/テスト/テスト定義書.md) を正とする。
