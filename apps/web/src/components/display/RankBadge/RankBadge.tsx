import { cn } from "@/lib/cn";

export type RankBadgeProps = {
  rank: number;
  className?: string;
};

/** SCR-004 推薦結果一覧向けの順位表示（UI-044、MVP 対象） */
export function RankBadge({ rank, className }: RankBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex h-6 min-w-6 items-center justify-center rounded-sm bg-accent-light px-2 text-small font-semibold text-text",
        className,
      )}
      aria-label={`順位 ${rank}`}
    >
      {rank}
    </span>
  );
}
