"use client";

import type { ButtonProps } from "@/components/types";
import { Spinner } from "@/components/feedback/Spinner";
import { cn } from "@/lib/cn";

const variantClasses: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-primary text-on-primary hover:bg-primary-hover disabled:opacity-60",
  secondary:
    "border border-border bg-surface text-text hover:bg-surface-muted disabled:opacity-60",
  ghost: "bg-transparent text-text-secondary hover:text-text disabled:opacity-60",
  danger: "bg-error text-on-primary hover:opacity-90 disabled:opacity-60",
};

const sizeClasses: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "h-8 px-3 text-small",
  md: "h-10 px-4 text-body",
  lg: "h-12 px-6 text-body",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className,
  children,
  type = "button",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      disabled={isDisabled}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-sm font-medium transition-colors",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
        "disabled:cursor-not-allowed",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {loading ? <Spinner size="sm" label="読み込み中" /> : null}
      {children}
    </button>
  );
}
