import { LoadingPanel } from "@/components/feedback/LoadingPanel";
import { PageLayout } from "@/components/layout/PageLayout";
import { Text } from "@/components/display/Text";

import { RUNNING_MESSAGE, RUNNING_WAITING_MESSAGE } from "./constants";

/**
 * SCR-003: レコメンド実行中表示（宿主 RecommendationInputPage の running phase）。
 * キャンセル導線は MVP 対象外。
 */
export function RecommendationRunningPanel() {
  return (
    <PageLayout title="レコメンド実行中">
      <LoadingPanel message={RUNNING_MESSAGE}>
        <Text className="text-small text-text-muted">{RUNNING_WAITING_MESSAGE}</Text>
      </LoadingPanel>
    </PageLayout>
  );
}
