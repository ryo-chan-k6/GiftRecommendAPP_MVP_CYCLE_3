import Link from "next/link";

import { cn } from "@/lib/cn";

export type BackLinkProps = {
  href: string;
  children?: React.ReactNode;
  className?: string;
};

export function BackLink({
  href,
  children = "戻る",
  className,
}: BackLinkProps) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center gap-1 text-small text-text-secondary hover:text-text",
        className,
      )}
    >
      ← {children}
    </Link>
  );
}
