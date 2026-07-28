# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| --- | --- |
| Log ID | `2026-07-28-upstash-redis-adoption` |
| Log種別 | `human-decision` |
| 件名 | MVP 簡易 stg / prod の Redis プロバイダとして Upstash を採用 |
| 発生日時 | 2026-07-28 |
| 記録日時 | 2026-07-28 |
| 確定日時 | 2026-07-28 |
| 発生元 | 簡易 stg 構築（#1686）作業中のプロバイダ選定。正本化は #1708（親 Epic #146） |
| 関連Issue | `#1708` / `#146` / `#1686` / `#144` |
| 重要度 | `high` |
| 状態 | `resolved` |
| 確定方式 | Human が候補比較後に Upstash を選択（チャット 2026-07-28） |

---

## 2. 背景

- local Redis は Docker compose で確定済み（2026-06-18）
- stg / prod の Redis **製品名**は未確定のまま「マネージド Redis」とだけ記載されていた
- API≈Render / Reco≈Fly のため、同一系 PaaS 付属 Redis だとクロスホスト接続になりやすい

---

## 3. 選択肢

| 案 | 概要 | 判定 |
| --- | --- | --- |
| **A. Upstash Redis** | サーバレス寄りのマネージド。Render/Fly 双方から同一 `REDIS_URL` を参照しやすい | **採用** |
| B. Render / Railway 付属 Redis | API と同系に寄せやすい。Reco=Fly 前提ではクロスプロバイダ | 不採用（当面） |
| C. Redis Cloud | 本家マネージド。安心感は高いが簡易 stg 着手には重い | 不採用（当面）。将来移行候補 |

---

## 4. 確定事項

| ID | 確定内容 |
| --- | --- |
| H-DEP-01 | MVP 簡易 stg および prod の Redis は **Upstash Redis** |
| H-DEP-02 | stg と prod で Upstash DB を **分離**。local は Docker のまま |
| H-DEP-03 | 同一環境の api / reco は **同一 `REDIS_URL`** |

正本反映先: [デプロイ設定書](../../docs/14_リリース/デプロイ設定/デプロイ設定書.md)（Task #1708 / Epic #146）

---

## 5. 判断しない場合のリスク（参考）

- 簡易 stg 構築（R1）でプロバイダが毎回揺れ、手順と実装が乖離する
- Render 付属に寄せると Fly Reco 側の到達性が後から問題になる

---

## 6. 改訂履歴

| 日付 | 内容 |
| --- | --- |
| 2026-07-28 | 初版。Upstash 採用を記録 |
