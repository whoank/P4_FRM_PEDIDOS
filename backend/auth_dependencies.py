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

# Consulta de permisos efectivos del usuario. roles_service importa SOLO de
# models y sqlalchemy (nunca de este modulo), por lo que no hay ciclo de
# importacion: auth_dependencies -> roles_service -> models.
from roles_service import permisos_de_usuario


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


def require_permission(codigo: str):
    """Fabrica de dependencia que exige un permiso concreto por su codigo.

    La SEGURIDAD REAL vive aqui, en el backend: aunque el frontend oculte o
    muestre opciones de menu segun los permisos, esa capa es solo de comodidad
    (UX) y puede ser manipulada. Todo endpoint protegido comprueba el permiso en
    el servidor antes de ejecutar la logica.

    Uso: `Depends(require_permission("CLIENTES"))` en la firma del endpoint.

    Comportamiento:
      - get_current_user ya garantiza 401 si no hay sesion valida.
      - Si el usuario autenticado no posee el codigo requerido en sus permisos
        efectivos (rol activo + permisos activos) -> 403.
      - En caso contrario devuelve el usuario, por si el endpoint quiere usarlo.
    """

    def dependencia(
        request: Request,
        db: Session = Depends(get_db),
        usuario: User = Depends(get_current_user),
    ) -> User:
        permisos = permisos_de_usuario(db, usuario)
        if codigo not in permisos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para realizar esta acción.",
            )
        return usuario

    return dependencia
