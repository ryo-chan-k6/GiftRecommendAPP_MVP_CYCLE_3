"use client";

import { Text } from "@/components/display/Text";
import { Alert } from "@/components/feedback/Alert";
import type { PublicRecommendationResultItem } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";
import { cn } from "@/lib/cn";

import {
  CAUTION_ALERT_TITLE,
  DETAIL_EMPTY_GUIDE,
  REASON_DETAIL_MAX_HEIGHT_CLASS,
  REASON_POINTS_LIST_LABEL,
} from "./constants";

export type ReasonDetailPanelProps = {
  item: PublicRecommendationResultItem;
  panelId: string;
  className?: string;
};

function normalizePoints(points: string[] | undefined): string[] {
  if (!points?.length) {
    return [];
  }
  return points
    .map((point) => point.trim())
    .filter((point) => point.length > 0)
    .slice(0, 3);
}

function normalizeBadges(
  badges: PublicRecommendationResultItem["reasonBadges"],
): string[] {
  return (badges ?? [])
    .map((badge) => badge.label?.trim())
    .filter((label): label is string => Boolean(label));
}

/**
 * SCR-005: 推薦理由詳細の展開パネル。
 * 優先順位: reasonPoints → reasonDetail → cautionNote →（薄いとき）要約/バッジ再掲 → 案内文。
 */
export function ReasonDetailPanel({
  item,
  panelId,
  className,
}: ReasonDetailPanelProps) {
  const points = normalizePoints(item.reasonPoints);
  const detail = item.reasonDetail?.trim() ?? "";
  const caution = item.cautionNote?.trim() ?? "";
  const hasRichDetail = points.length > 0 || detail.length > 0;
  const badges = normalizeBadges(item.reasonBadges);
  const summary = item.reasonSummary?.trim() ?? "";
  const showRedisplay = !hasRichDetail;

  return (
    <div
      id={panelId}
      className={cn(
        "mt-2 overflow-y-auto rounded-md border border-border bg-surface p-3",
        REASON_DETAIL_MAX_HEIGHT_CLASS,
        className,
      )}
    >
      {points.length > 0 ? (
        <ul
          className="mb-2 list-disc space-y-1 pl-5 text-body text-text"
          aria-label={REASON_POINTS_LIST_LABEL}
        >
          {points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      ) : null}

      {detail ? <Text className="mb-2">{detail}</Text> : null}

      {caution ? (
        <Alert variant="warning" title={CAUTION_ALERT_TITLE} className="mb-3">
          {caution}
        </Alert>
      ) : null}

      {showRedisplay && summary ? (
        <Text className="mb-2">{summary}</Text>
      ) : null}

      {showRedisplay && badges.length > 0 ? (
        <ul className="mb-2 flex flex-wrap gap-2">
          {badges.map((label) => (
            <li
              key={`detail-${label}`}
              className="rounded-sm bg-surface-muted px-2 py-0.5 text-small text-text-secondary"
            >
              {label}
            </li>
          ))}
        </ul>
      ) : null}

      {showRedisplay ? (
        <Text className="text-small text-text-muted">{DETAIL_EMPTY_GUIDE}</Text>
      ) : null}
    </div>
  );
}
