# Style Guide Preview（Phase4a）

W3 トークン・部品スタイルをブラウザで確認するための**静的プレビュー**です。本番ルーティング（`src/app/**`）とは独立しています。

## 含まれるもの

| ファイル | 内容 |
| -------- | ---- |
| `style-guide.html` | カラー・タイポ・余白・ボタン・カード等のサンプル |
| `style-guide.css` | プレビュー用スタイル（`:root` は `../globals.css` と同期） |
| `serve.mjs` | ローカル確認用の最小 HTTP サーバー |

## 見方

### 推奨: ローカルサーバー

```bash
cd apps/web
pnpm preview:style-guide
```

ブラウザで http://localhost:3099/style-guide.html を開く。

### 代替: ファイル直開き

`style-guide.html` をブラウザで直接開いても可（Google Fonts は CDN から読み込み）。

## 位置づけ

- **正本**: `tokens/` + `docs/.../デザインルール.md`
- **本プレビュー**: 人間確認・デザインすり合わせ用。Phase4b で Next.js 画面へ置き換え可能
- **W2 以降**: 共通 UI コンポーネント実装後、本ページへ部品サンプルを追記するか、Vitest + Storybook 相当へ移行を検討
