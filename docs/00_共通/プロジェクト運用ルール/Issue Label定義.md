## Issue Labels定義

### 1. 作業単位：`unit:*`

| Label name   | Color     | Description               |
| ------------ | --------- | ------------------------- |
| `unit: epic` | `#1D76DB` | 複数のtaskを束ねる親Issue |
| `unit: task` | `#54AEFF` | 実作業単位のIssue         |

### 2. 作業種別：`type:*`

| Label name       | Color     | Description                |
| ---------------- | --------- | -------------------------- |
| `type: feature`  | `#0E8A16` | 新機能・新規成果物の追加   |
| `type: fix`      | `#D73A4A` | 不具合修正                 |
| `type: docs`     | `#0075CA` | ドキュメント作成・修正     |
| `type: refactor` | `#5319E7` | 振る舞いを変えない内部改善 |
| `type: chore`    | `#C5DEF5` | 設定・雑務・運用補助       |
| `type: test`     | `#FBCA04` | テスト作成・修正           |
| `type: hotfix`   | `#B60205` | 本番影響のある緊急修正     |
| `type: spike`    | `#D4C5F9` | 調査・検証・技術検証       |

### 3. 対象領域：`area:*`

| Label name      | Color     | Description                                |
| --------------- | --------- | ------------------------------------------ |
| `area: web`     | `#BFDADC` | Web / Next.js / UI領域                     |
| `area: api`     | `#BFD4F2` | API / Express / Backend API領域            |
| `area: reco`    | `#C2E0C6` | Recommendation / FastAPI / 推薦処理領域    |
| `area: batch`   | `#F9D0C4` | Batch / ETL / 定期処理領域                 |
| `area: db`      | `#D4C5F9` | DB / schema / migration領域                |
| `area: docs`    | `#DDEEFF` | docs成果物・設計書領域                     |
| `area: infra`   | `#FEF2C0` | CI/CD / hosting / env / infrastructure領域 |
| `area: project` | `#EDEDED` | Issue / Projects / GitHub運用領域          |

### 4. 優先度：`priority:*`

| Label name         | Color     | Description              |
| ------------------ | --------- | ------------------------ |
| `priority: high`   | `#D93F0B` | 優先度高。早期対応が必要 |
| `priority: medium` | `#FBCA04` | 優先度中。通常優先度     |
| `priority: low`    | `#C2E0C6` | 優先度低。後回し可能     |

### 5. 作業主体・レビュー補助

| Label name   | Color     | Description                         |
| ------------ | --------- | ----------------------------------- |
| `ai-agent`   | `#7057FF` | AIエージェント主導で作業するIssue   |
| `human-led`  | `#BFDADC` | 人主導で作業するIssue               |
| `blocked`    | `#000000` | 依存・未決事項により作業停止中      |
| `risk: high` | `#B60205` | 影響範囲または失敗リスクが高いIssue |
| `no-branch`  | `#E4E669` | ブランチ自動作成の対象外Issue       |

## 必須付与ルール

Issue作成時は原則として、以下を必ず1つずつ付与します。

```
unit: epic / unit: task
type: *
area: *
priority: *
```

AI作業対象の場合は追加で：

```
ai-agent
```

人主導の場合は：

```
human-led
```

## 例

```
unit: task
type: docs
area: project
priority: medium
human-led
```

AI開発タスクなら：

```
unit: task
type: feature
area: api
priority: high
ai-agent
```

## 色設計の考え方

```
unit      = 青系
type      = 機能別に強めの色
area      = 淡色系
priority  = 赤/黄/緑
補助      = 紫・黒・黄など目立つ色
```
