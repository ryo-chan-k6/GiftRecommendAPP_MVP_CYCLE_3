import type { HTMLAttributes, ReactNode } from "react";

import { MorphingIndicator } from "@/components/feedback/MorphingIndicator";
import { Text } from "@/components/display/Text";
import { cn } from "@/lib/cn";

export type LoadingPanelProps = {
  message?: string;
  children?: ReactNode;
} & HTMLAttributes<HTMLDivElement>;

export function LoadingPanel({
  message = "推薦を実行しています",
  className,
  children,
  ...props
}: LoadingPanelProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 py-16 text-center",
        className,
      )}
      role="status"
      aria-live="polite"
      {...props}
    >
      <MorphingIndicator />
      <Text className="text-text-secondary">{message}</Text>
      {children}
    </div>
  );
}
