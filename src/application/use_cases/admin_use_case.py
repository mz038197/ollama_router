from typing import Any

from src.domain.errors import AdminBusinessError
from src.domain.ports.api_key_repository import ApiKeyRepositoryPort
from src.domain.ports.request_log import RequestLogPort


class AdminUseCase:
    def __init__(
        self,
        api_key_repo: ApiKeyRepositoryPort,
        request_logger: RequestLogPort | None = None,
    ):
        self.api_key_repo = api_key_repo
        self.request_logger = request_logger

    def get_config(self) -> dict[str, Any]:
        data = self.api_key_repo.get_all_config()
        return {"teachers": data, "enabled": self.api_key_repo.is_enabled()}

    def get_logs(
        self,
        date: str | None = None,
        teacher: str | None = None,
        model: str | None = None,
        is_valid: bool | None = None,
        keyword: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        if not self.request_logger:
            return {"items": [], "total": 0, "has_more": False}

        safe_limit = max(1, min(limit, 200))
        safe_offset = max(offset, 0)
        return self.request_logger.query_logs(
            date=date,
            teacher=teacher,
            model=model,
            is_valid=is_valid,
            keyword=keyword,
            limit=safe_limit,
            offset=safe_offset,
        )

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

    def update_api_key(
        self,
        teacher_name: str,
        old_key: str,
        name: str,
        key: str,
        enabled: bool,
    ) -> dict[str, Any]:
        ok = self.api_key_repo.update_api_key(teacher_name, old_key, name, key, enabled)
        if not ok:
            if teacher_name not in self.api_key_repo.get_all_config():
                raise AdminBusinessError(
                    message=f"教師不存在: {teacher_name}",
                    code="ADMIN_TEACHER_NOT_FOUND",
                    status_code=404,
                )
            raise AdminBusinessError(
                message=f"金鑰不存在: {old_key}",
                code="ADMIN_KEY_NOT_FOUND",
                status_code=404,
            )
        return {"success": True, "message": f"已更新金鑰: {name}"}

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
