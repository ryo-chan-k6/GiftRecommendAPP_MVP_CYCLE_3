import type { HTMLAttributes, ReactNode } from "react";

import { Container } from "@/components/layout/Container";
import { Heading } from "@/components/display/Heading";
import { cn } from "@/lib/cn";

export type PageLayoutProps = {
  title?: string;
  showHeader?: boolean;
  children: ReactNode;
} & HTMLAttributes<HTMLDivElement>;

export function PageLayout({
  title,
  showHeader = true,
  className,
  children,
  ...props
}: PageLayoutProps) {
  return (
    <div className={cn("min-h-screen", className)} {...props}>
      {showHeader && title ? (
        <header className="border-b border-border bg-surface">
          <Container className="py-4">
            <Heading level={1}>{title}</Heading>
          </Container>
        </header>
      ) : null}
      <Container className="py-8">{children}</Container>
    </div>
  );
}
