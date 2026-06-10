from pydantic import BaseModel


class ThemeOut(BaseModel):
    theme_preference: str | None
    theme_custom_color: str | None
    theme_glow_enabled: bool


class ThemePatch(BaseModel):
    theme_preference: str | None = None
    theme_custom_color: str | None = None
    theme_glow_enabled: bool | None = None
