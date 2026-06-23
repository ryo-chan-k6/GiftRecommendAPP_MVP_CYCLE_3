import { cn } from "@/lib/cn";

export type ExternalLinkProps = {
  href: string;
  children: React.ReactNode;
  className?: string;
};

export function ExternalLink({ href, children, className }: ExternalLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "text-body font-medium text-primary underline-offset-2 hover:underline",
        className,
      )}
    >
      {children}
    </a>
  );
}
