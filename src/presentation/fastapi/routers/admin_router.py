from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.application.use_cases.admin_use_case import AdminUseCase
from src.domain.errors import AdminBusinessError
from src.presentation.fastapi.schemas.admin import (
    AddKeyRequest,
    AddTeacherRequest,
    DeleteKeyRequest,
    DeleteTeacherRequest,
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
