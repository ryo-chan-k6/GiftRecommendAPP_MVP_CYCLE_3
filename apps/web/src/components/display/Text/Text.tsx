import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

export type TextProps = {
  children: ReactNode;
  as?: "p" | "span" | "div";
} & HTMLAttributes<HTMLElement>;

export function Text({
  as: Component = "p",
  className,
  children,
  ...props
}: TextProps) {
  return (
    <Component
      className={cn("text-body text-text", className)}
      {...props}
    >
      {children}
    </Component>
  );
}
