from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import settings

_jwk_client = PyJWKClient(settings.jwks_url, cache_keys=True)

_bearer = HTTPBearer(auto_error=False)

_CREDENCIALES_INVALIDAS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token inválido o expirado",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass(frozen=True)
class CurrentUser:

    id: str
    email: str | None
    token: str


def _decodificar(token: str) -> dict:
    
    try:
        clave = _jwk_client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            clave,
            algorithms=["ES256", "RS256", "HS256"],
            audience="authenticated",
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise _CREDENCIALES_INVALIDAS from exc


def get_current_user(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
   
    if credenciales is None:
        raise _CREDENCIALES_INVALIDAS

    claims = _decodificar(credenciales.credentials)
    user_id = claims.get("sub")
    if not user_id:
        raise _CREDENCIALES_INVALIDAS

    return CurrentUser(
        id=user_id,
        email=claims.get("email"),
        token=credenciales.credentials,
    )