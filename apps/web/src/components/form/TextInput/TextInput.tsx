import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

const inputClassName =
  "w-full rounded-md border border-border bg-surface px-3 py-2 text-body text-text placeholder:text-text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-60";

export type TextInputProps = InputHTMLAttributes<HTMLInputElement>;

export function TextInput({ className, type = "text", ...props }: TextInputProps) {
  return <input type={type} className={cn(inputClassName, className)} {...props} />;
}
