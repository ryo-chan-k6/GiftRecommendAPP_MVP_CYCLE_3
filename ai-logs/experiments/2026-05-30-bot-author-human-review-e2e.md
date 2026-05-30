# bot author Human Review E2E

## 目的

`gift-recommend-ai-bot` の Classic PAT で PR を open し、`ryo-chan-k6` が Human Review（Approve / Request changes）できることを確認する。

## 手順

1. bot PAT（`GH_BOT_TOKEN`）で branch push
2. `gh pr create`（author = `gift-recommend-ai-bot`）
3. `ryo-chan-k6` で PR を開き Review changes → Approve / Request changes が選べること

## 後片付け

検証後、この PR は Close してよい（merge 不要）。
