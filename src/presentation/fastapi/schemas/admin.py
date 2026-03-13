from pydantic import BaseModel


class AddTeacherRequest(BaseModel):
    name: str


class DeleteTeacherRequest(BaseModel):
    teacher: str


class AddKeyRequest(BaseModel):
    teacher: str
    name: str
    key: str
    enabled: bool = True


class UpdateKeyStatusRequest(BaseModel):
    teacher: str
    key: str
    enabled: bool = True


class DeleteKeyRequest(BaseModel):
    teacher: str
    key: str
