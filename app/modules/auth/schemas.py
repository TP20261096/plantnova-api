from pydantic import BaseModel, EmailStr, Field


class RegistroRequest(BaseModel):
    #Datos para crear una cuenta.

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    nombre: str = Field(min_length=2, max_length=60)


class LoginRequest(BaseModel):
    #Credenciales de acceso.

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class RefreshRequest(BaseModel):
    #Token de refresco emitido junto al de acceso.

    refresh_token: str


class UsuarioResponse(BaseModel):
    #Identidad del usuario autenticado.

    id: str
    email: str | None
    nombre: str | None


class SesionResponse(BaseModel):
    
    access_token: str
    refresh_token: str
    expires_in: int
    usuario: UsuarioResponse