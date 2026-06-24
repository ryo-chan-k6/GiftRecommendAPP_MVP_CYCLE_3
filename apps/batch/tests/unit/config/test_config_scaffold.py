import pytest

from batch.config import (
    AppEnv,
    BatchSettings,
    load_batch_settings,
    parse_app_env,
    scaffold_batch_settings,
)


def test_parse_app_env_defaults_to_dev() -> None:
    assert parse_app_env(None) is AppEnv.DEV
    assert parse_app_env("") is AppEnv.DEV


def test_parse_app_env_accepts_supported_values() -> None:
    assert parse_app_env("prod") is AppEnv.PROD
    assert parse_app_env(" STG ") is AppEnv.STG


def test_parse_app_env_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="Unsupported APP_ENV"):
        parse_app_env("stage")


def test_load_batch_settings_reads_non_secret_fields() -> None:
    settings = load_batch_settings(
        environ={
            "APP_ENV": "stg",
            "LOG_LEVEL": "debug",
            "OBJECT_STORAGE_BUCKET": "raw-dev",
            "OBJECT_STORAGE_ENDPOINT": "https://storage.example",
            "BATCH_CHUNK_SIZE": "250",
            "BATCH_MAX_RETRY": "5",
        }
    )

    assert settings.app_env is AppEnv.STG
    assert settings.log_level == "debug"
    assert settings.object_storage_bucket == "raw-dev"
    assert settings.object_storage_endpoint == "https://storage.example"
    assert settings.batch_chunk_size == 250
    assert settings.batch_max_retry == 5
    assert settings.missing_required_secrets() == (
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "RAKUTEN_APPLICATION_ID",
        "OBJECT_STORAGE_ACCESS_KEY",
        "OBJECT_STORAGE_SECRET_KEY",
    )


def test_load_batch_settings_reads_secret_fields_without_logging() -> None:
    settings = load_batch_settings(
        environ={
            "APP_ENV": "dev",
            "OBJECT_STORAGE_BUCKET": "raw-dev",
            "DATABASE_URL": "postgresql://user:password@localhost:5432/gift_reco_dev",
            "OPENAI_API_KEY": "test-openai-key",
            "RAKUTEN_APPLICATION_ID": "test-rakuten-app-id",
            "OBJECT_STORAGE_ACCESS_KEY": "test-access-key",
            "OBJECT_STORAGE_SECRET_KEY": "test-secret-key",
        }
    )

    assert settings.has_required_settings() is True
    assert settings.database_url == "postgresql://user:password@localhost:5432/gift_reco_dev"
    assert "password" not in repr(settings)


def test_load_batch_settings_reports_missing_required_config() -> None:
    settings = load_batch_settings(
        environ={
            "APP_ENV": "dev",
            "DATABASE_URL": "postgresql://localhost/db",
            "OPENAI_API_KEY": "test-openai-key",
            "RAKUTEN_APPLICATION_ID": "test-rakuten-app-id",
            "OBJECT_STORAGE_ACCESS_KEY": "test-access-key",
            "OBJECT_STORAGE_SECRET_KEY": "test-secret-key",
        }
    )

    assert settings.has_required_secrets() is True
    assert settings.missing_required_config() == ("OBJECT_STORAGE_BUCKET",)
    assert settings.has_required_settings() is False


def test_load_batch_settings_rejects_invalid_positive_int() -> None:
    with pytest.raises(ValueError, match="BATCH_CHUNK_SIZE must be an integer"):
        load_batch_settings(environ={"BATCH_CHUNK_SIZE": "not-a-number"})

    with pytest.raises(ValueError, match="BATCH_MAX_RETRY must be positive"):
        load_batch_settings(environ={"BATCH_MAX_RETRY": "0"})


def test_scaffold_batch_settings_provides_placeholder_secrets() -> None:
    settings = scaffold_batch_settings(app_env=AppEnv.PROD)

    assert settings.app_env is AppEnv.PROD
    assert settings.batch_chunk_size == 100
    assert settings.has_required_settings() is True
    assert isinstance(settings, BatchSettings)
