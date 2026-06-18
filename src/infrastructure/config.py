from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AuthSettings:
    teacher_domain: str = ""
    admin_emails: tuple[str, ...] = ()
    session_secret: str = "dev-session-secret"
    google_client_id: str = ""
    google_client_secret: str = ""
    open_registration: bool = True


@dataclass(frozen=True)
class DatabaseSettings:
    path: str = "~/.ollama_router/router.db"
    archive_dir: str = "~/.ollama_router/archive"


@dataclass(frozen=True)
class PromptLogSettings:
    retention_days: int = 30


@dataclass(frozen=True)
class RouterSettings:
    path: str | None = None
    public_url: str = "http://127.0.0.1:8000"
    student_default_ttl_hours: int = 2
    auth: AuthSettings = field(default_factory=AuthSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    prompt_logs: PromptLogSettings = field(default_factory=PromptLogSettings)


def load_router_settings(path: str | None = None) -> RouterSettings:
    config_path = Path(path).expanduser() if path else Path("~/.ollama_router/router.yaml").expanduser()
    if not config_path.exists():
        return RouterSettings(path=str(config_path))

    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    auth = data.get("auth") or {}
    database = data.get("database") or {}
    prompt_logs = data.get("prompt_logs") or {}

    return RouterSettings(
        path=str(config_path),
        public_url=str(data.get("public_url", "http://127.0.0.1:8000")),
        student_default_ttl_hours=int(data.get("student_default_ttl_hours", 2)),
        auth=AuthSettings(
            teacher_domain=str(auth.get("teacher_domain", "")).lower(),
            admin_emails=tuple(str(e).lower() for e in auth.get("admin_emails", [])),
            session_secret=str(auth.get("session_secret", "dev-session-secret")),
            google_client_id=str(auth.get("google_client_id", "")),
            google_client_secret=str(auth.get("google_client_secret", "")),
            open_registration=bool(auth.get("open_registration", True)),
        ),
        database=DatabaseSettings(
            path=str(database.get("path", "~/.ollama_router/router.db")),
            archive_dir=str(database.get("archive_dir", "~/.ollama_router/archive")),
        ),
        prompt_logs=PromptLogSettings(retention_days=int(prompt_logs.get("retention_days", 30))),
    )


def settings_summary(settings: RouterSettings) -> dict[str, Any]:
    return {
        "config_path": settings.path,
        "public_url": settings.public_url,
        "database_path": settings.database.path,
        "archive_dir": settings.database.archive_dir,
        "auth": {
            "teacher_domain": settings.auth.teacher_domain,
            "admin_emails": list(settings.auth.admin_emails),
            "google_client_id": settings.auth.google_client_id,
            "google_client_secret": "***" if settings.auth.google_client_secret else "",
            "open_registration": settings.auth.open_registration,
        },
        "student_default_ttl_hours": settings.student_default_ttl_hours,
        "prompt_logs": {"retention_days": settings.prompt_logs.retention_days},
    }


def update_non_secret_settings(
    path: str,
    retention_days: int | None = None,
    student_default_ttl_hours: int | None = None,
    open_registration: bool | None = None,
) -> RouterSettings:
    config_path = Path(path).expanduser()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    data = data or {}
    if student_default_ttl_hours is not None:
        data["student_default_ttl_hours"] = student_default_ttl_hours
    if retention_days is not None:
        data.setdefault("prompt_logs", {})["retention_days"] = retention_days
    if open_registration is not None:
        data.setdefault("auth", {})["open_registration"] = open_registration
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return load_router_settings(str(config_path))
