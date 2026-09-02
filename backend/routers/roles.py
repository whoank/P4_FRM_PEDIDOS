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

# Codigo de permiso que protege este modulo (gestion de roles).
from roles_service import PERMISOS_MENU  # noqa: F401  (documenta el catalogo)

# APIRouter con prefijo /api; las rutas concretas se declaran abajo.
router = APIRouter(prefix="/api", tags=["roles"])


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
    """Activa o desactiva un rol, con una salvaguarda de acceso administrativo.

    REGLA DE SALVAGUARDA (documentada): no se permite DESACTIVAR un rol si es el
    UNICO rol activo que otorga el permiso "ROLES" a al menos un usuario ACTIVO.
    Es decir, si al desactivarlo el sistema quedaria sin ningun rol activo (con
    "ROLES") asignado a un usuario activo, se rechaza con 400. Asi se evita
    bloquear el acceso a la propia gestion de roles/usuarios.
    Activar un rol siempre es seguro.
    """
    rol = _obtener_rol_o_404(rol_id, db)

    # Solo hay riesgo al DESACTIVAR (activar nunca reduce el acceso).
    if not datos.activo and rol.activo:
        # ?Este rol otorga actualmente el permiso "ROLES"?
        rol_da_roles = any(
            permiso.codigo == "ROLES" and permiso.activo for permiso in rol.permisos
        )
        if rol_da_roles:
            # ?Hay al menos un usuario activo con este rol? (dependen de el)
            hay_usuario_activo = (
                db.query(User)
                .filter(User.role_id == rol.id, User.active.is_(True))
                .first()
                is not None
            )
            if hay_usuario_activo:
                # ?Existe OTRO rol activo que tambien otorgue "ROLES" a algun
                # usuario activo? Si no, este es el unico soporte de acceso.
                otro_soporte = False
                otros_roles = (
                    db.query(Role)
                    .filter(Role.id != rol.id, Role.activo.is_(True))
                    .all()
                )
                for otro in otros_roles:
                    otorga_roles = any(
                        p.codigo == "ROLES" and p.activo for p in otro.permisos
                    )
                    if not otorga_roles:
                        continue
                    tiene_usuario_activo = (
                        db.query(User)
                        .filter(User.role_id == otro.id, User.active.is_(True))
                        .first()
                        is not None
                    )
                    if tiene_usuario_activo:
                        otro_soporte = True
                        break

                if not otro_soporte:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No se puede desactivar: el sistema quedaría sin acceso administrativo.",
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
