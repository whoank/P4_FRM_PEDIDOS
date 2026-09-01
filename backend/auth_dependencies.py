# auth_dependencies.py
# Dependencia de FastAPI para proteger endpoints que requieren sesion activa.
#
# get_current_user lee la cookie de sesion de la peticion y resuelve el usuario
# reutilizando auth_service.obtener_usuario_por_token. Si no hay sesion valida
# (cookie ausente, token invalido/expirado o usuario inactivo) responde 401.

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth_config import COOKIE_NAME
from database import get_db
from models import User
from auth_service import obtener_usuario_por_token


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> User:
    """Devuelve el usuario autenticado a partir de la cookie de sesion.

    Lee la cookie COOKIE_NAME de la peticion y valida la sesion. Lanza
    HTTPException 401 con un mensaje generico si la sesion no es valida; en caso
    contrario devuelve el objeto User para inyectarlo en los endpoints.
    """
    token = request.cookies.get(COOKIE_NAME)
    usuario = obtener_usuario_por_token(db, token or "")
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado.",
        )
    return usuario
