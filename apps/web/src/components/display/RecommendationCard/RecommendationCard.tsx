"use client";

import type { HTMLAttributes } from "react";

import type { RecommendationItemStub } from "@/components/types";
import { Card } from "@/components/display/Card";
import { PriceDisplay } from "@/components/display/PriceDisplay";
import { RankBadge } from "@/components/display/RankBadge";
import { ReasonSummary } from "@/components/display/ReasonSummary";
import { cn } from "@/lib/cn";

export type RecommendationCardProps = {
  item: RecommendationItemStub;
  rank?: number;
  reasonSummary?: string;
  onSelect?: () => void;
  onOpenReason?: () => void;
} & HTMLAttributes<HTMLDivElement>;

export function RecommendationCard({
  item,
  rank,
  reasonSummary,
  onSelect,
  onOpenReason,
  className,
  ...props
}: RecommendationCardProps) {
  return (
    <Card
      className={cn("flex flex-col gap-3 transition-shadow hover:shadow-md", className)}
      {...props}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-2">
          {rank !== undefined ? <RankBadge rank={rank} /> : null}
          <h3 className="font-heading text-h3 text-text">{item.name}</h3>
        </div>
        {item.priceYen !== undefined ? (
          <PriceDisplay amountYen={item.priceYen} />
        ) : null}
      </div>
      {item.imageUrl ? (
        // eslint-disable-next-line @next/next/no-img-element -- Phase4a 骨格。next/image は Phase4b で検討
        <img
          src={item.imageUrl}
          alt={item.name}
          className="aspect-[4/3] w-full rounded-md bg-surface-muted object-cover"
        />
      ) : (
        <div
          className="aspect-[4/3] w-full rounded-md bg-surface-muted"
          aria-hidden
        />
      )}
      {reasonSummary ? <ReasonSummary text={reasonSummary} /> : null}
      <div className="flex gap-2">
        {onSelect ? (
          <button
            type="button"
            onClick={onSelect}
            className="text-small font-medium text-primary underline-offset-2 hover:underline"
          >
            詳細を見る
          </button>
        ) : null}
        {onOpenReason ? (
          <button
            type="button"
            onClick={onOpenReason}
            className="text-small text-text-secondary underline-offset-2 hover:underline"
          >
            推薦理由
          </button>
        ) : null}
      </div>
    </Card>
  );
}
