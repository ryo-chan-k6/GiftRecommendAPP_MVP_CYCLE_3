import type { HTMLAttributes, ReactNode } from "react";

import { Heading } from "@/components/display/Heading";
import { Text } from "@/components/display/Text";
import { cn } from "@/lib/cn";

export type FormSectionProps = {
  title: string;
  description?: string;
  children: ReactNode;
} & HTMLAttributes<HTMLElement>;

export function FormSection({
  title,
  description,
  className,
  children,
  ...props
}: FormSectionProps) {
  return (
    <section className={cn("flex flex-col gap-4", className)} {...props}>
      <div>
        <Heading level={3}>{title}</Heading>
        {description ? (
          <Text className="mt-1 text-text-secondary">{description}</Text>
        ) : null}
      </div>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}
