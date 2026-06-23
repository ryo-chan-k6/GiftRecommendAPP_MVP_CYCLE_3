import { cn } from "@/lib/cn";

export type InlineErrorProps = {
  message: string;
  className?: string;
};

export function InlineError({ message, className }: InlineErrorProps) {
  return (
    <p className={cn("text-small text-error", className)} role="alert">
      {message}
    </p>
  );
}
