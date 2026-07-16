"use client";

import { useId, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/action/Button";
import { PriceDisplay } from "@/components/display/PriceDisplay";
import { RankBadge } from "@/components/display/RankBadge";
import { ReasonSummary } from "@/components/display/ReasonSummary";
import { Text } from "@/components/display/Text";
import { ExternalLink } from "@/components/nav/ExternalLink";
import { FeedbackInputModal } from "@/features/feedback-input";
import type { PublicRecommendationResultItem } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

import {
  DETAIL_TOGGLE_CLOSED,
  DETAIL_TOGGLE_OPEN,
  EXTERNAL_EC_LABEL,
  FALLBACK_REASON_HINT,
  FEEDBACK_LABEL,
  ITEM_DETAIL_LABEL,
  buildItemDetailHref,
} from "./constants";
import { isSafeExternalUrl } from "./is-safe-external-url";
import { ReasonDetailPanel } from "./ReasonDetailPanel";

export type RecommendationResultItemProps = {
  item: PublicRecommendationResultItem;
  resultId: string;
};

export function RecommendationResultItem({
  item,
  resultId,
}: RecommendationResultItemProps) {
  const [open, setOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const panelId = useId();
  const badges = (item.reasonBadges ?? [])
    .map((badge) => badge.label?.trim())
    .filter((label): label is string => Boolean(label));
  const safeExternal = isSafeExternalUrl(item.itemUrl);
  const detailHref = buildItemDetailHref(item.itemId, resultId);

  return (
    <article className="flex flex-col gap-3 border-b border-border py-6 last:border-b-0">
      <div className="flex items-start gap-3">
        <RankBadge rank={item.rank} />
        <div className="min-w-0 flex-1">
          <h2 className="font-heading text-h3 text-text">{item.itemName}</h2>
          {item.itemCatchcopy ? (
            <Text className="mt-1 text-text-secondary">{item.itemCatchcopy}</Text>
          ) : null}
        </div>
        <PriceDisplay amountYen={item.itemPrice} className="shrink-0" />
      </div>

      {item.itemImageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element -- 外部EC画像。next/image ドメイン設定は後続で検討
        <img
          src={item.itemImageUrl}
          alt={item.itemName}
          className="aspect-[4/3] w-full max-w-md rounded-md bg-surface-muted object-cover"
        />
      ) : (
        <div
          className="aspect-[4/3] w-full max-w-md rounded-md bg-surface-muted"
          aria-hidden
        />
      )}

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

      {item.reasonSummary ? (
        <ReasonSummary text={item.reasonSummary} />
      ) : null}

      {item.isFallback ? (
        <Text className="text-small text-text-muted">{FALLBACK_REASON_HINT}</Text>
      ) : null}

      <div>
        <button
          type="button"
          className="text-small font-medium text-primary underline-offset-2 hover:underline"
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? DETAIL_TOGGLE_OPEN : DETAIL_TOGGLE_CLOSED}
        </button>
        {open ? <ReasonDetailPanel item={item} panelId={panelId} /> : null}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Link
          href={detailHref}
          className="text-small font-medium text-primary underline-offset-2 hover:underline"
        >
          {ITEM_DETAIL_LABEL}
        </Link>
        {safeExternal ? (
          <ExternalLink href={item.itemUrl}>{EXTERNAL_EC_LABEL}</ExternalLink>
        ) : null}
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setFeedbackOpen(true)}
        >
          {FEEDBACK_LABEL}
        </Button>
      </div>

      <FeedbackInputModal
        open={feedbackOpen}
        onClose={() => setFeedbackOpen(false)}
        resultId={resultId}
        resultItemId={item.recommendationResultItemId}
        itemName={item.itemName}
        sourcePage="SCR-004"
      />
    </article>
  );
}
