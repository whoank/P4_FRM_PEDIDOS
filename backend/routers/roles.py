# routers/roles.py
# Router de la API para la gestion de Roles y Permisos por opcion de menu.
#
# Expone las rutas bajo el prefijo /api:
#   - GET   /api/roles            -> lista todos los roles (con sus permisos).
#   - GET   /api/roles/{id}       -> obtiene un rol (404 si no existe).
#   - POST  /api/roles            -> crea un rol (201).
#   - PUT   /api/roles/{id}       -> actualiza un rol (reemplaza sus permisos).
#   - PATCH /api/roles/{id}/estado-> activa/desactiva un rol (con salvaguarda).
#   - GET   /api/permisos         -> catalogo de permisos (para el formulario).
#
# SEGURIDAD: TODOS los endpoints exigen el permiso "ROLES" (require_permission),
# incluido /api/permisos, que se usa para poblar el formulario de roles. La
# seguridad real vive en el backend, no en el frontend.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# get_db entrega una sesion de base de datos por peticion (database.py).
from database import get_db

# Modelos ORM del modulo de autorizacion.
from models import Permission, Role, User

# Esquemas de request/response de roles y permisos (schemas.py).
from schemas import (
    PermisoRespuesta,
    RolActualizar,
    RolCrear,
    RolEstado,
    RolRespuesta,
)

# Dependencia de autorizacion: exige el permiso "ROLES".
from auth_dependencies import require_permission

# Catalogo de permisos (documenta el conjunto) y la funcion central del
# invariante de acceso administrativo.
from roles_service import (  # noqa: F401  (PERMISOS_MENU documenta el catalogo)
    PERMISOS_MENU,
    existe_admin_tras_cambio,
)

# APIRouter con prefijo /api; las rutas concretas se declaran abajo.
router = APIRouter(prefix="/api", tags=["roles"])

# Mensaje unico cuando una operacion sobre roles dejaria al sistema sin acceso
# administrativo (sin ningun usuario activo con rol activo que tenga ROLES).
MENSAJE_SIN_ADMIN = (
    "No se puede completar: el sistema quedaría sin ningún usuario "
    "administrador activo con permiso de Roles."
)


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _a_respuesta(rol: Role) -> RolRespuesta:
    """Construye el RolRespuesta desde el ORM (con permisos y su cantidad)."""
    permisos = [
        PermisoRespuesta(codigo=permiso.codigo, nombre=permiso.nombre)
        for permiso in rol.permisos
    ]
    return RolRespuesta(
        id=rol.id,
        nombre=rol.nombre,
        descripcion=rol.descripcion,
        activo=rol.activo,
        permisos=permisos,
        cantidad_permisos=len(permisos),
    )


def _obtener_rol_o_404(rol_id: int, db: Session) -> Role:
    """Busca un rol por id o lanza 404 con mensaje descriptivo."""
    rol = db.get(Role, rol_id)
    if rol is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El rol no existe.",
        )
    return rol


def _resolver_permisos(codigos: list[str], db: Session) -> list[Permission]:
    """Valida y resuelve una lista de CODIGOS a objetos Permission.

    - Elimina duplicados (usa set).
    - Si algun codigo no existe en la tabla permissions -> 400.
    Devuelve la lista de Permission correspondiente (puede ser vacia).
    """
    codigos_unicos = set(codigos)
    if not codigos_unicos:
        return []

    encontrados = (
        db.query(Permission).filter(Permission.codigo.in_(codigos_unicos)).all()
    )
    # Si faltan codigos, alguno no es valido.
    if len(encontrados) != len(codigos_unicos):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o más permisos no son válidos.",
        )
    return encontrados


def _validar_nombre_unico(
    nombre: str, db: Session, excluir_id: int | None = None
) -> None:
    """Valida que el nombre de rol no este en uso (400 si ya existe).

    excluir_id permite ignorar el propio rol al actualizar.
    """
    consulta = db.query(Role).filter(Role.nombre == nombre)
    if excluir_id is not None:
        consulta = consulta.filter(Role.id != excluir_id)
    if consulta.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un rol con ese nombre.",
        )


# ---------------------------------------------------------------------------
# GET /api/roles -> lista de roles con permisos
# ---------------------------------------------------------------------------
@router.get("/roles", response_model=list[RolRespuesta])
def listar_roles(
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("ROLES")),
) -> list[RolRespuesta]:
    """Devuelve todos los roles con sus permisos y la cantidad de permisos."""
    roles = db.query(Role).order_by(Role.id).all()
    return [_a_respuesta(rol) for rol in roles]


# ---------------------------------------------------------------------------
# GET /api/roles/{id} -> detalle de un rol
# ---------------------------------------------------------------------------
@router.get("/roles/{rol_id}", response_model=RolRespuesta)
def obtener_rol(
    rol_id: int,
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("ROLES")),
) -> RolRespuesta:
    """Devuelve un rol por su id; 404 si no existe."""
    rol = _obtener_rol_o_404(rol_id, db)
    return _a_respuesta(rol)


# ---------------------------------------------------------------------------
# POST /api/roles -> crea un rol (201)
# ---------------------------------------------------------------------------
@router.post("/roles", response_model=RolRespuesta, status_code=status.HTTP_201_CREATED)
def crear_rol(
    datos: RolCrear,
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("ROLES")),
) -> RolRespuesta:
    """Crea un rol validando nombre unico y permisos existentes.

    Validaciones (400 con detail claro):
      - nombre obligatorio (no vacio tras strip).
      - nombre unico.
      - cada codigo de permiso debe existir en el catalogo.
    """
    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre del rol es obligatorio.",
        )

    _validar_nombre_unico(nombre, db)
    permisos = _resolver_permisos(datos.permisos, db)

    rol = Role(
        nombre=nombre,
        descripcion=datos.descripcion,
        activo=datos.activo,
    )
    rol.permisos = permisos
    db.add(rol)
    db.commit()
    db.refresh(rol)
    return _a_respuesta(rol)


# ---------------------------------------------------------------------------
# PUT /api/roles/{id} -> actualiza un rol (reemplaza permisos)
# ---------------------------------------------------------------------------
@router.put("/roles/{rol_id}", response_model=RolRespuesta)
def actualizar_rol(
    rol_id: int,
    datos: RolActualizar,
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("ROLES")),
) -> RolRespuesta:
    """Actualiza nombre, descripcion, activo y REEMPLAZA el conjunto de permisos.

    404 si el rol no existe. Valida nombre unico (excluyendo el propio id) y que
    todos los codigos de permiso existan.
    """
    rol = _obtener_rol_o_404(rol_id, db)

    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre del rol es obligatorio.",
        )

    _validar_nombre_unico(nombre, db, excluir_id=rol.id)
    permisos = _resolver_permisos(datos.permisos, db)

    # Invariante de acceso administrativo: editar el rol (cambiar su estado
    # `activo` o quitarle el permiso ROLES) no debe dejar al sistema sin ningun
    # usuario activo con rol activo que tenga ROLES. Simulamos el estado
    # resultante de ESTE rol (nuevo `activo` y nuevo conjunto de codigos).
    codigos_resultantes = {permiso.codigo for permiso in permisos}
    if not existe_admin_tras_cambio(
        db, rol_override=(rol.id, datos.activo, codigos_resultantes)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_SIN_ADMIN,
        )

    rol.nombre = nombre
    rol.descripcion = datos.descripcion
    rol.activo = datos.activo
    # Reemplazo completo del conjunto de permisos por el enviado.
    rol.permisos = permisos
    db.commit()
    db.refresh(rol)
    return _a_respuesta(rol)


# ---------------------------------------------------------------------------
# PATCH /api/roles/{id}/estado -> activa/desactiva un rol (con salvaguarda)
# ---------------------------------------------------------------------------
@router.patch("/roles/{rol_id}/estado", response_model=RolRespuesta)
def cambiar_estado_rol(
    rol_id: int,
    datos: RolEstado,
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("ROLES")),
) -> RolRespuesta:
    """Activa o desactiva un rol, protegiendo el invariante de acceso administrativo.

    REGLA (obligatoria): el sistema NUNCA debe quedar sin al menos un usuario
    ACTIVO con un ROL ACTIVO que contenga el permiso ROLES. Al DESACTIVAR un rol
    se comprueba, mediante la funcion central existe_admin_tras_cambio, que tras
    el cambio siga existiendo ese acceso; si no, se rechaza con 400. Activar un
    rol nunca reduce el acceso, por lo que no requiere comprobacion.
    """
    rol = _obtener_rol_o_404(rol_id, db)

    # Solo hay riesgo al DESACTIVAR (activar nunca reduce el acceso). Simulamos
    # que este rol queda inactivo, conservando su conjunto de permisos actual.
    if not datos.activo and rol.activo:
        codigos_actuales = {permiso.codigo for permiso in rol.permisos}
        if not existe_admin_tras_cambio(
            db, rol_override=(rol.id, False, codigos_actuales)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=MENSAJE_SIN_ADMIN,
            )

    rol.activo = datos.activo
    db.commit()
    db.refresh(rol)
    return _a_respuesta(rol)


# ---------------------------------------------------------------------------
# GET /api/permisos -> catalogo de permisos (para el formulario de roles)
# ---------------------------------------------------------------------------
@router.get("/permisos", response_model=list[PermisoRespuesta])
def listar_permisos(
    db: Session = Depends(get_db),
    _usuario: User = Depends(require_permission("ROLES")),
) -> list[Permission]:
    """Devuelve todos los permisos ACTIVOS (codigo + nombre) del catalogo.

    Se usa para poblar el formulario de creacion/edicion de roles. Protegido con
    el permiso "ROLES" porque solo quien gestiona roles necesita este catalogo.
    """
    return (
        db.query(Permission)
        .filter(Permission.activo.is_(True))
        .order_by(Permission.id)
        .all()
    )
