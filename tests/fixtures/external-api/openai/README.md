# OpenAI mock fixture

Layer2（GHA `workflow_dispatch`）での OpenAI / Embedding 利用方針の fixture 正本。

## 方針（要約）

| 区分 | Layer2 既定 | 例外 |
| ---- | ----------- | ---- |
| Embedding API | `embedding-success.json` 等の **fixture mock** | なし（MVP） |
| Chat Completion（理由文） | `chat-completion-reason-success.json` mock | Human 判断後、`OPENAI_API_KEY` を GHA Secrets 注入して限定実接続可 |
| Secrets | **commit 禁止** | dispatch 入力または `secrets.OPENAI_API_KEY` のみ |

詳細は [テスト定義書 §8.1](../../../docs/05_アプリケーション設計/テスト/テスト定義書.md) を正とする。

## fixture 一覧

| ファイル | 用途 |
| -------- | ---- |
| `embedding-success.json` | `text-embedding-3-small` 成功（1536 次元） |
| `chat-completion-reason-success.json` | 理由文生成成功 |
| `rate-limit-error.json` | 異常系（retry / fallback 検証） |

mock 実装は HTTP レイヤで上記 JSON を返す。実 API キーはテストコード・fixture に含めない。
