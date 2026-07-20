# Human Decision Log

## 1. 概要

| 項目          | 内容                  |
| ------------- | --------------------- |
| Log ID        | `2026-07-20-ui-e2e-required-promotion-plan` |
| Log種別       | `human-decision`      |
| 件名          | UI E2E（S1）の required 昇格方針: 段階昇格（案2）を採用し、gate ジョブ追加＋soak 後に Human が branch protection で昇格する |
| 発生日時      | 2026-07-20            |
| 記録日時      | 2026-07-20            |
| 発生元Command | required 昇格の検討（plan） |
| 発生元Agent   | `orchestrator-ai`     |
| workstream_key | `lane-1e-ui-e2e-required-prep` |
| 関連Issue     | #1471（本 Epic） / #1464（UI E2E CIゲート化・完了） |
| 関連PR        | #1465（方針B 導入・merged） / 本 Epic PR（作成後に確定） |
| Definition    | `prompts/definitions/epics/lane-1e-ui-e2e-required-prep/epic.yaml` |
| 重要度        | `medium`              |
| 状態          | `open`（gate ジョブ導入まで確定 / required 設定変更は soak 後の Human 判断待ち） |

---

## 2. 結論

**UI E2E（S1）の required 昇格は段階昇格（案2）を採用する。**

1. **gate ジョブ導入（本 Epic で実施）**: `test-ui-e2e.yml` に `ui-e2e-gate`（`needs: [decide, ui-e2e]` / `if: always()`）を追加する。将来 branch protection の required check には、skip し得る `UI E2E (S1)` ではなく **`UI E2E gate`** を指定する。
2. **対象ブランチ**: **develop**（Epic PR の target・現行運用に合致）。main は対象外。
3. **soak（安定性観測）基準**: **2 週間 かつ 10 PR で flake 0** を満たすまで required 昇格しない。
4. **required 昇格そのもの（branch protection 設定）は Human 判断・repo 設定**とし、本 Epic では実施しない。

---

## 3. human-decision として記録する理由

required 昇格は merge ゲートの強制力を変える運用判断であり、CI/CD 横断影響と開発速度・コストに影響する。AI は branch protection を変更できず（また変更すべきでなく）、判断材料と前提条件を正本化して Human 判断に引き渡す必要があるため。

### 3.1 記録対象理由

- required 化は Human 判断（AGENTS.md §23 / project-operation.mdc §3.4）に該当する
- gate ジョブ設計・soak 基準・対象ブランチという後続判断の前提を確定づける
- #1464 の out_of_scope（required 化）を引き継ぐ後続方針である

### 3.2 通常作業ログではない理由

merge ゲート方針の選択であり、branch protection・CI/CD・開発フローに横断影響するため。正本は本ログとし、AIログ運用ルール §13 に従う。

---

## 4. 発生経緯

| 項目                  | 内容                                   |
| --------------------- | -------------------------------------- |
| 発生元                | required 昇格の検討（#1465 merge 後）  |
| 関連Task              | #1471 `lane-1e-ui-e2e-required-prep`   |
| 関連Command           | 検討（plan）→ `/start-epic`（予定）    |

### 4.1 詳細

#1464（PR #1465 merged）で UI E2E S1 を段階導入（方針B: 主導線 path / ラベル `ui-e2e` / nightly / `workflow_dispatch`）した。Human から required 昇格の検討開始が指示され、選択肢を比較した結果、段階昇格（案2）・対象 develop・soak 2週間かつ10PR flake0 が選択された。

---

## 5. 選択肢と比較

| 案 | 内容 | 評価 |
| --- | ---- | ---- |
| 案1 | 即 required 化（`UI E2E (S1)` を指定） | skip 結論の曖昧さ・flake データ不足でロック多発の恐れ。不採用 |
| **案2（採用）** | gate ジョブ追加 → soak → Human が required 昇格 | 確実・安全。採用 |
| 案3 | required 化しない（nightly＋主導線 PR 可視化のみ） | デグレ検知が best-effort に留まる。将来の判断余地として保持 |

---

## 6. 技術的根拠（GitHub 挙動）

- 公式Docs（Troubleshooting required status checks / About status checks）:
  - workflow 自体が path/branch/commit filter で skip されると、required チェックは "Pending" のままブロックする。
  - ジョブが `if` 条件で skip された場合は "Success" 扱いで、required でもブロックしない。
  - 依存ジョブを required にする場合は `always()` ＋ `needs` を用いる。
- 現場報告（例: rjmurillo/ai-agents#1168）では skip 結論が詰まる事例もあり、確実策として **常に success/failure を返す gate ジョブ**を required 対象にするのが標準パターン。
- 本 workflow はトップレベル path filter を撤廃済みのため「Pending 固着」トラップは既に回避済み。残る曖昧さを gate ジョブで解消する。

---

## 7. Human 判断事項（未確定・引き渡し）

- soak 完了後に `UI E2E gate` を develop の required check に追加するか（GitHub UI / branch protection）
- soak 基準の最終承認（**2週間 かつ 10 PR で flake 0** を推奨）
- リポジトリに `ui-e2e` ラベルを作成するか（opt-in 強制実行用）
- （将来）main も required 対象に含めるか
- （将来）merge queue を採用する場合、`merge_group` トリガ追加が別途必要

---

## 8. 判断しない場合のリスク

- gate ジョブなしで required 化すると、skip 結論の扱いにより PR がロックされる・または false green を pass にする恐れがある。
- soak なしで required 化すると、E2E flake で develop への merge が不安定にブロックされる。
- 昇格を放置すると、UI 主導線 S1 のデグレ検知が best-effort（nightly / 主導線 PR 可視化）に留まる。
