import Link from "next/link";

import { Heading } from "@/components/display/Heading";
import { Text } from "@/components/display/Text";
import { Container } from "@/components/layout/Container";
import { cn } from "@/lib/cn";

import {
  CTA_LABEL,
  NOTICE_EXTERNAL_EC,
  PAGE_CATCHCOPY,
  PAGE_DESCRIPTION,
  PAGE_SERVICE_NAME,
  RECOMMENDATIONS_HREF,
} from "./constants";

/**
 * SCR-001 トップ画面。
 * 主 CTA は SCR-002（/recommendations）へ遷移する。
 */
export function HomePage() {
  return (
    <main>
      <Container className="py-12">
        <Heading level={1}>{PAGE_SERVICE_NAME}</Heading>
        <Text className="mt-4 text-text">{PAGE_CATCHCOPY}</Text>
        <Text className="mt-3 max-w-2xl text-text-secondary">
          {PAGE_DESCRIPTION}
        </Text>
        <div className="mt-8">
          <Link
            href={RECOMMENDATIONS_HREF}
            className={cn(
              "inline-flex h-12 items-center justify-center gap-2 rounded-sm px-6 text-body font-medium transition-colors",
              "bg-primary text-on-primary hover:bg-primary-hover",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
            )}
          >
            {CTA_LABEL}
          </Link>
        </div>
        <Text className="mt-6 text-small text-text-muted">
          {NOTICE_EXTERNAL_EC}
        </Text>
      </Container>
    </main>
  );
}
