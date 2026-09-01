# routers/auth.py
# Router de autenticacion por sesion (cookie). NO lleva prefijo /api; expone:
#   - POST /auth/login   -> valida credenciales, crea sesion y setea la cookie.
#   - GET  /auth/me      -> devuelve el usuario autenticado (401 si no hay sesion).
#   - POST /auth/logout  -> invalida la sesion y borra la cookie.
#
# La cookie es HttpOnly (no accesible por JavaScript) para reducir el riesgo de
# robo de sesion via XSS. Los mensajes de error de login son genericos para no
# revelar si fallo el usuario o la contrasena.

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

# get_db entrega una sesion de base de datos por peticion (database.py).
from database import get_db

# Modelo ORM User (models.py).
from models import User

# Esquemas de request/response de autenticacion (schemas.py).
from schemas import LoginRequest, MensajeRespuesta, UsuarioRespuesta

# Configuracion de la cookie de sesion (auth_config.py).
from auth_config import (
    COOKIE_NAME,
    COOKIE_SAMESITE,
    COOKIE_SECURE,
    SESSION_EXPIRATION_MINUTES,
)

# Logica de autenticacion (auth_service.py).
from auth_service import crear_sesion, invalidar_sesion, verificar_password

# Dependencia que resuelve el usuario autenticado (auth_dependencies.py).
from auth_dependencies import get_current_user

# APIRouter SIN prefijo /api: el modulo de auth vive bajo /auth.
router = APIRouter(prefix="/auth", tags=["auth"])

# Mensaje generico de credenciales invalidas: identico en todos los casos para
# no revelar si el fallo fue el usuario, la contrasena o un usuario inactivo.
MENSAJE_CREDENCIALES = "Usuario o contraseña incorrectos."


# ---------------------------------------------------------------------------
# POST /auth/login -> inicia sesion y setea la cookie
# ---------------------------------------------------------------------------
@router.post("/login", response_model=UsuarioRespuesta)
def login(
    datos: LoginRequest, response: Response, db: Session = Depends(get_db)
) -> User:
    """Valida credenciales y, si son correctas, crea la sesion y setea la cookie.

    Devuelve 401 con un mensaje generico si el usuario no existe, esta inactivo
    o la contrasena no coincide (mismo mensaje en los tres casos).
    """
    # Buscamos el usuario por username (consulta parametrizada via ORM).
    usuario = db.query(User).filter(User.username == datos.username).first()

    # Mismo error para usuario inexistente, inactivo o contrasena incorrecta.
    if (
        usuario is None
        or not usuario.active
        or not verificar_password(datos.password, usuario.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=MENSAJE_CREDENCIALES,
        )

    # Credenciales validas: creamos la sesion (registra last_login) y obtenemos
    # el token en claro para colocarlo en la cookie.
    token = crear_sesion(db, usuario)

    # Cookie HttpOnly con la vida de la sesion. secure/samesite se toman de la
    # configuracion (en desarrollo local COOKIE_SECURE=False por HTTP).
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
        max_age=SESSION_EXPIRATION_MINUTES * 60,
    )
    return usuario


# ---------------------------------------------------------------------------
# GET /auth/me -> usuario autenticado actual
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UsuarioRespuesta)
def me(current_user: User = Depends(get_current_user)) -> User:
    """Devuelve el usuario de la sesion actual.

    get_current_user ya devuelve 401 si no hay una sesion valida, por lo que
    aqui solo hay que retornar el usuario.
    """
    return current_user


# ---------------------------------------------------------------------------
# POST /auth/logout -> cierra la sesion
# ---------------------------------------------------------------------------
@router.post("/logout", response_model=MensajeRespuesta)
def logout(
    request: Request, response: Response, db: Session = Depends(get_db)
) -> MensajeRespuesta:
    """Invalida la sesion (si hay cookie) y borra la cookie del navegador.

    No exige estar autenticado: si hay cookie, se elimina la sesion asociada en
    la base de datos; en cualquier caso se limpia la cookie.
    """
    token = request.cookies.get(COOKIE_NAME)
    if token:
        invalidar_sesion(db, token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return MensajeRespuesta(detail="Sesion cerrada.")
