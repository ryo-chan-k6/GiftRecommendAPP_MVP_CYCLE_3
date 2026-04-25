# Git運用手順書（標準フロー）

# 1. 全体フロー

```
1. Issue作成
2. ブランチ作成
3. 作業（設計 / 実装）
4. コミット（Cursor）
5. プッシュ
6. PR作成
7. セルフレビュー
8. developへマージ
9. mainへ反映
```

---

# 2. 手順詳細

---

## Step 1. Issue作成

### 目的

- 変更理由を明確化
- 作業単位の固定

### ルール

- 1 Issue = 1責務
- タイトルは具体的に

### 例

```
docs: ルートREADMEとapps READMEを整備
```

---

## Step 2. ブランチ作成

### ルール

```
<type>/issue-<番号>-<summary>
```

### 例

```
docs/issue-12-add-root-readme
```

---

### コマンド（ローカル）

```
git checkout develop
git pull
git checkout-b docs/issue-12-add-root-readme
```

---

## Step 3. 作業

- Cursorで実装 / docs修正
- 必ず docs と整合を取る

---

## Step 4. コミット（Cursor）

### 方法

1. Cursorの変更タブを開く
2. 「Generate Commit Message」クリック
3. 内容を軽く確認
4. Commit

---

### ルール

- 日本語
- 1コミット1責務
- 内容と一致

---

### 例

```
docs: ルートREADMEと各アプリREADMEを追加
```

---

## Step 5. プッシュ

```
git push origin docs/issue-12-add-root-readme
```

---

## Step 6. PR作成

### ベース

- base: `develop`
- compare: 作業ブランチ

---

### PRに必ず書く内容

```
## Issue
#12

## 目的
ルートREADMEと各アプリREADMEの整備

## 変更内容
- README.md追加
- apps配下README作成
- .gitignore追加

## 影響範囲
- docsのみ

## docs更新
あり

## 確認内容
- ファイル構成確認
- 内容レビュー済み

## 未対応
なし
```

---

## Step 7. セルフレビュー

### チェック項目

- docsと整合しているか
- 不要ファイル入ってないか
- 変更が1責務か
- commit messageが適切か

---

## Step 8. developへマージ

### 方法

- GitHubで **Squash Merge**

---

### 理由

- 履歴が綺麗になる
- PR単位で履歴が残る

---

## Step 9. mainへ反映

### 方法

```
git checkout main
git pull
git merge develop
git push origin main
```

または

- GitHubでPR（develop → main）
