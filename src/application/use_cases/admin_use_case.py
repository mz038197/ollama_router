from typing import Any

from src.domain.errors import AdminBusinessError
from src.domain.ports.api_key_repository import ApiKeyRepositoryPort


class AdminUseCase:
    def __init__(self, api_key_repo: ApiKeyRepositoryPort):
        self.api_key_repo = api_key_repo

    def get_config(self) -> dict[str, Any]:
        data = self.api_key_repo.get_all_config()
        return {"teachers": data, "enabled": self.api_key_repo.is_enabled()}

    def add_teacher(self, teacher_name: str) -> dict[str, Any]:
        self.api_key_repo.add_teacher(teacher_name)
        return {"success": True, "message": f"已新增教師: {teacher_name}"}

    def delete_teacher(self, teacher_name: str) -> dict[str, Any]:
        ok = self.api_key_repo.delete_teacher(teacher_name)
        if not ok:
            raise AdminBusinessError(
                message=f"教師不存在: {teacher_name}",
                code="ADMIN_TEACHER_NOT_FOUND",
                status_code=404,
            )
        return {"success": True, "message": f"已刪除教師: {teacher_name}"}

    def add_api_key(self, teacher_name: str, name: str, key: str, enabled: bool) -> dict[str, Any]:
        self.api_key_repo.add_api_key(teacher_name, name, key, enabled)
        return {"success": True, "message": f"已為 {teacher_name} 新增金鑰: {name}"}

    def update_api_key_status(self, teacher_name: str, key: str, enabled: bool) -> dict[str, Any]:
        ok = self.api_key_repo.update_api_key_status(teacher_name, key, enabled)
        if not ok:
            if teacher_name not in self.api_key_repo.get_all_config():
                raise AdminBusinessError(
                    message=f"教師不存在: {teacher_name}",
                    code="ADMIN_TEACHER_NOT_FOUND",
                    status_code=404,
                )
            raise AdminBusinessError(
                message=f"金鑰不存在: {key}",
                code="ADMIN_KEY_NOT_FOUND",
                status_code=404,
            )
        status = "啟用" if enabled else "禁用"
        return {"success": True, "message": f"已{status}金鑰: {key}"}

    def delete_api_key(self, teacher_name: str, key: str) -> dict[str, Any]:
        ok = self.api_key_repo.delete_api_key(teacher_name, key)
        if not ok:
            if teacher_name not in self.api_key_repo.get_all_config():
                raise AdminBusinessError(
                    message=f"教師不存在: {teacher_name}",
                    code="ADMIN_TEACHER_NOT_FOUND",
                    status_code=404,
                )
            raise AdminBusinessError(
                message=f"金鑰不存在: {key}",
                code="ADMIN_KEY_NOT_FOUND",
                status_code=404,
            )
        return {"success": True, "message": f"已刪除金鑰: {key}"}
