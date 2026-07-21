# Experiment: SCR-005〜007 回帰 E2E

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-17 |
| Epic | #1418 |
| Task | #1419 |
| 目的 | D1 後の SCR-005（points/detail）・SCR-006・SCR-007 短い手動回帰 |

## 実施内容

1. Docker / Supabase / Redis / reco / api / web を起動（develop tip `4e795065`）
2. master / test-data seed
3. PUB-002 で結果ありを取得し、UI で S5' / S7 / S8 を確認
4. チェックリスト §9 / 手順書 §10.4.16 を更新

## 結果（事実）

| ID | 結果 | 根拠 |
| ---- | ---- | ---- |
| S5' | **pass** | 「理由の詳細」展開で `reasonPoints` 2件表示。本実行の応答に `reasonDetail` は無し（任意） |
| S7 | **pass** | 商品詳細で名称・¥4,320・外部EC・結果一覧へ戻るを確認 |
| S8 | **pass** | Feedback モーダルで「良い」送信 →「フィードバックを受け付けました。」 |

| 項目 | 値 |
| ---- | ---- |
| `recommendationResultId` | `8723c5d6-7514-4195-8ba4-8095a3fb55dc` |
| `traceId` | `scr-reg-e2e-s5-001` |
| `resultItemCount` | 1 |

## 環境

| 項目 | 値 |
| ---- | ---- |
| develop tip（アプリ） | `4e795065`（Reason Postgres #1417 含む） |
| Docker | OK |
| DB / Redis / api / reco / web | 起動確認済み |

### 実行時メモ（事実）

- Cursor ブラウザの `http://localhost:3000` が古い `page.js`（Feedback「準備中」時代）を返す事象あり
- 本実行は WSL IP（`172.28.140.226:3000`）経由で現行 chunk を確認
- API 疎通のため一時的に `NEXT_PUBLIC_API_BASE_URL` / `CORS_ALLOWED_ORIGINS` に同 IP を追加。実行後 `.env` は復元（commit なし）

## 次（推論）

- 手動回帰証跡としては充足。Playwright（D2）は別後続のまま
- localhost 経由のブラウザキャッシュ／WSL relay の挙動は、ローカル E2E 時の注意点として残す
