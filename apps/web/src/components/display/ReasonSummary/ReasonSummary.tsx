import { cn } from "@/lib/cn";

export type ReasonSummaryProps = {
  text: string;
  className?: string;
};

export function ReasonSummary({ text, className }: ReasonSummaryProps) {
  return (
    <p className={cn("line-clamp-2 text-small text-text-secondary", className)}>
      {text}
    </p>
  );
}
