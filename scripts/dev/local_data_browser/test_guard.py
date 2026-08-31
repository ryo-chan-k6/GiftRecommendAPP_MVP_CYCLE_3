#!/usr/bin/env python3
"""guard.py の DB 不要単体テスト。"""

from __future__ import annotations

import unittest

from guard import (
    assert_app_env_allows_local_browser,
    assert_local_bind_host,
    assert_local_database_url,
    describe_db_target,
    sql_is_read_only,
)


class LocalDatabaseUrlTests(unittest.TestCase):
    def test_loopback_ok(self) -> None:
        desc = assert_local_database_url(
            "postgresql://postgres:secret-value@127.0.0.1:54322/postgres"
        )
        self.assertEqual(desc, "127.0.0.1:54322/postgres")
        self.assertNotIn("secret-value", desc)
        self.assertNotIn("postgres:secret", desc)

    def test_localhost_normalized(self) -> None:
        desc = assert_local_database_url("postgresql://u:p@localhost:5432/app")
        self.assertEqual(desc, "127.0.0.1:5432/app")
        self.assertNotIn("u:p", desc)

    def test_remote_host_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            assert_local_database_url(
                "postgresql://postgres:secret@db.example.supabase.co:5432/postgres"
            )
        message = str(ctx.exception)
        self.assertNotIn("secret", message)
        self.assertNotIn("supabase.co", message)
        self.assertIn("loopback", message)

    def test_empty_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assert_local_database_url("")

    def test_describe_never_includes_password(self) -> None:
        desc = describe_db_target("postgresql://alice:s3cret@127.0.0.1:54322/gift")
        self.assertEqual(desc, "127.0.0.1:54322/gift")
        self.assertNotIn("alice", desc)
        self.assertNotIn("s3cret", desc)


class BindHostTests(unittest.TestCase):
    def test_loopback_ok(self) -> None:
        self.assertEqual(assert_local_bind_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(assert_local_bind_host("localhost"), "127.0.0.1")

    def test_wildcard_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            assert_local_bind_host("0.0.0.0")
        self.assertIn("0.0.0.0", str(ctx.exception))
        self.assertIn("Human", str(ctx.exception))


class AppEnvTests(unittest.TestCase):
    def test_dev_ok(self) -> None:
        assert_app_env_allows_local_browser("dev")
        assert_app_env_allows_local_browser("local")
        assert_app_env_allows_local_browser(None)

    def test_prod_rejected(self) -> None:
        with self.assertRaises(ValueError):
            assert_app_env_allows_local_browser("production")
        with self.assertRaises(ValueError):
            assert_app_env_allows_local_browser("stg")


class SqlReadOnlyTests(unittest.TestCase):
    def test_select_ok(self) -> None:
        self.assertTrue(sql_is_read_only("SELECT count(*) FROM item"))
        self.assertTrue(
            sql_is_read_only(
                "WITH x AS (SELECT 1 AS n) SELECT n FROM x"
            )
        )

    def test_mutating_rejected(self) -> None:
        self.assertFalse(sql_is_read_only("DELETE FROM item"))
        self.assertFalse(sql_is_read_only("TRUNCATE item"))
        self.assertFalse(sql_is_read_only("SELECT 1; DELETE FROM item"))
        self.assertFalse(sql_is_read_only("DROP TABLE item"))
        self.assertFalse(sql_is_read_only("UPDATE item SET is_active = false"))

    def test_empty_rejected(self) -> None:
        self.assertFalse(sql_is_read_only(""))
        self.assertFalse(sql_is_read_only("   "))


if __name__ == "__main__":
    unittest.main()
