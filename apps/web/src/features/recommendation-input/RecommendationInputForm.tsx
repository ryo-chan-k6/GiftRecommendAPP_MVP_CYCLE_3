"use client";

import { Button } from "@/components/action/Button";
import { FormField } from "@/components/form/FormField";
import { FormSection } from "@/components/form/FormSection";
import { NumberInput } from "@/components/form/NumberInput";
import { Select } from "@/components/form/Select";
import { TextArea } from "@/components/form/TextArea";
import {
  NG_TEXT_MAX,
  NON_PREFERRED_TEXT_MAX,
  PREFERRED_TEXT_MAX,
} from "./constants";
import type {
  MasterOption,
  RecommendationInputFieldErrors,
  RecommendationInputFormValues,
} from "./types";

export type RecommendationInputFormProps = {
  values: RecommendationInputFormValues;
  errors: RecommendationInputFieldErrors;
  relationships: MasterOption[];
  occasions: MasterOption[];
  mastersLoading: boolean;
  mastersEmpty: boolean;
  submitDisabled: boolean;
  onChange: (patch: Partial<RecommendationInputFormValues>) => void;
  onBlurField: (field: keyof RecommendationInputFieldErrors) => void;
  onSubmit: () => void;
};

export function RecommendationInputForm({
  values,
  errors,
  relationships,
  occasions,
  mastersLoading,
  mastersEmpty,
  submitDisabled,
  onChange,
  onBlurField,
  onSubmit,
}: RecommendationInputFormProps) {
  const selectDisabled = mastersLoading || mastersEmpty;

  return (
    <form
      className="flex flex-col gap-8"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      noValidate
    >
      <FormSection
        title="贈る相手と用途"
        description="必須項目を選んでください。"
      >
        <FormField
          label="贈る相手"
          required
          htmlFor="relationshipCode"
          error={errors.relationshipCode}
        >
          <Select
            id="relationshipCode"
            name="relationshipCode"
            value={values.relationshipCode}
            disabled={selectDisabled}
            aria-invalid={Boolean(errors.relationshipCode)}
            onChange={(event) =>
              onChange({ relationshipCode: event.target.value })
            }
            onBlur={() => onBlurField("relationshipCode")}
          >
            <option value="">
              {mastersLoading
                ? "読み込み中…"
                : mastersEmpty
                  ? "選択肢がありません"
                  : "選択してください"}
            </option>
            {relationships.map((item) => (
              <option key={item.code} value={item.code}>
                {item.label}
              </option>
            ))}
          </Select>
        </FormField>

        <FormField
          label="用途"
          required
          htmlFor="occasionCode"
          error={errors.occasionCode}
        >
          <Select
            id="occasionCode"
            name="occasionCode"
            value={values.occasionCode}
            disabled={selectDisabled}
            aria-invalid={Boolean(errors.occasionCode)}
            onChange={(event) => onChange({ occasionCode: event.target.value })}
            onBlur={() => onBlurField("occasionCode")}
          >
            <option value="">
              {mastersLoading
                ? "読み込み中…"
                : mastersEmpty
                  ? "選択肢がありません"
                  : "選択してください"}
            </option>
            {occasions.map((item) => (
              <option key={item.code} value={item.code}>
                {item.label}
              </option>
            ))}
          </Select>
        </FormField>
      </FormSection>

      <FormSection
        title="予算"
        description="上限は必須です。単位は円（税込）です。"
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            label="予算下限"
            htmlFor="budgetMin"
            error={errors.budgetMin}
            helperText="任意"
          >
            <NumberInput
              id="budgetMin"
              name="budgetMin"
              inputMode="numeric"
              min={0}
              step={1}
              value={values.budgetMin}
              aria-invalid={Boolean(errors.budgetMin)}
              onChange={(event) => onChange({ budgetMin: event.target.value })}
              onBlur={() => onBlurField("budgetMin")}
            />
          </FormField>
          <FormField
            label="予算上限"
            required
            htmlFor="budgetMax"
            error={errors.budgetMax}
          >
            <NumberInput
              id="budgetMax"
              name="budgetMax"
              inputMode="numeric"
              min={0}
              step={1}
              value={values.budgetMax}
              aria-invalid={Boolean(errors.budgetMax)}
              onChange={(event) => onChange({ budgetMax: event.target.value })}
              onBlur={() => onBlurField("budgetMax")}
            />
          </FormField>
        </div>
      </FormSection>

      <FormSection
        title="好み・避けたい条件"
        description="任意です。レコメンドの手がかりになります。"
      >
        <FormField
          label="好み"
          htmlFor="preferredText"
          error={errors.preferredText}
          helperText={`最大 ${PREFERRED_TEXT_MAX} 文字`}
        >
          <TextArea
            id="preferredText"
            name="preferredText"
            rows={3}
            maxLength={PREFERRED_TEXT_MAX + 50}
            value={values.preferredText}
            aria-invalid={Boolean(errors.preferredText)}
            onChange={(event) =>
              onChange({ preferredText: event.target.value })
            }
            onBlur={() => onBlurField("preferredText")}
          />
        </FormField>
        <FormField
          label="避けたい条件"
          htmlFor="nonPreferredText"
          error={errors.nonPreferredText}
          helperText={`最大 ${NON_PREFERRED_TEXT_MAX} 文字`}
        >
          <TextArea
            id="nonPreferredText"
            name="nonPreferredText"
            rows={3}
            maxLength={NON_PREFERRED_TEXT_MAX + 50}
            value={values.nonPreferredText}
            aria-invalid={Boolean(errors.nonPreferredText)}
            onChange={(event) =>
              onChange({ nonPreferredText: event.target.value })
            }
            onBlur={() => onBlurField("nonPreferredText")}
          />
        </FormField>
        <FormField
          label="NG条件"
          htmlFor="ngText"
          error={errors.ngText}
          helperText={`最大 ${NG_TEXT_MAX} 文字（Hard Filter）`}
        >
          <TextArea
            id="ngText"
            name="ngText"
            rows={2}
            maxLength={NG_TEXT_MAX + 50}
            value={values.ngText}
            aria-invalid={Boolean(errors.ngText)}
            onChange={(event) => onChange({ ngText: event.target.value })}
            onBlur={() => onBlurField("ngText")}
          />
        </FormField>
      </FormSection>

      <div>
        <Button
          type="submit"
          variant="primary"
          size="lg"
          disabled={submitDisabled}
        >
          レコメンドを実行
        </Button>
      </div>
    </form>
  );
}
