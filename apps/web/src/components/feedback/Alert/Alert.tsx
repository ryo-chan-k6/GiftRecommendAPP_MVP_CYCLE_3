import type { HTMLAttributes, ReactNode } from "react";

import type { AlertVariant } from "@/components/types";
import { cn } from "@/lib/cn";

export type AlertProps = {
  variant?: AlertVariant;
  title?: string;
  children: ReactNode;
} & HTMLAttributes<HTMLDivElement>;

const variantClasses: Record<AlertVariant, string> = {
  info: "border-border bg-surface-muted text-text",
  warning: "border-warning bg-surface-muted text-text",
  error: "border-error bg-surface text-text",
};

export function Alert({
  variant = "info",
  title,
  className,
  children,
  role = "alert",
  ...props
}: AlertProps) {
  return (
    <div
      role={role}
      className={cn(
        "rounded-md border px-4 py-3 text-body",
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {title ? <p className="mb-1 font-semibold">{title}</p> : null}
      <div>{children}</div>
    </div>
  );
}
