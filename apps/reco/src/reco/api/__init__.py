"""API-INT-002 reco Internal API endpoint layer."""

__all__ = ["app", "create_app"]


def __getattr__(name: str):
    if name == "create_app":
        from reco.api.main import create_app

        return create_app
    if name == "app":
        from reco.api.main import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
