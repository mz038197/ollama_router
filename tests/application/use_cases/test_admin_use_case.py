import pytest

from src.application.use_cases.admin_use_case import AdminUseCase
from src.domain.errors import AdminBusinessError


def test_get_config_contains_teachers_and_enabled(fake_repo, fake_logger):
    use_case = AdminUseCase(api_key_repo=fake_repo, request_logger=fake_logger)
    data = use_case.get_config()
    assert "teachers" in data
    assert "enabled" in data
    assert data["enabled"] is True
    assert "TeacherA" in data["teachers"]


def test_delete_teacher_not_found_returns_expected_message(fake_repo, fake_logger):
    use_case = AdminUseCase(api_key_repo=fake_repo, request_logger=fake_logger)
    with pytest.raises(AdminBusinessError) as exc_info:
        use_case.delete_teacher("NoSuchTeacher")
    assert exc_info.value.message == "教師不存在: NoSuchTeacher"
    assert exc_info.value.code == "ADMIN_TEACHER_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_add_update_delete_api_key_flow(fake_repo, fake_logger):
    use_case = AdminUseCase(api_key_repo=fake_repo, request_logger=fake_logger)

    add_result = use_case.add_api_key("TeacherA", "ClassC", "new-key", True)
    assert add_result["success"] is True
    assert "已為 TeacherA 新增金鑰: ClassC" == add_result["message"]

    disable_result = use_case.update_api_key_status("TeacherA", "new-key", False)
    assert disable_result == {"success": True, "message": "已禁用金鑰: new-key"}

    delete_result = use_case.delete_api_key("TeacherA", "new-key")
    assert delete_result == {"success": True, "message": "已刪除金鑰: new-key"}


def test_update_api_key_content_flow(fake_repo, fake_logger):
    use_case = AdminUseCase(api_key_repo=fake_repo, request_logger=fake_logger)
    result = use_case.update_api_key(
        teacher_name="TeacherA",
        old_key="valid-key",
        name="ClassA-Edited",
        key="valid-key-updated",
        enabled=False,
    )
    assert result == {"success": True, "message": "已更新金鑰: ClassA-Edited"}
    config = use_case.get_config()
    keys = config["teachers"]["TeacherA"]["api_keys"]
    assert any(k["key"] == "valid-key-updated" and k["name"] == "ClassA-Edited" for k in keys)


def test_get_logs_returns_paginated_result(fake_repo, fake_logger):
    use_case = AdminUseCase(api_key_repo=fake_repo, request_logger=fake_logger)
    fake_logger.log_validation_result(
        teacher_name="TeacherA",
        api_key="valid-key",
        model="fake-model",
        messages=[{"role": "user", "content": "hello"}],
        is_valid=True,
    )

    data = use_case.get_logs(limit=10, offset=0)
    assert "items" in data
    assert "total" in data
    assert "has_more" in data
    assert len(data["items"]) == 1
