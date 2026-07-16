"use client";

import { cn } from "@/lib/cn";

import styles from "./MorphingIndicator.module.css";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

export type MorphingIndicatorProps = {
  className?: string;
  /** テスト用。指定時は matchMedia より優先する */
  reducedMotion?: boolean;
};

/**
 * LoadingPanel（UI-032）向けの幾何学的モーフィングインジケータ。
 * UI-031 Spinner（インライン用）とは責務を分ける。
 */
export function MorphingIndicator({
  className,
  reducedMotion,
}: MorphingIndicatorProps) {
  const prefersReduced = usePrefersReducedMotion();
  const reduced = reducedMotion ?? prefersReduced;

  return (
    <span
      aria-hidden="true"
      data-testid="morphing-indicator"
      data-motion={reduced ? "reduced" : "full"}
      className={cn(
        styles.indicator,
        reduced ? styles.reduced : null,
        className,
      )}
    />
  );
}
