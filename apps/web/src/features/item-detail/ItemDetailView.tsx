"use client";

import { useId, useState } from "react";

import { Button } from "@/components/action/Button";
import { PriceDisplay } from "@/components/display/PriceDisplay";
import { RankBadge } from "@/components/display/RankBadge";
import { ReasonSummary } from "@/components/display/ReasonSummary";
import { Text } from "@/components/display/Text";
import { Alert } from "@/components/feedback/Alert";
import { ExternalLink } from "@/components/nav/ExternalLink";
import { FeedbackInputModal } from "@/features/feedback-input";
import { FEEDBACK_UNAVAILABLE_HINT } from "@/features/feedback-input/constants";
import { isSafeExternalUrl } from "@/features/recommendation-result/is-safe-external-url";
import type {
  PublicItemDetail,
  PublicRecommendationResultItem,
} from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

import {
  DESCRIPTION_COLLAPSE_THRESHOLD,
  DESCRIPTION_TOGGLE_CLOSED,
  DESCRIPTION_TOGGLE_OPEN,
  EXTERNAL_EC_LABEL,
  FALLBACK_REASON_HINT,
  FEEDBACK_LABEL,
  REASON_DETAIL_DISABLED_HINT,
  REASON_DETAIL_LABEL,
} from "./constants";

export type ItemDetailViewProps = {
  item: PublicItemDetail;
  context: PublicRecommendationResultItem | null;
  /** fromResultId。文脈 Item があるときのみ Feedback 送信可 */
  resultId?: string | null;
};

export function ItemDetailView({
  item,
  context,
  resultId,
}: ItemDetailViewProps) {
  const description = item.itemDescription?.trim() ?? "";
  const collapse =
    description.length > DESCRIPTION_COLLAPSE_THRESHOLD;
  const [descriptionOpen, setDescriptionOpen] = useState(!collapse);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const canOpenFeedback = Boolean(
    resultId && context?.recommendationResultItemId,
  );
  const descriptionId = useId();
  const safeExternal = isSafeExternalUrl(item.itemUrl);
  const badges = (context?.reasonBadges ?? [])
    .map((badge) => badge.label?.trim())
    .filter((label): label is string => Boolean(label));

  const review = item.reviewSummary;
  const reviewLabel =
    review && typeof review.average === "number"
      ? `レビュー ${review.average.toFixed(1)}${
          typeof review.count === "number" ? `（${review.count}件）` : ""
        }`
      : null;

  return (
    <div className="flex flex-col gap-6">
      <section className="flex flex-col gap-3" aria-label="商品情報">
        {item.itemImageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- 外部EC画像。ドメイン allowlist は後続で検討
          <img
            src={item.itemImageUrl}
            alt={item.itemName}
            className="aspect-[4/3] w-full max-w-md rounded-md bg-surface-muted object-cover"
          />
        ) : (
          <div
            className="aspect-[4/3] w-full max-w-md rounded-md bg-surface-muted"
            role="img"
            aria-label="画像なし"
          />
        )}

        <h2 className="font-heading text-h2 text-text">{item.itemName}</h2>

        {item.itemCatchcopy ? (
          <Text className="text-text-secondary">{item.itemCatchcopy}</Text>
        ) : null}

        <PriceDisplay amountYen={item.itemPrice} />

        {reviewLabel ? (
          <Text className="text-small text-text-secondary">{reviewLabel}</Text>
        ) : null}

        <div className="flex flex-wrap items-center gap-2">
          {item.genreName ? (
            <Text className="text-small text-text-muted">{item.genreName}</Text>
          ) : null}
          {item.popularityBadge?.label ? (
            <span className="rounded-sm bg-surface-muted px-2 py-0.5 text-small text-text-secondary">
              {item.popularityBadge.label}
            </span>
          ) : null}
        </div>

        {description ? (
          <div>
            <Text
              id={descriptionId}
              className={
                !descriptionOpen
                  ? "line-clamp-8 whitespace-pre-wrap"
                  : "whitespace-pre-wrap"
              }
            >
              {description}
            </Text>
            {collapse ? (
              <button
                type="button"
                className="mt-2 text-small font-medium text-primary underline-offset-2 hover:underline"
                aria-expanded={descriptionOpen}
                aria-controls={descriptionId}
                onClick={() => setDescriptionOpen((value) => !value)}
              >
                {descriptionOpen
                  ? DESCRIPTION_TOGGLE_OPEN
                  : DESCRIPTION_TOGGLE_CLOSED}
              </button>
            ) : null}
          </div>
        ) : null}
      </section>

      {context ? (
        <section
          className="flex flex-col gap-2 border-t border-border pt-4"
          aria-label="推薦文脈"
        >
          <div className="flex items-center gap-2">
            <RankBadge rank={context.rank} />
            <Text className="text-small text-text-secondary">
              推薦順位: {context.rank} 位
            </Text>
          </div>
          {context.reasonSummary ? (
            <ReasonSummary text={context.reasonSummary} />
          ) : null}
          {badges.length > 0 ? (
            <ul className="flex flex-wrap gap-2" aria-label="推薦理由バッジ">
              {badges.map((label) => (
                <li
                  key={label}
                  className="rounded-sm bg-surface-muted px-2 py-0.5 text-small text-text-secondary"
                >
                  {label}
                </li>
              ))}
            </ul>
          ) : null}
          {context.cautionNote ? (
            <Alert variant="warning" title="注意">
              {context.cautionNote}
            </Alert>
          ) : null}
          {context.isFallback ? (
            <Text className="text-small text-text-muted">
              {FALLBACK_REASON_HINT}
            </Text>
          ) : null}
        </section>
      ) : null}

      <section className="flex flex-col gap-3" aria-label="操作">
        {safeExternal ? (
          <ExternalLink href={item.itemUrl}>{EXTERNAL_EC_LABEL}</ExternalLink>
        ) : null}
        <div className="flex flex-col gap-0.5">
          <Button type="button" variant="secondary" size="sm" disabled>
            {REASON_DETAIL_LABEL}
          </Button>
          <span className="text-small text-text-muted">
            {REASON_DETAIL_DISABLED_HINT}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={!canOpenFeedback}
            onClick={() => {
              if (canOpenFeedback) {
                setFeedbackOpen(true);
              }
            }}
          >
            {FEEDBACK_LABEL}
          </Button>
          {!canOpenFeedback ? (
            <span className="text-small text-text-muted">
              {FEEDBACK_UNAVAILABLE_HINT}
            </span>
          ) : null}
        </div>
      </section>

      {canOpenFeedback && resultId && context ? (
        <FeedbackInputModal
          open={feedbackOpen}
          onClose={() => setFeedbackOpen(false)}
          resultId={resultId}
          resultItemId={context.recommendationResultItemId}
          itemName={item.itemName}
          sourcePage="SCR-006"
        />
      ) : null}
    </div>
  );
}
