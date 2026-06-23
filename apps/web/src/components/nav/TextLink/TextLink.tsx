import Link from "next/link";

import { cn } from "@/lib/cn";

export type TextLinkProps = {
  href: string;
  children: React.ReactNode;
  className?: string;
  external?: false;
};

export function TextLink({ href, children, className }: TextLinkProps) {
  return (
    <Link
      href={href}
      className={cn(
        "text-body text-text-secondary underline-offset-2 hover:text-text hover:underline",
        className,
      )}
    >
      {children}
    </Link>
  );
}
