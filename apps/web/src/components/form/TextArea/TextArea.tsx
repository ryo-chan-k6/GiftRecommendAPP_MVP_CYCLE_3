import type { TextareaHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

const textareaClassName =
  "min-h-[120px] w-full rounded-md border border-border bg-surface px-3 py-2 text-body text-text placeholder:text-text-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-60";

export type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export function TextArea({ className, ...props }: TextAreaProps) {
  return <textarea className={cn(textareaClassName, className)} {...props} />;
}
