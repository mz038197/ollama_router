from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.use_cases.admin_use_case import AdminUseCase
from src.application.use_cases.api_use_case import ApiUseCase
from src.application.use_cases.auth_use_case import AuthUseCase
from src.presentation.fastapi.error_handlers import register_error_handlers
from src.presentation.fastapi.middleware.api_key_middleware import ApiKeyMiddleware
from src.presentation.fastapi.routers.admin_router import create_admin_router
from src.presentation.fastapi.routers.api_router import create_api_router


def build_test_client(fake_repo, fake_gateway, fake_logger) -> TestClient:
    auth_use_case = AuthUseCase(api_key_repo=fake_repo)
    api_use_case = ApiUseCase(gateway=fake_gateway, api_key_repo=fake_repo, logger=fake_logger)
    admin_use_case = AdminUseCase(api_key_repo=fake_repo)

    app = FastAPI()
    register_error_handlers(app)
    app.add_middleware(ApiKeyMiddleware, auth_use_case=auth_use_case)
    app.include_router(create_api_router(api_use_case))
    app.include_router(create_admin_router(admin_use_case))
    return TestClient(app)


def test_health_endpoint_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert "queue_waiting" in payload
    assert "backends" in payload


def test_models_endpoint_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.get("/v1/models")
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "list"
    assert isinstance(payload["data"], list)
    assert payload["data"][0]["id"] == "fake-model"


def test_chat_completion_rejects_when_api_key_missing(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        json={"model": "fake-model", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "無效的 API 金鑰"}


def test_chat_completion_nonstream_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={"model": "fake-model", "messages": [{"role": "user", "content": "hello"}], "stream": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert "choices" in payload
    assert "usage" in payload
    assert payload["choices"][0]["message"]["role"] == "assistant"


def test_chat_completion_stream_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    with client.stream(
        "POST",
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={"model": "fake-model", "messages": [{"role": "user", "content": "hello"}], "stream": True},
    ) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "data: [DONE]" in body


def test_admin_panel_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert len(response.text) > 0


def test_admin_config_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.get("/api/admin/config")
    assert response.status_code == 200
    payload = response.json()
    assert "teachers" in payload
    assert "enabled" in payload


def test_admin_teacher_add_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post("/api/admin/teacher/add", json={"name": "TeacherB"})
    assert response.status_code == 201
    assert response.json() == {"success": True, "message": "已新增教師: TeacherB"}


def test_admin_teacher_delete_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post("/api/admin/teacher/delete", json={"teacher": "TeacherA"})
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "已刪除教師: TeacherA"}


def test_admin_key_add_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/api/admin/key/add",
        json={"teacher": "TeacherA", "name": "ClassZ", "key": "new-key", "enabled": True},
    )
    assert response.status_code == 201
    assert response.json() == {"success": True, "message": "已為 TeacherA 新增金鑰: ClassZ"}


def test_admin_key_status_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    client.post(
        "/api/admin/key/add",
        json={"teacher": "TeacherA", "name": "ClassZ", "key": "new-key", "enabled": True},
    )
    response = client.post(
        "/api/admin/key/status",
        json={"teacher": "TeacherA", "key": "new-key", "enabled": False},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "已禁用金鑰: new-key"}


def test_admin_key_delete_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/api/admin/key/delete",
        json={"teacher": "TeacherA", "key": "valid-key"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "已刪除金鑰: valid-key"}


def test_admin_teacher_add_bad_request_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post("/api/admin/teacher/add", json={"name": "   "})
    assert response.status_code == 400
    payload = response.json()
    assert payload["detail"]["code"] == "ADMIN_INVALID_TEACHER_NAME"
    assert payload["detail"]["message"] == "教師名稱不能為空"


def test_admin_teacher_delete_not_found_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post("/api/admin/teacher/delete", json={"teacher": "NoSuchTeacher"})
    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"]["code"] == "ADMIN_TEACHER_NOT_FOUND"
    assert payload["detail"]["message"] == "教師不存在: NoSuchTeacher"
