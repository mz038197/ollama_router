from pathlib import Path

from fastapi import APIRouter, Cookie, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.application.use_cases.portal_use_case import PortalUseCase

PORTAL_HTML_PATH = Path(__file__).resolve().parent.parent / "web" / "portal.html"


class GoogleLoginRequest(BaseModel):
    email: str
    name: str
    google_sub: str | None = None


class ClassRequest(BaseModel):
    name: str
    ends_at: str | None = None
    api_key_ttl_hours: int | None = None


class RedeemRequest(BaseModel):
    invite_code: str


class UserPatchRequest(BaseModel):
    role: str | None = None
    status: str | None = None


class ClassPatchRequest(BaseModel):
    status: str


class SettingsPatchRequest(BaseModel):
    retention_days: int | None = None
    student_default_ttl_hours: int | None = None
    open_registration: bool | None = None


def create_portal_router(portal_use_case: PortalUseCase) -> APIRouter:
    router = APIRouter(tags=["Portal"])

    def portal_call(fn):
        try:
            return fn()
        except PermissionError:
            raise HTTPException(status_code=403, detail="權限不足") from None
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None

    def current_user_id(session_user_id: str | None) -> int:
        if not session_user_id:
            raise HTTPException(status_code=401, detail="尚未登入")
        return int(session_user_id)

    @router.get("/portal", response_class=HTMLResponse)
    async def portal_page():
        return HTMLResponse(PORTAL_HTML_PATH.read_text(encoding="utf-8"))

    @router.post("/auth/google")
    async def google_login(data: GoogleLoginRequest, response: Response):
        user = portal_use_case.google_login(data.email, data.name, data.google_sub)
        response.set_cookie("session_user_id", str(user["id"]), httponly=True, samesite="lax")
        return {"user": user}

    @router.get("/auth/me")
    async def me(session_user_id: str | None = Cookie(default=None)):
        user = portal_use_case.me(current_user_id(session_user_id))
        if not user:
            raise HTTPException(status_code=404, detail="找不到使用者")
        return user

    @router.post("/auth/logout")
    async def logout(response: Response):
        response.delete_cookie("session_user_id")
        return {"success": True}

    @router.post("/portal/teacher/api-key")
    async def teacher_key(session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: portal_use_case.teacher_key(current_user_id(session_user_id)))

    @router.post("/teacher/classes")
    async def create_class(data: ClassRequest, session_user_id: str | None = Cookie(default=None)):
        return portal_call(
            lambda: portal_use_case.create_class(
                current_user_id(session_user_id),
                data.name.strip(),
                data.ends_at,
                data.api_key_ttl_hours,
            )
        )

    @router.get("/teacher/classes")
    async def list_my_classes(session_user_id: str | None = Cookie(default=None)):
        user = portal_use_case.me(current_user_id(session_user_id))
        return {"items": user.get("classes", []) if user else []}

    @router.post("/teacher/classes/{class_id}/sessions")
    async def create_session(class_id: int, session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: portal_use_case.create_session(current_user_id(session_user_id), class_id))

    @router.get("/teacher/classes/{class_id}/redemptions")
    async def class_redemptions(class_id: int, session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: {"items": portal_use_case.redemptions(current_user_id(session_user_id), class_id)})

    @router.get("/teacher/classes/{class_id}/prompt-logs")
    async def prompt_logs(
        class_id: int,
        session_id: int | None = None,
        keyword: str | None = None,
        start_at: str | None = None,
        end_at: str | None = None,
        session_user_id: str | None = Cookie(default=None),
    ):
        return portal_call(
            lambda: {
                "items": portal_use_case.prompt_logs(
                    current_user_id(session_user_id),
                    class_id,
                    session_id,
                    keyword,
                    start_at,
                    end_at,
                )
            }
        )

    @router.post("/sessions/redeem")
    async def redeem(data: RedeemRequest, session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: portal_use_case.redeem(current_user_id(session_user_id), data.invite_code))

    @router.get("/admin/users")
    async def admin_users(session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: {"items": portal_use_case.admin_users(current_user_id(session_user_id))})

    @router.patch("/admin/users/{user_id}")
    async def admin_update_user(user_id: int, data: UserPatchRequest, session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: portal_use_case.admin_update_user(current_user_id(session_user_id), user_id, data.role, data.status))

    @router.get("/admin/classes")
    async def admin_classes(session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: {"items": portal_use_case.admin_classes(current_user_id(session_user_id))})

    @router.patch("/admin/classes/{class_id}")
    async def admin_update_class(class_id: int, data: ClassPatchRequest, session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: portal_use_case.admin_update_class(current_user_id(session_user_id), class_id, data.status))

    @router.get("/admin/settings")
    async def admin_settings(session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: portal_use_case.admin_settings(current_user_id(session_user_id)))

    @router.patch("/admin/settings")
    async def admin_update_settings(data: SettingsPatchRequest, session_user_id: str | None = Cookie(default=None)):
        return portal_call(
            lambda: portal_use_case.admin_update_settings(
                current_user_id(session_user_id),
                retention_days=data.retention_days,
                student_default_ttl_hours=data.student_default_ttl_hours,
                open_registration=data.open_registration,
            )
        )

    @router.post("/admin/archive/run")
    async def admin_archive_run(session_user_id: str | None = Cookie(default=None)):
        return portal_call(lambda: portal_use_case.admin_run_archive(current_user_id(session_user_id)))

    return router
