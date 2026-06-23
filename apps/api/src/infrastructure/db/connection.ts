const SENSITIVE_URL_PATTERN =
  /(postgres(?:ql)?:\/\/)([^:@/]+)(?::([^@/]*))?@/i;

/** Redact credentials from a database URL before logging. */
export function maskDatabaseUrl(url: string): string {
  if (url.trim() === "") {
    return "";
  }

  return url.replace(
    SENSITIVE_URL_PATTERN,
    (_match, protocol: string, user: string, password?: string) => {
      const maskedUser = user === "" ? "" : "***REDACTED***";
      const maskedPassword =
        password === undefined ? "" : ":***REDACTED***";

      return `${protocol}${maskedUser}${maskedPassword}@`;
    },
  );
}
