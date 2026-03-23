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
    admin_use_case = AdminUseCase(api_key_repo=fake_repo, request_logger=fake_logger)

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
    # 驗證無效的認證嘗試被記錄到審計追蹤
    assert len(fake_logger.entries) > 0
    # 檢查最後一次記錄是無效的認證
    last_entry = fake_logger.entries[-1]
    assert last_entry["is_valid"] is False


def test_chat_completion_rejects_when_api_key_invalid(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer invalid-key"},
        json={"model": "fake-model", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "無效的 API 金鑰"}
    # 驗證無效的認證嘗試被記錄到審計追蹤
    assert len(fake_logger.entries) > 0
    # 檢查最後一次記錄是無效的認證
    last_entry = fake_logger.entries[-1]
    assert last_entry["is_valid"] is False
    assert last_entry["api_key"] == "invalid-key"


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


def test_admin_logs_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={"model": "fake-model", "messages": [{"role": "user", "content": "hello log"}], "stream": False},
    )

    response = client.get("/api/admin/logs?limit=10")
    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert "total" in payload
    assert "has_more" in payload
    assert isinstance(payload["items"], list)


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


def test_admin_key_update_contract(fake_repo, fake_gateway, fake_logger):
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/api/admin/key/update",
        json={
            "teacher": "TeacherA",
            "old_key": "valid-key",
            "name": "ClassA-Edited",
            "key": "valid-key-updated",
            "enabled": False,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "已更新金鑰: ClassA-Edited"}


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


def test_chat_completion_rejects_empty_content(fake_repo, fake_gateway, fake_logger):
    """驗證 content 不能為空字符串 - API 契約強制執行非空內容。"""
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={"model": "fake-model", "messages": [{"role": "user", "content": ""}]},
    )
    # Pydantic 驗證失敗應返回 422 Unprocessable Entity
    assert response.status_code == 422
    payload = response.json()
    assert "detail" in payload


def test_chat_completion_rejects_null_content(fake_repo, fake_gateway, fake_logger):
    """驗證 content 不能為 null - API 契約不允許可選的內容欄位。"""
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={"model": "fake-model", "messages": [{"role": "user", "content": None}]},
    )
    # Pydantic 驗證失敗應返回 422 Unprocessable Entity
    assert response.status_code == 422
    payload = response.json()
    assert "detail" in payload


def test_chat_completion_with_openai_text_format(fake_repo, fake_gateway, fake_logger):
    """驗證支援 OpenAI 相容格式 - content 是包含 text 物件的陣列"""
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={
            "model": "fake-model",
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": "What is this?"}],
                }
            ],
            "stream": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["role"] == "assistant"


def test_chat_completion_with_openai_image_format(fake_repo, fake_gateway, fake_logger):
    """驗證支援 OpenAI 相容格式 - content 包含文字和影像"""
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={
            "model": "fake-model",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="},
                        },
                    ],
                }
            ],
            "stream": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert fake_gateway.last_nonstream_req is not None
    assert fake_gateway.last_nonstream_req.messages[0].images == ["/9j/4AAQSkZJRg=="]


def test_chat_completion_with_simple_text_format(fake_repo, fake_gateway, fake_logger):
    """驗證向後相容性 - content 仍可以是簡單字符串"""
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={
            "model": "fake-model",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"


def test_chat_completion_forwards_tools_to_gateway(fake_repo, fake_gateway, fake_logger):
    """驗證 tools / tool_choice 會傳入 use case 與 gateway（domain 請求）。"""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "天氣",
                "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
            },
        }
    ]
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={
            "model": "fake-model",
            "messages": [{"role": "user", "content": "台北天氣"}],
            "stream": False,
            "tools": tools,
            "tool_choice": "auto",
        },
    )
    assert response.status_code == 200
    assert fake_gateway.last_nonstream_req is not None
    assert fake_gateway.last_nonstream_req.tools == tools
    assert fake_gateway.last_nonstream_req.tool_choice == "auto"


def test_chat_completion_accepts_assistant_with_tool_calls_only(fake_repo, fake_gateway, fake_logger):
    """驗證 OpenAI 風格：assistant 僅含 tool_calls 時可通過驗證。"""
    client = build_test_client(fake_repo, fake_gateway, fake_logger)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-key"},
        json={
            "model": "fake-model",
            "messages": [
                {"role": "user", "content": "查天氣"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "get_weather", "arguments": '{"city":"TPE"}'},
                        }
                    ],
                },
                {"role": "tool", "tool_call_id": "call_1", "content": "25C"},
            ],
            "stream": False,
        },
    )
    assert response.status_code == 200
    assert fake_gateway.last_nonstream_req is not None
    msgs = fake_gateway.last_nonstream_req.messages
    assert msgs[1].tool_calls is not None
    assert msgs[2].role == "tool"
    assert msgs[2].tool_call_id == "call_1"
