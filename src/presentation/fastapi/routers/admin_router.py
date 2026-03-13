from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from src.application.use_cases.admin_use_case import AdminUseCase
from src.domain.errors import AdminBusinessError
from src.presentation.fastapi.schemas.admin import (
    AddKeyRequest,
    AddTeacherRequest,
    DeleteKeyRequest,
    DeleteTeacherRequest,
    UpdateKeyRequest,
    UpdateKeyStatusRequest,
)

ADMIN_HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "admin.html"


def create_admin_router(admin_use_case: AdminUseCase) -> APIRouter:
    router = APIRouter(tags=["Admin"])

    @router.get("/")
    async def admin_panel():
        with open(ADMIN_HTML_PATH, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)

    @router.get("/api/admin/config")
    async def get_admin_config():
        return admin_use_case.get_config()

    @router.get("/api/admin/logs")
    async def get_admin_logs(
        date: str | None = Query(default=None, description="查詢日期，格式 YYYYMMDD"),
        teacher: str | None = Query(default=None, description="教師名稱"),
        model: str | None = Query(default=None, description="模型名稱"),
        is_valid: bool | None = Query(default=None, description="驗證結果（true/false）"),
        keyword: str | None = Query(default=None, description="訊息關鍵字"),
        limit: int = Query(default=50, ge=1, le=200, description="回傳筆數上限"),
        offset: int = Query(default=0, ge=0, description="分頁偏移"),
    ):
        return admin_use_case.get_logs(
            date=date,
            teacher=teacher,
            model=model,
            is_valid=is_valid,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )

    @router.post("/api/admin/teacher/add", status_code=201)
    async def add_teacher_admin(data: AddTeacherRequest):
        teacher_name = data.name.strip()
        if not teacher_name:
            raise AdminBusinessError(
                message="教師名稱不能為空",
                code="ADMIN_INVALID_TEACHER_NAME",
                status_code=400,
            )
        return admin_use_case.add_teacher(teacher_name)

    @router.post("/api/admin/teacher/delete")
    async def delete_teacher_admin(data: DeleteTeacherRequest):
        teacher_name = data.teacher.strip()
        if not teacher_name:
            raise AdminBusinessError(
                message="教師名稱不能為空",
                code="ADMIN_INVALID_TEACHER_NAME",
                status_code=400,
            )
        return admin_use_case.delete_teacher(teacher_name)

    @router.post("/api/admin/key/add", status_code=201)
    async def add_key_admin(data: AddKeyRequest):
        teacher = data.teacher.strip()
        name = data.name.strip()
        key = data.key.strip()
        if not teacher or not name or not key:
            raise AdminBusinessError(
                message="請提供完整的教師名稱、班級名稱和金鑰",
                code="ADMIN_INVALID_KEY_INPUT",
                status_code=400,
            )
        return admin_use_case.add_api_key(teacher, name, key, data.enabled)

    @router.post("/api/admin/key/update")
    async def update_key_admin(data: UpdateKeyRequest):
        teacher = data.teacher.strip()
        old_key = data.old_key.strip()
        name = data.name.strip()
        key = data.key.strip()
        if not teacher or not old_key or not name or not key:
            raise AdminBusinessError(
                message="請提供完整的教師名稱、舊金鑰、班級名稱和新金鑰",
                code="ADMIN_INVALID_KEY_INPUT",
                status_code=400,
            )
        return admin_use_case.update_api_key(teacher, old_key, name, key, data.enabled)

    @router.post("/api/admin/key/status")
    async def update_key_status_admin(data: UpdateKeyStatusRequest):
        teacher = data.teacher.strip()
        key = data.key.strip()
        if not teacher or not key:
            raise AdminBusinessError(
                message="教師和金鑰不能為空",
                code="ADMIN_INVALID_KEY_INPUT",
                status_code=400,
            )
        return admin_use_case.update_api_key_status(teacher, key, data.enabled)

    @router.post("/api/admin/key/delete")
    async def delete_key_admin(data: DeleteKeyRequest):
        teacher = data.teacher.strip()
        key = data.key.strip()
        if not teacher or not key:
            raise AdminBusinessError(
                message="教師和金鑰不能為空",
                code="ADMIN_INVALID_KEY_INPUT",
                status_code=400,
            )
        return admin_use_case.delete_api_key(teacher, key)

    return router
