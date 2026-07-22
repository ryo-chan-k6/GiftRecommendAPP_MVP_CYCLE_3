# TV-009: Feature生成性能

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 検証ID | TV-009 |
| 検証名 | Feature生成性能 |
| 定義正本 | [全体テスト計画書](../../../05_アプリケーション設計/テスト/全体テスト計画書.md) §7.1.2 |
| 全体計画 | [技術検証全体計画](../技術検証全体計画.md) |
| 進捗 | [TV進捗一覧](../../管理/TV進捗一覧.md) |
| 結果の既定置き場 | `docs/90_PoC/性能フィジビリティ/` |
| 結果 | [Feature生成性能検証結果_TV-009](../../性能フィジビリティ/Feature生成性能検証結果_TV-009.md) |

---

## 2. 要件（確認すること）

| 観点 | 内容 |
| ---- | ---- |
| 主な確認内容 | User / Item Feature生成時間 |
| 判断結果の反映先 | shared_logic設計、Online / Batch責務 |

開始・終了条件の共通枠は全体テスト計画書 §7.1.4 / §7.1.5 に従う。

---

## 3. 実施方針

段階は全体計画 §5（S0〜S4）に従う。

| 段階 | 本TVでの実施内容 | 状態（2026-07-23） |
| ---- | ---------------- | ------------------ |
| S0 | 既存 Issue / スクリプト / 結果の有無を棚卸し | 完了 |
| S1 | 判断基準具体化（Feature 単体 vs TV-007 合算） | 完了 |
| S2 | `feature_generation_bench.py`（in-memory） | 完了 |
| S3 | local 実行・結果記録 | 完了（暫定 **Go**） |
| S4 | 設計反映メモ。正式 docs は別 Task | 完了（メモ作成） |

- Online: `UserFeatureGenerator`。Item: `ItemFeatureGenerator`（Batch ジョブ全体は非必須）。
- `apps/batch/**` は改修しない。

---

## 4. 検証方針

| 項目 | 方針 |
| ---- | ---- |
| 環境 | local。production 禁止 |
| データ | in-memory fixture。個人情報・本番データを使わない |
| 記録 | p50/p95、経路区分。secret 実値は記録しない |
| CI | 通常 PR CI の必須ゲートにしない |
| 判定 | Go / Adjust / Block を明記 |

---

## 5. 関連Issue / 成果物

| 種別 | 状態（2026-07-23） |
| ---- | ------------------ |
| Epic | [#1578](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1578) |
| Task | [#1580](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1580) |
| 結果レポート | [Feature生成性能検証結果_TV-009](../../性能フィジビリティ/Feature生成性能検証結果_TV-009.md) |
| ハーネス | `scripts/perf/feature_generation_bench.py` |

---

## 6. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-21 | 初版方針（#1496） |
| 2026-07-23 | S0〜S4 実施・結果 doc 反映（#1580） |
