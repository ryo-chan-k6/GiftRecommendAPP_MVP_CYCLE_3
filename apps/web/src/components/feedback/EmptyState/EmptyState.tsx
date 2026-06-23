import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

export type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
} & HTMLAttributes<HTMLDivElement>;

export function EmptyState({
  title,
  description,
  action,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-4 rounded-lg border border-border bg-surface px-6 py-12 text-center shadow-sm",
        className,
      )}
      {...props}
    >
      <h2 className="font-heading text-h2 text-text">{title}</h2>
      {description ? (
        <p className="max-w-md text-body text-text-secondary">{description}</p>
      ) : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
