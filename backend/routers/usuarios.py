# routers/usuarios.py
# Router de la API para la Gestion de Usuarios (extension de Administracion).
#
# Expone el alta, listado, activacion/desactivacion (baja logica) y cambio de
# contrasena de usuarios bajo el prefijo /api/usuarios. Reutiliza el codigo de
# autenticacion existente:
#   - hash_password: para guardar SOLO el hash bcrypt de la contrasena.
#   - invalidar_sesiones_usuario: para cerrar todas las sesiones al desactivar
#     un usuario o cambiarle la contrasena (fuerza a iniciar sesion de nuevo).
#   - require_permission("USUARIOS"): dependencia de autorizacion que protege
#     TODOS los endpoints (401 sin sesion valida + 403 sin el permiso USUARIOS).
#
# Ademas, este router permite asignar un rol al usuario (al crear y mediante
# PATCH /{id}/rol), validando siempre que el rol exista y este ACTIVO.
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
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioCambiarPassword,
    UsuarioListado,
    MensajeRespuesta,
)

# Modelo ORM Role (para validar la asignacion de rol).
from models import Role

# Servicios de autenticacion reutilizados: hashing seguro e invalidacion de sesiones.
from auth_service import hash_password, invalidar_sesiones_usuario

# Invariante de acceso administrativo: el sistema nunca debe quedar sin un
# usuario activo con rol activo que tenga el permiso ROLES.
from roles_service import existe_admin_tras_cambio

# Dependencia de autorizacion: protege todos los endpoints exigiendo el permiso
# "USUARIOS" (require_permission valida sesion 401 + 403 si falta el permiso).
from auth_dependencies import require_permission

# APIRouter con prefijo comun y etiqueta para la documentacion automatica.
router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])

# Mensaje unico cuando una operacion dejaria al sistema sin acceso
# administrativo (sin ningun usuario activo con rol activo que tenga ROLES).
MENSAJE_SIN_ADMIN = (
    "No se puede completar: el sistema quedaría sin ningún usuario "
    "administrador activo con permiso de Roles."
)


# ---------------------------------------------------------------------------
# Helper: convierte un User (ORM) al esquema de listado incluyendo el rol.
# ---------------------------------------------------------------------------
def _a_listado(usuario: User) -> UsuarioListado:
    """Mapea el usuario ORM a UsuarioListado incluyendo role_id y role_nombre.

    role_nombre se deriva de la relacion user.role (None si el usuario no tiene
    rol). Nunca expone password_hash.
    """
    return UsuarioListado(
        id=usuario.id,
        username=usuario.username,
        active=usuario.active,
        created_at=usuario.created_at,
        updated_at=usuario.updated_at,
        last_login=usuario.last_login,
        role_id=usuario.role_id,
        role_nombre=usuario.role.nombre if usuario.role is not None else None,
    )


# ---------------------------------------------------------------------------
# Helper: valida que un role_id (si se envia) exista y este ACTIVO.
# ---------------------------------------------------------------------------
def _validar_rol_activo(role_id: int | None, db: Session) -> None:
    """Valida la asignacion de rol: si role_id no es None, el rol debe existir y

    estar ACTIVO. Un rol inactivo NO puede asignarse (400). Si role_id es None,
    no valida nada (el usuario quedaria sin rol).
    """
    if role_id is None:
        return
    rol = db.get(Role, role_id)
    if rol is None or not rol.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rol seleccionado no existe o no está activo.",
        )


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
    _usuario: User = Depends(require_permission("USUARIOS")),
) -> list[UsuarioListado]:
    """Devuelve todos los usuarios ordenados por id (con su rol).

    Nunca expone password_hash porque el response_model UsuarioListado no lo
    incluye. Incluye role_id y role_nombre. Si no hay usuarios, lista vacia.
    """
    usuarios = db.query(User).order_by(User.id).all()
    return [_a_listado(usuario) for usuario in usuarios]


# ---------------------------------------------------------------------------
# POST /api/usuarios -> crea un usuario (201)
# ---------------------------------------------------------------------------
@router.post("", response_model=UsuarioListado, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    datos: UsuarioCrear,
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("USUARIOS")),
) -> UsuarioListado:
    """Crea un nuevo usuario activo con la contrasena hasheada (Req. 19).

    Validaciones (todas devuelven 400 con un `detail` claro para el frontend):
      - username obligatorio (no vacio ni solo espacios).
      - password obligatoria.
      - password y password_confirmacion deben coincidir.
      - username unico (no puede estar en uso).
      - si se envia role_id, el rol debe existir y estar ACTIVO (un rol
        inactivo no puede asignarse). Si role_id es None, el usuario queda
        sin rol (no se fuerza ninguno).
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

    # Si se envia un rol, debe existir y estar activo (400 si no).
    _validar_rol_activo(datos.role_id, db)

    # Creamos el usuario: activo por defecto (Req. 19.2) y con hash seguro
    # generado por el mecanismo de autenticacion existente (Req. 19.3). El
    # role_id puede ser None (usuario sin rol) o un rol activo ya validado.
    usuario = User(
        username=datos.username,
        password_hash=hash_password(datos.password),
        active=True,
        role_id=datos.role_id,
    )
    db.add(usuario)
    db.commit()
    # refresh recarga el objeto desde la BD para obtener id y fechas autogeneradas.
    db.refresh(usuario)
    return _a_listado(usuario)


# ---------------------------------------------------------------------------
# PATCH /api/usuarios/{id}/activar -> reactiva un usuario
# ---------------------------------------------------------------------------
@router.patch("/{user_id}/activar", response_model=UsuarioListado)
def activar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("USUARIOS")),
) -> UsuarioListado:
    """Marca un usuario como activo (active=True) y lo devuelve; 404 si no existe."""
    usuario = _obtener_usuario_o_404(user_id, db)
    usuario.active = True
    db.commit()
    db.refresh(usuario)
    return _a_listado(usuario)


# ---------------------------------------------------------------------------
# PATCH /api/usuarios/{id}/desactivar -> baja logica + invalida sesiones
# ---------------------------------------------------------------------------
@router.patch("/{user_id}/desactivar", response_model=UsuarioListado)
def desactivar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("USUARIOS")),
) -> UsuarioListado:
    """Da de baja logica a un usuario (active=False) e invalida sus sesiones (Req. 21).

    Al desactivar, se eliminan TODAS sus sesiones activas para que no pueda
    seguir operando con una cookie vigente; 404 si el usuario no existe.
    """
    usuario = _obtener_usuario_o_404(user_id, db)

    # Invariante de acceso administrativo: no permitir desactivar a este usuario
    # si al hacerlo el sistema quedaria sin ningun usuario activo con rol activo
    # que tenga el permiso ROLES. Simulamos el estado resultante (este usuario
    # inactivo) sin aplicar el cambio todavia.
    if not existe_admin_tras_cambio(
        db, usuario_override=(usuario.id, False, usuario.role_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_SIN_ADMIN,
        )

    usuario.active = False
    db.commit()
    # Cerramos todas las sesiones del usuario tras la baja logica.
    invalidar_sesiones_usuario(db, usuario.id)
    db.refresh(usuario)
    return _a_listado(usuario)


# ---------------------------------------------------------------------------
# PATCH /api/usuarios/{id}/password -> cambia la contrasena + invalida sesiones
# ---------------------------------------------------------------------------
@router.patch("/{user_id}/password", response_model=MensajeRespuesta)
def cambiar_password(
    user_id: int,
    datos: UsuarioCambiarPassword,
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("USUARIOS")),
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


# ---------------------------------------------------------------------------
# PATCH /api/usuarios/{id}/rol -> asigna o cambia el rol de un usuario
# ---------------------------------------------------------------------------
# Se anade este endpoint (decision documentada) para cumplir "asignar rol al
# editar usuario" sin existir una edicion general de usuario. Valida que el rol
# exista y este ACTIVO antes de asignarlo; role_id None deja al usuario sin rol.
@router.patch("/{user_id}/rol", response_model=UsuarioListado)
def cambiar_rol_usuario(
    user_id: int,
    datos: UsuarioActualizar,
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("USUARIOS")),
) -> UsuarioListado:
    """Asigna o cambia el rol de un usuario existente (404 si no existe).

    - Si datos.role_id es un id: el rol debe existir y estar ACTIVO (400 si no);
      un rol inactivo NO puede asignarse.
    - Si datos.role_id es None: se deja al usuario sin rol.
    Solo toca el rol (no modifica contrasena ni el estado active aqui).
    """
    usuario = _obtener_usuario_o_404(user_id, db)

    # Valida que, si se envia rol, exista y este activo.
    _validar_rol_activo(datos.role_id, db)

    # Invariante de acceso administrativo: cambiar el rol de este usuario no debe
    # dejar al sistema sin ningun usuario activo con rol activo que tenga ROLES.
    # Simulamos que este usuario queda con el nuevo role_id (conservando su
    # estado active actual).
    if not existe_admin_tras_cambio(
        db, usuario_override=(usuario.id, usuario.active, datos.role_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_SIN_ADMIN,
        )

    usuario.role_id = datos.role_id
    db.commit()
    db.refresh(usuario)
    return _a_listado(usuario)
