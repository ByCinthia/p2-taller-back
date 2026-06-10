from pydantic import BaseModel, EmailStr, Field


class RegisterCompanyRequest(BaseModel):
    empresa_nombre: str = Field(max_length=100)
    empresa_nit: str = Field(max_length=20)
    empresa_email: EmailStr | None = None
    empresa_telefono: str | None = Field(default=None, max_length=20)
    empresa_direccion: str | None = Field(default=None, max_length=255)

    card_number: str | None = None
    card_expiry: str | None = None
    card_cvc: str | None = None
    plan: str = "basico"


class RegisterCompanyResponse(BaseModel):
    empresa_id: str
    empresa_nombre: str
    registration_token: str


class RegisterAdminRequest(BaseModel):
    registration_token: str

    admin_username: str = Field(max_length=100)
    admin_password: str
    admin_first_name: str = Field(max_length=100)
    admin_email: EmailStr
    admin_ci: str = Field(max_length=20)
    admin_apellido_p: str = Field(max_length=100)
    admin_apellido_m: str = Field(default="", max_length=100)


class RegisterEmpresaRequest(BaseModel):
    empresa_nombre: str = Field(max_length=100)
    empresa_nit: str = Field(max_length=20)
    empresa_email: EmailStr | None = None
    empresa_telefono: str | None = Field(default=None, max_length=20)
    empresa_direccion: str | None = Field(default=None, max_length=255)

    admin_username: str = Field(max_length=100)
    admin_password: str
    admin_first_name: str = Field(max_length=100)
    admin_email: EmailStr
    admin_ci: str = Field(max_length=20)
    admin_apellido_p: str = Field(max_length=100)
    admin_apellido_m: str = Field(default="", max_length=100)

    card_number: str | None = None
    card_expiry: str | None = None
    card_cvc: str | None = None
    plan: str = "basico"
