import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

const selectClassName =
  "w-full rounded-md border border-border bg-surface px-3 py-2 text-body text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-60";

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export function Select({ className, children, ...props }: SelectProps) {
  return (
    <select className={cn(selectClassName, className)} {...props}>
      {children}
    </select>
  );
}
