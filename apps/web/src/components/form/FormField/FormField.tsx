import type { FormFieldProps } from "@/components/types";
import { InlineError } from "@/components/feedback/InlineError";
import { cn } from "@/lib/cn";

export function FormField({
  label,
  required = false,
  helperText,
  error,
  children,
  htmlFor,
}: FormFieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <label
        htmlFor={htmlFor}
        className={cn("text-label font-medium text-text", htmlFor && "cursor-pointer")}
      >
        {label}
        {required ? (
          <span className="ml-1 text-error" aria-hidden>
            *
          </span>
        ) : null}
      </label>
      {children}
      {helperText && !error ? (
        <p className="text-small text-text-muted">{helperText}</p>
      ) : null}
      {error ? <InlineError message={error} /> : null}
    </div>
  );
}
