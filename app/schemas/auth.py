from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh: str


class TokenResponse(BaseModel):
    access: str
    refresh: str


class AccessTokenResponse(BaseModel):
    access: str


class FcmTokenUpdate(BaseModel):
    fcm_token: str | None = None
