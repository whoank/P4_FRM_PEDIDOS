# routers/usuarios.py
# Router de la API para la Gestion de Usuarios (extension de Administracion).
#
# Expone el alta, listado, activacion/desactivacion (baja logica) y cambio de
# contrasena de usuarios bajo el prefijo /api/usuarios. Reutiliza el codigo de
# autenticacion existente:
#   - hash_password: para guardar SOLO el hash bcrypt de la contrasena.
#   - invalidar_sesiones_usuario: para cerrar todas las sesiones al desactivar
#     un usuario o cambiarle la contrasena (fuerza a iniciar sesion de nuevo).
#   - get_current_user: dependencia que protege TODOS los endpoints (401 sin
#     sesion valida).
#
# Reglas de seguridad:
#   - Nunca se exponen password_hash ni token_hash: el response_model
#     (UsuarioListado / MensajeRespuesta) no los incluye.
#   - Nunca se registran (log) contrasenas ni hashes.
#   - Todas las consultas son parametrizadas via ORM (nada de SQL crudo).

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# get_db entrega una sesion de base de datos por peticion (database.py).
from database import get_db

# Modelo ORM User (models.py).
from models import User

# Esquemas Pydantic de request/response para la gestion de usuarios (schemas.py).
from schemas import (
    UsuarioCrear,
    UsuarioCambiarPassword,
    UsuarioListado,
    MensajeRespuesta,
)

# Servicios de autenticacion reutilizados: hashing seguro e invalidacion de sesiones.
from auth_service import hash_password, invalidar_sesiones_usuario

# Dependencia de autenticacion: protege todos los endpoints (requiere sesion).
from auth_dependencies import get_current_user

# APIRouter con prefijo comun y etiqueta para la documentacion automatica.
router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------
def _obtener_usuario_o_404(user_id: int, db: Session) -> User:
    """Busca un usuario por id o lanza 404 con mensaje descriptivo."""
    usuario = db.get(User, user_id)
    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario no existe.",
        )
    return usuario


# ---------------------------------------------------------------------------
# GET /api/usuarios -> lista de usuarios
# ---------------------------------------------------------------------------
@router.get("", response_model=list[UsuarioListado])
def listar_usuarios(
    db: Session = Depends(get_db),
    _usuario: User = Depends(get_current_user),
) -> list[User]:
    """Devuelve todos los usuarios ordenados por id.

    Nunca expone password_hash porque el response_model UsuarioListado no lo
    incluye. Si no hay usuarios, devuelve una lista vacia.
    """
    return db.query(User).order_by(User.id).all()


# ---------------------------------------------------------------------------
# POST /api/usuarios -> crea un usuario (201)
# ---------------------------------------------------------------------------
@router.post("", response_model=UsuarioListado, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCrear,
    db: Session = Depends(get_db),
    _usuario: User = Depends(get_current_user),
) -> User:
    """Crea un nuevo usuario activo con la contrasena hasheada (Req. 19).

    Validaciones (todas devuelven 400 con un `detail` claro para el frontend):
      - username obligatorio (no vacio ni solo espacios).
      - password obligatoria.
      - password y password_confirmacion deben coincidir.
      - username unico (no puede estar en uso).
    """
    # username obligatorio: rechazamos vacio o compuesto solo por espacios.
    if not datos.username.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario es obligatorio.",
        )

    # password obligatoria.
    if not datos.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña es obligatoria.",
        )

    # Las dos contrasenas deben coincidir.
    if datos.password != datos.password_confirmacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden.",
        )

    # Unicidad del username (consulta parametrizada via ORM).
    if db.query(User).filter(User.username == datos.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está en uso.",
        )

    # Creamos el usuario: activo por defecto (Req. 19.2) y con hash seguro
    # generado por el mecanismo de autenticacion existente (Req. 19.3).
    usuario = User(
        username=datos.username,
        password_hash=hash_password(datos.password),
        active=True,
    )
    db.add(usuario)
    db.commit()
    # refresh recarga el objeto desde la BD para obtener id y fechas autogeneradas.
    db.refresh(usuario)
    return usuario


# ---------------------------------------------------------------------------
# PATCH /api/usuarios/{id}/activar -> reactiva un usuario
# ---------------------------------------------------------------------------
@router.patch("/{user_id}/activar", response_model=UsuarioListado)
def activar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    _usuario: User = Depends(get_current_user),
) -> User:
    """Marca un usuario como activo (active=True) y lo devuelve; 404 si no existe."""
    usuario = _obtener_usuario_o_404(user_id, db)
    usuario.active = True
    db.commit()
    db.refresh(usuario)
    return usuario


# ---------------------------------------------------------------------------
# PATCH /api/usuarios/{id}/desactivar -> baja logica + invalida sesiones
# ---------------------------------------------------------------------------
@router.patch("/{user_id}/desactivar", response_model=UsuarioListado)
def desactivar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    _usuario: User = Depends(get_current_user),
) -> User:
    """Da de baja logica a un usuario (active=False) e invalida sus sesiones (Req. 21).

    Al desactivar, se eliminan TODAS sus sesiones activas para que no pueda
    seguir operando con una cookie vigente; 404 si el usuario no existe.
    """
    usuario = _obtener_usuario_o_404(user_id, db)
    usuario.active = False
    db.commit()
    # Cerramos todas las sesiones del usuario tras la baja logica.
    invalidar_sesiones_usuario(db, usuario.id)
    db.refresh(usuario)
    return usuario


# ---------------------------------------------------------------------------
# PATCH /api/usuarios/{id}/password -> cambia la contrasena + invalida sesiones
# ---------------------------------------------------------------------------
@router.patch("/{user_id}/password", response_model=MensajeRespuesta)
def cambiar_password(
    user_id: int,
    datos: UsuarioCambiarPassword,
    db: Session = Depends(get_db),
    _usuario: User = Depends(get_current_user),
) -> MensajeRespuesta:
    """Cambia la contrasena de un usuario con hash seguro e invalida sesiones (Req. 22).

    Validaciones (400 con `detail` claro):
      - password y password_confirmacion deben coincidir.
      - password obligatoria.
    Tras actualizar el hash, se cierran todas las sesiones del usuario para
    forzar un nuevo inicio de sesion; 404 si el usuario no existe.
    """
    usuario = _obtener_usuario_o_404(user_id, db)

    # Las dos contrasenas deben coincidir.
    if datos.password != datos.password_confirmacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las contraseñas no coinciden.",
        )

    # password obligatoria.
    if not datos.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña es obligatoria.",
        )

    # Guardamos SOLO el hash (nunca la contrasena en claro) y persistimos.
    usuario.password_hash = hash_password(datos.password)
    db.commit()
    # Cerramos todas las sesiones del usuario tras el cambio de contrasena.
    invalidar_sesiones_usuario(db, usuario.id)
    return MensajeRespuesta(detail="Contraseña actualizada.")
