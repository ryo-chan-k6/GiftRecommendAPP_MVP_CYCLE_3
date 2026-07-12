import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind クラス名を安全に結合する */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
