from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.use_cases.portal_use_case import PortalUseCase
from src.infrastructure.config import DatabaseSettings, RouterSettings
from src.infrastructure.repositories.sqlite_router_repository import SqliteRouterRepository
from src.presentation.fastapi.routers.portal_router import create_portal_router


def _client(tmp_path):
    settings = RouterSettings(
        path=str(tmp_path / "router.yaml"),
        database=DatabaseSettings(path=str(tmp_path / "router.db"), archive_dir=str(tmp_path / "archive")),
    )
    repo = SqliteRouterRepository(str(tmp_path / "router.db"), settings)
    app = FastAPI()
    app.include_router(create_portal_router(PortalUseCase(repo, settings)))
    return TestClient(app), repo


def test_portal_permission_error_returns_403(tmp_path):
    client, repo = _client(tmp_path)
    student = repo.upsert_google_user("student@example.com", "Student")

    response = client.get("/admin/users", cookies={"session_user_id": str(student["id"])})

    assert response.status_code == 403
    assert response.json()["detail"] == "權限不足"


def test_admin_archive_run_endpoint(tmp_path):
    client, repo = _client(tmp_path)
    admin = repo.upsert_google_user("admin@example.com", "Admin")
    repo.update_user(admin["id"], role="admin")

    response = client.post("/admin/archive/run", cookies={"session_user_id": str(admin["id"])})

    assert response.status_code == 200
    assert response.json() == {"archived": 0}


def test_admin_update_settings_endpoint(tmp_path):
    client, repo = _client(tmp_path)
    admin = repo.upsert_google_user("admin@example.com", "Admin")
    repo.update_user(admin["id"], role="admin")

    response = client.patch(
        "/admin/settings",
        cookies={"session_user_id": str(admin["id"])},
        json={"retention_days": 10, "student_default_ttl_hours": 4, "open_registration": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["prompt_logs"]["retention_days"] == 10
    assert payload["student_default_ttl_hours"] == 4
    assert payload["auth"]["open_registration"] is False


def test_admin_update_class_endpoint(tmp_path):
    client, repo = _client(tmp_path)
    admin = repo.upsert_google_user("admin@example.com", "Admin")
    repo.update_user(admin["id"], role="admin")
    teacher = repo.upsert_google_user("teacher@example.com", "Teacher")
    repo.update_user(teacher["id"], role="teacher")
    klass = repo.create_class(teacher["id"], "AI", None, 2)

    response = client.patch(
        f"/admin/classes/{klass['id']}",
        cookies={"session_user_id": str(admin["id"])},
        json={"status": "ended"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ended"
