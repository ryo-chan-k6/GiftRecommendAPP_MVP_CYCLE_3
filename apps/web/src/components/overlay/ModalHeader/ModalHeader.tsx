"use client";

import { Heading } from "@/components/display/Heading";

export type ModalHeaderProps = {
  title: string;
  onClose: () => void;
};

export function ModalHeader({ title, onClose }: ModalHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <Heading level={2} id="modal-title">
        {title}
      </Heading>
      <button
        type="button"
        onClick={onClose}
        className="rounded-sm px-2 py-1 text-small text-text-secondary hover:text-text"
        aria-label="閉じる"
      >
        ×
      </button>
    </div>
  );
}
