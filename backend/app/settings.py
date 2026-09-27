import os
from dataclasses import dataclass, field

from app.config import BACKEND_DIR


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: _env(
        "DATABASE_URL", f"sqlite:///{(BACKEND_DIR / 'accessguard.db').as_posix()}"))
    jwt_secret: str = field(default_factory=lambda: _env("JWT_SECRET", "dev-only-insecure-secret"))
    jwt_expire_minutes: int = field(default_factory=lambda: int(_env("JWT_EXPIRE_MINUTES", "480")))
    cors_origins: list[str] = field(default_factory=lambda: [
        o.strip() for o in _env("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",") if o.strip()
    ])
    auditor_username: str = field(default_factory=lambda: _env("AUDITOR_USERNAME", "auditor"))
    auditor_password: str = field(default_factory=lambda: _env("AUDITOR_PASSWORD", "Auditor@123"))
    viewer_username: str = field(default_factory=lambda: _env("VIEWER_USERNAME", "viewer"))
    viewer_password: str = field(default_factory=lambda: _env("VIEWER_PASSWORD", "Viewer@123"))
    max_upload_bytes: int = 10 * 1024 * 1024


settings = Settings()
