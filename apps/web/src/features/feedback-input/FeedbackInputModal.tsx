"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/action/Button";
import { Text } from "@/components/display/Text";
import { Alert } from "@/components/feedback/Alert";
import { TextArea } from "@/components/form/TextArea";
import { Modal } from "@/components/overlay/Modal";
import {
  FeedbackTargetType,
  FeedbackType,
  FeedbackValueType,
  type FeedbackType as FeedbackTypeValue,
} from "@/generated/api/giftRecommendationServicePublicAPI.schemas";
import { submitFeedback } from "@/lib/api";
import { cn } from "@/lib/cn";

import {
  CANCEL_LABEL,
  COMMENT_LABEL,
  COMMENT_MAX_LENGTH,
  COMMENT_PLACEHOLDER,
  COMMENT_TOO_LONG,
  MODAL_TITLE,
  PROMPT_TEXT,
  RETRY_LABEL,
  SELECT_HINT,
  SUBMIT_LABEL,
  SUCCESS_AUTO_CLOSE_MS,
  SUCCESS_FALLBACK_MESSAGE,
} from "./constants";
import { ITEM_FEEDBACK_OPTIONS, findItemFeedbackOption } from "./feedback-options";
import {
  mapFeedbackSubmitError,
  type FeedbackUiError,
} from "./map-feedback-error";
import { getOrCreateFeedbackSessionId } from "./session-id";

export type FeedbackInputModalProps = {
  open: boolean;
  onClose: () => void;
  resultId: string;
  resultItemId: string;
  itemName?: string;
  /** SCR-004 / SCR-006。Request の sourcePage に載せる（仕様は SCR-007 推奨だが起動元も可） */
  sourcePage?: string;
};

type Phase =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "success"; message: string }
  | { status: "error"; error: FeedbackUiError };

export function FeedbackInputModal({
  open,
  onClose,
  resultId,
  resultItemId,
  itemName,
  sourcePage = "SCR-007",
}: FeedbackInputModalProps) {
  const [selectedType, setSelectedType] = useState<FeedbackTypeValue | null>(
    null,
  );
  const [comment, setComment] = useState("");
  const [phase, setPhase] = useState<Phase>({ status: "idle" });

  useEffect(() => {
    if (!open) {
      return;
    }
    setSelectedType(null);
    setComment("");
    setPhase({ status: "idle" });
  }, [open, resultId, resultItemId]);

  useEffect(() => {
    if (phase.status !== "success") {
      return;
    }
    const timer = window.setTimeout(() => {
      onClose();
    }, SUCCESS_AUTO_CLOSE_MS);
    return () => window.clearTimeout(timer);
  }, [phase, onClose]);

  const commentTooLong = comment.length > COMMENT_MAX_LENGTH;
  const canSubmit =
    Boolean(selectedType) &&
    !commentTooLong &&
    phase.status !== "submitting" &&
    phase.status !== "success";

  async function handleSubmit() {
    if (!selectedType || !canSubmit) {
      return;
    }
    const option = findItemFeedbackOption(selectedType);
    if (!option) {
      return;
    }

    setPhase({ status: "submitting" });
    const trimmed = comment.trim();
    try {
      const response = await submitFeedback(resultId, {
        feedbackTargetType: FeedbackTargetType.item,
        resultItemId,
        feedbackType: option.feedbackType,
        feedbackValueType: FeedbackValueType.boolean,
        feedbackValue: option.feedbackType === FeedbackType.item_good,
        rating: option.rating,
        ...(trimmed ? { comment: trimmed } : {}),
        sourcePage,
        sessionId: getOrCreateFeedbackSessionId(),
      });

      if (response.status === 200 || response.status === 201) {
        const message =
          response.data.data.message?.trim() || SUCCESS_FALLBACK_MESSAGE;
        setPhase({ status: "success", message });
        return;
      }

      setPhase({
        status: "error",
        error: mapFeedbackSubmitError(response.status, response.data),
      });
    } catch {
      setPhase({
        status: "error",
        error: mapFeedbackSubmitError(null),
      });
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={MODAL_TITLE}>
      <div className="flex flex-col gap-4">
        {itemName ? (
          <Text className="text-small text-text-secondary">対象: {itemName}</Text>
        ) : null}

        {phase.status === "success" ? (
          <Alert variant="info" title="送信完了">
            {phase.message}
          </Alert>
        ) : (
          <>
            <Text>{PROMPT_TEXT}</Text>

            <div
              className="flex flex-wrap gap-2"
              role="group"
              aria-label="評価選択"
            >
              {ITEM_FEEDBACK_OPTIONS.map((option) => {
                const selected = selectedType === option.feedbackType;
                return (
                  <button
                    key={option.feedbackType}
                    type="button"
                    disabled={phase.status === "submitting"}
                    aria-pressed={selected}
                    className={cn(
                      "rounded-sm border px-3 py-2 text-small transition-colors",
                      selected
                        ? "border-primary bg-primary/10 text-primary"
                        : "border-border bg-surface text-text hover:bg-surface-muted",
                      "disabled:opacity-60",
                    )}
                    onClick={() => setSelectedType(option.feedbackType)}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>

            {!selectedType ? (
              <Text className="text-small text-text-muted">{SELECT_HINT}</Text>
            ) : null}

            <div className="flex flex-col gap-1">
              <label htmlFor="scr-007-comment" className="text-small text-text">
                {COMMENT_LABEL}
              </label>
              <TextArea
                id="scr-007-comment"
                value={comment}
                disabled={phase.status === "submitting"}
                placeholder={COMMENT_PLACEHOLDER}
                maxLength={COMMENT_MAX_LENGTH + 50}
                onChange={(event) => setComment(event.target.value)}
              />
              <Text
                className={cn(
                  "text-small",
                  commentTooLong ? "text-error" : "text-text-muted",
                )}
              >
                {comment.length}/{COMMENT_MAX_LENGTH}
                {commentTooLong ? ` — ${COMMENT_TOO_LONG}` : null}
              </Text>
            </div>

            {phase.status === "error" ? (
              <Alert
                variant={phase.error.alertVariant}
                title={phase.error.title}
              >
                <p>{phase.error.message}</p>
              </Alert>
            ) : null}

            <div className="flex flex-wrap justify-end gap-3">
              <Button
                type="button"
                variant="secondary"
                onClick={onClose}
                disabled={phase.status === "submitting"}
              >
                {CANCEL_LABEL}
              </Button>
              {phase.status === "error" && phase.error.retryable ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => void handleSubmit()}
                >
                  {RETRY_LABEL}
                </Button>
              ) : null}
              <Button
                type="button"
                variant="primary"
                loading={phase.status === "submitting"}
                disabled={!canSubmit}
                onClick={() => void handleSubmit()}
              >
                {SUBMIT_LABEL}
              </Button>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
}
