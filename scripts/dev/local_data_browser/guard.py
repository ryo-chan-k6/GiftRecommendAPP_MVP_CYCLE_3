"""Local-only connection / bind / SQL 読み取りガード。

secret・接続文字列実値は戻り値にも例外メッセージにも含めない。
"""

from __future__ import annotations

from urllib.parse import unquote, urlparse

ALLOWED_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0:0:0:0:0:0:0:1"})
ALLOWED_BIND_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
FORBIDDEN_APP_ENV = frozenset({"prod", "production", "stg", "staging"})
READ_ONLY_LEAD_TOKENS = frozenset({"SELECT", "WITH"})
MUTATING_TOKENS = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "GRANT",
        "REVOKE",
        "COPY",
        "CALL",
        "DO",
        "VACUUM",
        "REINDEX",
        "CLUSTER",
        "LOCK",
        "LISTEN",
        "NOTIFY",
        "SECURITY",
        "SET ROLE",
    }
)


def _first_sql_token(sql: str) -> str:
    text = sql.strip()
    if not text:
        return ""
    while text.startswith("--"):
        newline = text.find("\n")
        if newline < 0:
            return ""
        text = text[newline + 1 :].strip()
    if text.startswith("/*"):
        end = text.find("*/")
        if end < 0:
            return ""
        text = text[end + 2 :].strip()
    if text.startswith("("):
        text = text[1:].strip()
    token = text.split(None, 1)[0] if text else ""
    return token.upper().rstrip(";")


def sql_is_read_only(sql: str) -> bool:
    """SELECT / WITH のみ許可。コメント付きでも先頭トークンで判定する。"""
    if not sql or not str(sql).strip():
        return False
    upper = " ".join(str(sql).upper().split())
    for token in MUTATING_TOKENS:
        if token in upper.split() or f"{token} " in f"{upper} ":
            # 列名に偶然含まれるのを避けるため単語境界で見る
            padded = f" {upper} "
            if f" {token} " in padded or padded.strip().startswith(token + " "):
                return False
    lead = _first_sql_token(sql)
    return lead in READ_ONLY_LEAD_TOKENS


def describe_db_target(database_url: str) -> str:
    """host:port/dbname のみ返す。user / password は出さない。"""
    parsed = urlparse(database_url)
    host = (parsed.hostname or "").lower()
    port = parsed.port or ""
    dbname = (parsed.path or "").lstrip("/") or "(unknown-db)"
    if host in {"localhost", "127.0.0.1"}:
        host = "127.0.0.1"
    elif host in {"::1", "0:0:0:0:0:0:0:1"}:
        host = "::1"
    port_part = f":{port}" if port else ""
    return f"{host}{port_part}/{dbname}"


def assert_local_database_url(database_url: str) -> str:
    """loopback 以外の DATABASE_URL を拒否する。成功時は describe_db_target を返す。"""
    if not database_url or not str(database_url).strip():
        raise ValueError("DATABASE_URL が空です。リポジトリの .env を確認してください。")
    parsed = urlparse(database_url.strip())
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise ValueError("DATABASE_URL の scheme が PostgreSQL ではありません。")
    host = unquote(parsed.hostname or "").lower().strip("[]")
    if not host:
        raise ValueError("DATABASE_URL に host がありません。")
    if host not in ALLOWED_LOOPBACK_HOSTS:
        raise ValueError(
            "DATABASE_URL の host が local loopback ではありません。"
            " 本ビューアは 127.0.0.1 / localhost / ::1 のみ接続します。"
            " 本番・stg・クラウド DB へ繋ぐ場合は Human 判断が必要です。"
        )
    if parsed.username is None and ":@" in database_url:
        # 異常な URL。実値は出さない
        raise ValueError("DATABASE_URL の形式が不正です。")
    return describe_db_target(database_url)


def assert_local_bind_host(host: str) -> str:
    """0.0.0.0 など外部公開 bind を拒否する。"""
    normalized = (host or "").strip().lower().strip("[]")
    if normalized not in ALLOWED_BIND_HOSTS:
        raise ValueError(
            "bind host が loopback ではありません。"
            " 本ビューアは 127.0.0.1 のみ待受します。0.0.0.0 での公開は Human 判断が必要です。"
        )
    if normalized in {"localhost", "127.0.0.1"}:
        return "127.0.0.1"
    return "::1"


def assert_app_env_allows_local_browser(app_env: str | None) -> None:
    """APP_ENV が prod / stg のとき起動しない。"""
    if app_env is None or not str(app_env).strip():
        return
    key = str(app_env).strip().lower()
    if key in FORBIDDEN_APP_ENV:
        raise ValueError(
            f"APP_ENV={key} では起動しません。"
            " local/dev 以外の環境の DB 可視化は Human 判断が必要です。"
        )
