# roles_service.py
# Logica de acceso a datos y de negocio del modulo de Roles y Permisos por
# opcion de menu (autorizacion).
#
# Decision de esquema (IMPORTANTE): este proyecto NO usa Alembic. El esquema se
# crea con Base.metadata.create_all() (models.crear_tablas(), invocado en el
# lifespan de main.py). Los datos iniciales de este modulo (catalogo de
# permisos, rol "Administrador" y asignacion de rol a usuarios previos) se
# siembran con seed_roles_y_permisos(), una funcion IDEMPOTENTE que puede
# ejecutarse en cada arranque sin duplicar nada. Asi evitamos migraciones y
# mantenemos el patron ya existente (create_all + seed idempotente, como
# auth_service.crear_usuario_inicial).
#
# Este modulo importa SOLO de models y sqlalchemy (nunca de auth_dependencies),
# para evitar ciclos de importacion: auth_dependencies importa de aqui.
#
# Reglas de seguridad: nunca se registran (log) contrasenas ni datos sensibles.
# El "codigo" de un permiso es el identificador de seguridad interno; el
# "nombre" es solo la etiqueta visible en la interfaz.

from sqlalchemy.orm import Session

from models import Permission, Role, User

# Codigo del permiso que habilita la gestion de Roles (y, por extension, el
# acceso administrativo minimo que el sistema NUNCA debe perder).
PERMISO_ROLES = "ROLES"


# ---------------------------------------------------------------------------
# Catalogo de permisos del menu
# ---------------------------------------------------------------------------
# Cada tupla es (codigo interno de seguridad, nombre visible en el menu).
# La opcion "Inicio" NO lleva permiso: es la landing general accesible a
# cualquier usuario autenticado, por eso no aparece aqui.
PERMISOS_MENU: list[tuple[str, str]] = [
    ("CLIENTES", "Clientes"),
    ("PRODUCTOS", "Productos"),
    ("PEDIDOS", "Pedidos"),
    ("REPORTE_DIARIO", "Reporte diario"),
    ("ADMINISTRACION", "Administración"),
    ("USUARIOS", "Gestión de Usuarios"),
    ("ROLES", "Roles"),
]

# Nombre del rol de administracion sembrado por defecto.
ROL_ADMINISTRADOR = "Administrador"


# ---------------------------------------------------------------------------
# Consultas de permisos
# ---------------------------------------------------------------------------
def permisos_de_usuario(db: Session, user: User) -> set[str]:
    """Devuelve el conjunto de codigos de permiso efectivos de un usuario.

    Reglas:
      - Si el usuario no tiene rol (role_id NULL / role None) -> set() vacio.
      - Si el rol del usuario esta inactivo -> set() vacio (no otorga acceso).
      - Solo se consideran los permisos activos del rol.
    Todas las consultas se resuelven via ORM (relaciones), sin SQL crudo.
    """
    if user is None:
        return set()

    rol = user.role
    # Sin rol o rol inactivo: el usuario no tiene ningun permiso.
    if rol is None or not rol.activo:
        return set()

    # Solo permisos activos del rol.
    return {permiso.codigo for permiso in rol.permisos if permiso.activo}


def codigos_permisos_validos(db: Session) -> set[str]:
    """Devuelve el conjunto de codigos existentes en la tabla permissions.

    Se usa para validar que los codigos enviados al crear/actualizar un rol
    correspondan realmente a permisos del catalogo.
    """
    filas = db.query(Permission.codigo).all()
    return {codigo for (codigo,) in filas}


# ---------------------------------------------------------------------------
# Invariante de acceso administrativo (funcion central)
# ---------------------------------------------------------------------------
# REGLA (obligatoria): el sistema NUNCA debe quedar sin al menos UN usuario
# ACTIVO con un ROL ACTIVO que contenga el permiso "ROLES". Si se pierde, nadie
# podria volver a entrar a la gestion de Roles/Usuarios y el sistema quedaria
# bloqueado administrativamente.
#
# Esta funcion es la UNICA fuente de verdad del invariante. La invocan las
# cuatro operaciones que podrian romperlo:
#   1. Desactivar un usuario (usuarios: desactivar).
#   2. Cambiar el rol de un usuario (usuarios: cambiar rol).
#   3. Editar un rol (roles: PUT) quitandole ROLES o desactivandolo.
#   4. Desactivar un rol (roles: PATCH estado).
#
# Para poder evaluar el estado *resultante* de un cambio ANTES de aplicarlo (sin
# depender de commits), acepta "overrides" hipoteticos que describen el cambio
# propuesto:
#   - usuario_override = (user_id, activo, role_id): simula que ese usuario
#     quedaria con ese `activo` y ese `role_id`.
#   - rol_override = (role_id, activo, codigos_permisos): simula que ese rol
#     quedaria con ese `activo` y ese conjunto de codigos de permiso.
# Cualquiera puede ser None (sin override para esa entidad).


def _rol_otorga_roles(
    rol: Role, rol_override: tuple[int, bool, set[str]] | None
) -> bool:
    """Indica si un rol (considerando un posible override) esta ACTIVO y otorga ROLES.

    Si `rol_override` corresponde a este rol, se usan el `activo` y los codigos
    del override (estado hipotetico tras el cambio); en caso contrario se usa el
    estado real del rol en la BD.
    """
    if rol_override is not None and rol_override[0] == rol.id:
        _, activo_hipotetico, codigos_hipoteticos = rol_override
        return activo_hipotetico and (PERMISO_ROLES in codigos_hipoteticos)

    # Estado real: rol activo con el permiso ROLES activo entre sus permisos.
    if not rol.activo:
        return False
    return any(
        permiso.codigo == PERMISO_ROLES and permiso.activo
        for permiso in rol.permisos
    )


def existe_admin_tras_cambio(
    db: Session,
    usuario_override: tuple[int, bool, int | None] | None = None,
    rol_override: tuple[int, bool, set[str]] | None = None,
) -> bool:
    """Indica si, tras el cambio propuesto, seguiria existiendo acceso administrativo.

    Devuelve True si existe al menos UN usuario ACTIVO cuyo ROL este ACTIVO y
    contenga el permiso ROLES, considerando los overrides hipoteticos. Se usa
    para bloquear operaciones que dejarian al sistema sin administrador.

    Args:
        usuario_override: (user_id, activo, role_id) estado hipotetico de un
            usuario que se esta por modificar (o None).
        rol_override: (role_id, activo, codigos_permisos) estado hipotetico de
            un rol que se esta por modificar (o None).
    """
    # Precalcula, por rol, si (con override) otorgaria ROLES estando activo.
    roles = db.query(Role).all()
    rol_otorga: dict[int, bool] = {
        rol.id: _rol_otorga_roles(rol, rol_override) for rol in roles
    }

    # Recorre los usuarios aplicando el override de usuario si corresponde.
    usuarios = db.query(User).all()
    for usuario in usuarios:
        if usuario_override is not None and usuario_override[0] == usuario.id:
            _, activo, role_id = usuario_override
        else:
            activo, role_id = usuario.active, usuario.role_id

        if not activo or role_id is None:
            continue
        if rol_otorga.get(role_id, False):
            # Hay al menos un usuario activo con un rol activo que da ROLES.
            return True

    return False


# ---------------------------------------------------------------------------
# Helpers de seed
# ---------------------------------------------------------------------------
def obtener_o_crear_permiso(db: Session, codigo: str, nombre: str) -> Permission:
    """Devuelve el Permission con ese codigo, creandolo si no existe (idempotente).

    Si el permiso ya existe pero su nombre visible difiere, lo actualiza (el
    codigo es el identificador estable; el nombre es solo la etiqueta). No hace
    commit: el llamador (seed) commitea al final.
    """
    permiso = db.query(Permission).filter(Permission.codigo == codigo).first()
    if permiso is None:
        permiso = Permission(codigo=codigo, nombre=nombre, activo=True)
        db.add(permiso)
        return permiso

    # Opcional: mantener sincronizada la etiqueta visible si cambio en el catalogo.
    if permiso.nombre != nombre:
        permiso.nombre = nombre
    return permiso


# ---------------------------------------------------------------------------
# Seed idempotente de roles y permisos
# ---------------------------------------------------------------------------
def seed_roles_y_permisos(db: Session) -> None:
    """Siembra el catalogo de permisos, el rol Administrador y su asignacion.

    Es IDEMPOTENTE: puede ejecutarse en cada arranque sin duplicar nada. Pasos:

      1. Por cada (codigo, nombre) de PERMISOS_MENU, crea el Permission si no
         existe (o actualiza su etiqueta visible si difiere).
      2. Crea el rol "Administrador" si no existe (activo, descripcion "Acceso
         completo") y se asegura de que tenga TODOS los permisos del catalogo,
         agregando solo los que le falten.
      3. Asigna el rol Administrador a TODOS los usuarios con role_id NULL (por
         ejemplo, juan123 y cualquier usuario creado antes de este modulo), para
         no dejar a nadie sin acceso tras incorporar Roles.
      4. commit unico al final.

    Decision del proyecto: create_all + este seed idempotente en vez de Alembic.
    """
    # (1) Catalogo de permisos: crear los que falten (sin duplicar).
    permisos_por_codigo: dict[str, Permission] = {}
    for codigo, nombre in PERMISOS_MENU:
        permiso = obtener_o_crear_permiso(db, codigo, nombre)
        permisos_por_codigo[codigo] = permiso
    # flush para que los permisos recien creados tengan id antes de asociarlos.
    db.flush()

    # (2) Rol Administrador: crearlo si no existe.
    rol_admin = db.query(Role).filter(Role.nombre == ROL_ADMINISTRADOR).first()
    if rol_admin is None:
        rol_admin = Role(
            nombre=ROL_ADMINISTRADOR,
            descripcion="Acceso completo",
            activo=True,
        )
        db.add(rol_admin)
        db.flush()

    # Asegurar que el rol Administrador tenga TODOS los permisos del catalogo,
    # agregando de forma idempotente solo los que le falten.
    codigos_actuales = {permiso.codigo for permiso in rol_admin.permisos}
    for codigo, permiso in permisos_por_codigo.items():
        if codigo not in codigos_actuales:
            rol_admin.permisos.append(permiso)

    # (3) Asignar el rol Administrador a todos los usuarios sin rol (role_id NULL).
    usuarios_sin_rol = db.query(User).filter(User.role_id.is_(None)).all()
    for usuario in usuarios_sin_rol:
        usuario.role_id = rol_admin.id

    # (4) commit unico de todos los cambios.
    db.commit()
