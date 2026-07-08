import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

export type ContainerProps = {
  maxWidth?: "md" | "lg";
  children: ReactNode;
} & HTMLAttributes<HTMLDivElement>;

const maxWidthClasses = {
  md: "max-w-screen-md",
  lg: "max-w-screen-lg",
} as const;

export function Container({
  maxWidth = "lg",
  className,
  children,
  ...props
}: ContainerProps) {
  return (
    <div
      className={cn(
        "mx-auto w-full px-4 md:px-6",
        maxWidthClasses[maxWidth],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
