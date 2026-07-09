import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

export type NumberInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type">;

export function NumberInput({ className, ...props }: NumberInputProps) {
  return (
    <input
      type="number"
      className={cn(
        "w-full rounded-md border border-border bg-surface px-3 py-2 text-body text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
