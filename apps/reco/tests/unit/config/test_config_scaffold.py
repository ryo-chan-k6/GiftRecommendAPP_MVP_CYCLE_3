import pytest

from reco.config import (
    AppEnv,
    RecoSettings,
    load_reco_settings,
    parse_app_env,
    scaffold_reco_settings,
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


def test_load_reco_settings_reads_non_secret_fields() -> None:
    settings = load_reco_settings(
        environ={
            "APP_ENV": "stg",
            "LOG_LEVEL": "debug",
            "PORT": "8000",
        }
    )

    assert settings.app_env is AppEnv.STG
    assert settings.log_level == "debug"
    assert settings.port == 8000
    assert settings.missing_required_secrets() == (
        "DATABASE_URL",
        "REDIS_URL",
        "OPENAI_API_KEY",
        "RECO_INTERNAL_API_KEY",
    )


def test_load_reco_settings_reads_secret_fields_without_logging() -> None:
    settings = load_reco_settings(
        environ={
            "APP_ENV": "dev",
            "DATABASE_URL": "postgresql://user:password@localhost:5432/gift_reco_dev",
            "REDIS_URL": "redis://localhost:6379/0",
            "OPENAI_API_KEY": "test-openai-key",
            "RECO_INTERNAL_API_KEY": "test-internal-key",
        }
    )

    assert settings.has_required_secrets() is True
    assert settings.database_url == "postgresql://user:password@localhost:5432/gift_reco_dev"
    assert "password" not in repr(settings)


def test_load_reco_settings_rejects_invalid_port() -> None:
    with pytest.raises(ValueError, match="PORT must be an integer"):
        load_reco_settings(environ={"PORT": "not-a-number"})

    with pytest.raises(ValueError, match="PORT must be positive"):
        load_reco_settings(environ={"PORT": "0"})


def test_scaffold_reco_settings_provides_placeholder_secrets() -> None:
    settings = scaffold_reco_settings(app_env=AppEnv.PROD)

    assert settings.app_env is AppEnv.PROD
    assert settings.port == 8000
    assert settings.has_required_secrets() is True
    assert isinstance(settings, RecoSettings)
