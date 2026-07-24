# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-07-24-rakuten-api-qps-ip-verify-policy` |
| Log種別 | `human-decision` |
| 件名 | 楽天市場 API: 目標 QPS・接続元 IP 必須・Rate Limiter Task 切り・本番 egress は Backlog |
| 発生日時 | 2026-07-24 |
| 記録日時 | 2026-07-24 |
| 発生元Command | 再設計検討（#1603）への Human 回答 |
| 発生元Agent | `support-ai` / 作業 Agent |
| 関連Issue | #1603（T2b live 疎通） / #1598（親 Epic） |
| 重要度 | `high` |
| 状態 | `decided`（本番 egress 設計は Backlog・未検討） |

---

## 2. 結論

楽天市場 API アプリ登録（予想 QPS 上限 10・接続元 IP 登録）を前提に、以下を採用する。

| No | 論点 | 決定 |
| -- | ---- | ---- |
| 1 | クライアント目標 QPS | **8**（登録上限 10 の下。運用目標） |
| 2 | live 検証時の egress IP 照合 | **必須**。不一致または未設定時は楽天 HTTP を行わず中止 |
| 3 | Rate Limiter 実装タイミング | **#1603 は検証ハーネスの最小間隔のみ**。`MOD-BATCH-008` External API Rate Limiter 本実装は **直後の別 Task** |
| 4 | 本番 / 検証環境の固定 egress IP 設計 | **Backlog 登録のみ**。現時点では検討しない |

補足（決定に付随する運用前提）:

- live 検証は **登録済み外部 IP を持つ WSL（local）のみ**
- CI（GitHub-hosted 動的 IP）での楽天 live 呼出は **引き続き禁止**
- 意図的な rate limit（429）誘発は現状不要（既存方針維持）

---

## 3. human-decision として記録する理由

- QPS・接続元 IP は規約・コスト・API 停止リスクに関わる Human 判断事項である
- 本番 egress は横断の基盤設計であり、今は Backlog に落とす明示が必要
- #1603 の scope（正式 Batch 仕様の独断更新禁止）と、後続 Task 境界を固定するため

---

## 4. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| #1603 / PoC | 検証計画・ハーネスに QPS=8・IP 必須を反映 | 本決定後に実施 |
| 別 Task | `MOD-BATCH-008` Rate Limiter 本実装（目標 QPS=8、ハードキャップ 10） | 未起票 |
| Backlog | 本番（および将来の固定 egress 実行基盤）の IP 登録・NAT / self-hosted 等の設計 | **未検討・Backlog のみ** |

---

## 5. 参照

- `docs/90_PoC/外部API疎通検証/楽天API疎通検証計画.md`
- `docs/05_アプリケーション設計/アプリ/batch/バッチ外部API本実装ギャップ一覧.md`
- `scripts/batch/rakuten_live_verify.py`
