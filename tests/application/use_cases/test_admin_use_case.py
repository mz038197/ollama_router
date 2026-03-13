import pytest

from src.application.use_cases.admin_use_case import AdminUseCase
from src.domain.errors import AdminBusinessError


def test_get_config_contains_teachers_and_enabled(fake_repo):
    use_case = AdminUseCase(api_key_repo=fake_repo)
    data = use_case.get_config()
    assert "teachers" in data
    assert "enabled" in data
    assert data["enabled"] is True
    assert "TeacherA" in data["teachers"]


def test_delete_teacher_not_found_returns_expected_message(fake_repo):
    use_case = AdminUseCase(api_key_repo=fake_repo)
    with pytest.raises(AdminBusinessError) as exc_info:
        use_case.delete_teacher("NoSuchTeacher")
    assert exc_info.value.message == "教師不存在: NoSuchTeacher"
    assert exc_info.value.code == "ADMIN_TEACHER_NOT_FOUND"
    assert exc_info.value.status_code == 404


def test_add_update_delete_api_key_flow(fake_repo):
    use_case = AdminUseCase(api_key_repo=fake_repo)

    add_result = use_case.add_api_key("TeacherA", "ClassC", "new-key", True)
    assert add_result["success"] is True
    assert "已為 TeacherA 新增金鑰: ClassC" == add_result["message"]

    disable_result = use_case.update_api_key_status("TeacherA", "new-key", False)
    assert disable_result == {"success": True, "message": "已禁用金鑰: new-key"}

    delete_result = use_case.delete_api_key("TeacherA", "new-key")
    assert delete_result == {"success": True, "message": "已刪除金鑰: new-key"}
