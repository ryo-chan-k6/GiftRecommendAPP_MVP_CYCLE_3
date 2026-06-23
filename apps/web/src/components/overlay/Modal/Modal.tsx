"use client";

import { useEffect } from "react";

import { ModalHeader } from "@/components/overlay/ModalHeader";
import type { ModalProps } from "@/components/types";
import { cn } from "@/lib/cn";

export function Modal({ open, onClose, title, children }: ModalProps) {
  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };

    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="presentation"
    >
      <button
        type="button"
        className="absolute inset-0 bg-text/40"
        aria-label="閉じる"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? "modal-title" : undefined}
        className={cn(
          "relative z-10 w-full max-w-lg rounded-lg bg-surface p-6 shadow-md",
        )}
      >
        {title ? <ModalHeader title={title} onClose={onClose} /> : null}
        <div className={title ? "mt-4" : undefined}>{children}</div>
      </div>
    </div>
  );
}

export type { ModalProps };
