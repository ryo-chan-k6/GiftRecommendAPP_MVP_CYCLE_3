import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

export type ButtonProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export type FormFieldProps = {
  label: string;
  required?: boolean;
  helperText?: string;
  error?: string;
  children: ReactNode;
  htmlFor?: string;
};

export type AlertVariant = "info" | "warning" | "error";

export type HeadingLevel = 1 | 2 | 3 | 4 | 5 | 6;

export type ModalProps = {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
};

/** RecommendationCard 骨格用の最小商品型（Phase4b API 型とは別） */
export type RecommendationItemStub = {
  id: string;
  name: string;
  imageUrl?: string;
  priceYen?: number;
};
