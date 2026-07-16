# Lane 1e D1 residual: SCR-001 HomePage `reading 'call'`

| 項目 | 内容 |
| ---- | ---- |
| Date | 2026-07-16 |
| Issue | #1346 |
| Epic | #1344 |
| Related | D1 #1330 S1 residual |

## 事実

- `/` で Application error: `Cannot read properties of undefined (reading 'call')`
- Next overlay: `src/features/home/HomePage.tsx (31:11) @ HomePage`（`<Link>`）
- `/recommendations` は同環境で正常表示
- 修正後（native `<a href="/recommendations">`）: `http://localhost:3010/` が例外なく表示され、CTA で SCR-002 へ遷移

## 修正

- `HomePage` の主 CTA を `next/link` から native `<a>` に変更（仕様「Link 等」）
- component UT 継続（`role=link` / `href`）

## 未実施

- develop 上の既存 `:3000` プロセスでの再確認（worktree `:3010` で確認済）
