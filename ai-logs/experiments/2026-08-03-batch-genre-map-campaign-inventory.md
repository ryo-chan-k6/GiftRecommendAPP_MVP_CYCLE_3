# Experiment: external_genre inventory snapshot (genre map campaign)

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-03-batch-genre-map-campaign-inventory` |
| 種別 | experiment（集計メモ・secretなし） |
| 関連Issue | #1831 / 親Epic #1827 |
| 正本docs | `docs/15_運用・改善/運用手順/ジャンル地図キャンペーン_external_genre棚卸し.md` |
| 記録日 | 2026-08-03 |

## 要約（事実）

| 指標 | 値 |
| ---- | -- |
| total_rows | 15 |
| source | rakuten のみ |
| genre_level | 1→2件 / 2→13件 |
| is_leaf | false→2 / true→13 |
| root `0` | 未登録 |
| MVP 4ID | すべて present（置き換えない） |
| table total_relation_size | 80 kB |
| db_size | 27 MB |

詳細・再測手順・Human再測欄は正本docsを参照。本ログは通常作業の正本ではない。
