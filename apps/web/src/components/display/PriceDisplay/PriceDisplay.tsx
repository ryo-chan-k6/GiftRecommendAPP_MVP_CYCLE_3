import { cn } from "@/lib/cn";

export type PriceDisplayProps = {
  amountYen: number;
  maxYen?: number;
  className?: string;
};

function formatYen(value: number): string {
  return `¥${value.toLocaleString("ja-JP")}`;
}

export function PriceDisplay({ amountYen, maxYen, className }: PriceDisplayProps) {
  const label =
    maxYen !== undefined && maxYen !== amountYen
      ? `${formatYen(amountYen)}〜${formatYen(maxYen)}`
      : formatYen(amountYen);

  return <span className={cn("text-body font-medium text-text", className)}>{label}</span>;
}
