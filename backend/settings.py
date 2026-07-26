import os

from dotenv import load_dotenv

# Loaded once for the whole application, replacing the previously scattered
# load_dotenv() calls in connect.py, auth/utils.py, and the repositories.
# override=False so real environment variables (Railway, docker compose,
# the test suite) always win over the committed .env file.
load_dotenv(override=False)

_ALLOWED_ENVS = {"development", "production"}


def _required(key: str) -> str:
    """Reads an environment variable that must be present and non-empty."""
    value = os.getenv(key)
    if value is None or value == "":
        raise RuntimeError(f"Required environment variable {key!r} is not set")
    return value


class Settings:
    """
    Central, validated configuration for the app. Instantiated once as the
    module-level `settings` object; import that instead of calling os.getenv
    directly. Every required variable is validated at import time, so a
    misconfigured deployment fails fast at startup with a clear message rather
    than deep inside a request.
    """

    def __init__(self):
        # Environment
        self.ENV = os.getenv("ENV", "development")
        if self.ENV not in _ALLOWED_ENVS:
            raise RuntimeError(
                f"ENV must be one of {sorted(_ALLOWED_ENVS)}, got {self.ENV!r}"
            )
        # Docs are exposed everywhere except production.
        self.DOCS_ENABLED = self.ENV != "production"

        # Database
        self.DB_NAME = _required("DB_NAME")
        self.DB_USER = _required("DB_USER")
        self.DB_PASSWORD = _required("DB_PASSWORD")
        self.DB_HOST = _required("DB_HOST")
        self.DB_PORT = _required("DB_PORT")

        # Auth / JWT
        self.SECRET_KEY = _required("SECRET_KEY")
        self.ALGORITHM = os.getenv("ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_HOURS = int(_required("ACCESS_TOKEN_EXPIRE_HOURS"))

        # Evolution API (WhatsApp)
        self.EVO_API_URL = _required("EVO_API_URL")
        self.EVO_API_TOKEN = _required("EVO_API_TOKEN")
        self.WHATSAPP_WEBHOOK_URL = _required("WHATSAPP_WEBHOOK_URL")

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


settings = Settings()
