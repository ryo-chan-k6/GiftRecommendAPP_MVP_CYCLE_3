import { Button } from "@/components/action/Button";
import { EmptyState } from "@/components/feedback/EmptyState";
import { PageLayout } from "@/components/layout/PageLayout";
import { TextLink } from "@/components/nav/TextLink";

import { EMPTY_RESULT_MESSAGE } from "./constants";

export type RecommendationEmptyPanelProps = {
  onChangeConditions: () => void;
};

/**
 * SCR-009: 0件結果表示（宿主 RecommendationInputPage の empty phase）。
 * 再検索専用 CTA は MVP 非採用。API displayMessage は使わずクライアント定数を正本とする。
 */
export function RecommendationEmptyPanel({
  onChangeConditions,
}: RecommendationEmptyPanelProps) {
  return (
    <PageLayout title="おすすめが見つかりませんでした">
      <EmptyState
        title="条件に合うギフトがありません"
        description={EMPTY_RESULT_MESSAGE}
        action={
          <div className="flex flex-col items-center gap-3">
            <Button variant="secondary" onClick={onChangeConditions}>
              条件を変更する
            </Button>
            <TextLink href="/">トップへ戻る</TextLink>
          </div>
        }
      />
    </PageLayout>
  );
}
