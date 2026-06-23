import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

import type { HeadingLevel } from "@/components/types";

export type HeadingProps = {
  level?: HeadingLevel;
  children: ReactNode;
} & HTMLAttributes<HTMLHeadingElement>;

const levelClasses: Record<HeadingLevel, string> = {
  1: "font-heading text-h1 text-text",
  2: "font-heading text-h2 text-text",
  3: "font-heading text-h3 text-text",
  4: "font-heading text-h3 text-text",
  5: "font-heading text-body font-semibold text-text",
  6: "font-heading text-small font-semibold text-text",
};

const headingTags = {
  1: "h1",
  2: "h2",
  3: "h3",
  4: "h4",
  5: "h5",
  6: "h6",
} as const;

export function Heading({
  level = 2,
  className,
  children,
  ...props
}: HeadingProps) {
  const Tag = headingTags[level];

  return (
    <Tag className={cn(levelClasses[level], className)} {...props}>
      {children}
    </Tag>
  );
}
