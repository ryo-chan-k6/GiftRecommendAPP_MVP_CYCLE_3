import type { HTMLAttributes, ReactNode } from "react";

import { Heading } from "@/components/display/Heading";
import { Text } from "@/components/display/Text";
import { cn } from "@/lib/cn";

export type SectionProps = {
  title: string;
  description?: string;
  children: ReactNode;
} & HTMLAttributes<HTMLElement>;

export function Section({
  title,
  description,
  className,
  children,
  ...props
}: SectionProps) {
  return (
    <section className={cn("flex flex-col gap-4", className)} {...props}>
      <div>
        <Heading level={2}>{title}</Heading>
        {description ? (
          <Text className="mt-2 text-text-secondary">{description}</Text>
        ) : null}
      </div>
      <div>{children}</div>
    </section>
  );
}
