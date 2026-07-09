import { cn } from "@/lib/cn";

export type SpinnerProps = {
  size?: "sm" | "md";
  label?: string;
  className?: string;
};

const sizeClasses = {
  sm: "h-4 w-4 border-2",
  md: "h-8 w-8 border-[3px]",
} as const;

export function Spinner({ size = "md", label = "読み込み中", className }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={cn(
        "inline-block animate-spin rounded-full border-primary border-t-transparent",
        sizeClasses[size],
        className,
      )}
    />
  );
}
