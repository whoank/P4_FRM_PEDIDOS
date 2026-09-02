# models.py
# Modelos ORM de SQLAlchemy que representan las tablas de la base de datos:
# Cliente, Producto y Pedido, con sus columnas, restricciones y relaciones.
#
# Los tipos y restricciones siguen la seccion "Data Models" del design.md
# (fuente autoritativa del esquema). Los montos usan Numeric (mapeado a Decimal
# en Python) y no punto flotante, para evitar errores de redondeo con dinero.

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    func,
    text,
)
from sqlalchemy.orm import relationship

# La Base declarativa y el engine se definen en database.py (Tarea 2.1).
# Importamos ambos: Base para declarar los modelos y engine para crear las tablas.
from database import Base, engine


class Cliente(Base):
    """Cliente del negocio que realiza pedidos.

    Un cliente puede tener varios pedidos (relacion uno-a-muchos con Pedido).
    """

    __tablename__ = "cliente"

    # id: clave primaria autoincremental.
    id = Column(Integer, primary_key=True, autoincrement=True)
    # nombre obligatorio, 1..100 caracteres (la validacion de longitud/espacios
    # de negocio se aplica en la capa de servicios; aqui solo el limite de la BD).
    nombre = Column(String(100), nullable=False)
    # telefono obligatorio, hasta 20 caracteres.
    telefono = Column(String(20), nullable=False)
    # direccion opcional, hasta 200 caracteres.
    direccion = Column(String(200), nullable=True)

    # Relacion inversa hacia los pedidos de este cliente (opcional, comodo para
    # exponer datos en tareas posteriores).
    pedidos = relationship("Pedido", back_populates="cliente")


class Producto(Base):
    """Producto que el negocio ofrece y que puede incluirse en un pedido."""

    __tablename__ = "producto"

    # Restriccion de rango del precio: 0.00 a 999999.99.
    __table_args__ = (
        CheckConstraint(
            "precio >= 0 AND precio <= 999999.99",
            name="ck_producto_precio_rango",
        ),
    )

    # id: clave primaria autoincremental.
    id = Column(Integer, primary_key=True, autoincrement=True)
    # nombre obligatorio, hasta 100 caracteres.
    nombre = Column(String(100), nullable=False)
    # descripcion opcional, hasta 500 caracteres.
    descripcion = Column(String(500), nullable=True)
    # precio obligatorio con 2 decimales (Numeric, no Float).
    precio = Column(Numeric(8, 2), nullable=False)
    # disponible por defecto verdadero (Req. 5.5). Usamos server_default para
    # que el DEFAULT quede tambien a nivel de la base de datos.
    disponible = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Relacion inversa hacia los pedidos de este producto.
    pedidos = relationship("Pedido", back_populates="producto")


class Pedido(Base):
    """Pedido realizado por un cliente sobre un producto.

    El precio_unitario se copia del producto al momento de crear el pedido para
    conservar el historico (cambios posteriores del precio no afectan al pedido).
    """

    __tablename__ = "pedido"

    __table_args__ = (
        # cantidad entera entre 1 y 9999.
        CheckConstraint(
            "cantidad BETWEEN 1 AND 9999",
            name="ck_pedido_cantidad_rango",
        ),
        # estado limitado a los 4 valores del ciclo de vida.
        CheckConstraint(
            "estado IN ('Pendiente', 'Preparando', 'Entregado', 'Cancelado')",
            name="ck_pedido_estado_valido",
        ),
    )

    # id: clave primaria autoincremental.
    id = Column(Integer, primary_key=True, autoincrement=True)
    # cliente_id y producto_id: claves foraneas obligatorias.
    cliente_id = Column(Integer, ForeignKey("cliente.id"), nullable=False)
    producto_id = Column(Integer, ForeignKey("producto.id"), nullable=False)
    # cantidad entera obligatoria (rango validado por el CheckConstraint).
    cantidad = Column(Integer, nullable=False)
    # precio_unitario: precio vigente del producto copiado al crear el pedido.
    precio_unitario = Column(Numeric(8, 2), nullable=False)
    # total: cantidad * precio_unitario (se calcula en la logica de creacion).
    total = Column(Numeric(12, 2), nullable=False)
    # fecha de creacion, por defecto el dia actual (server_default a nivel de BD).
    fecha = Column(
        Date,
        nullable=False,
        server_default=func.current_date(),
    )
    # estado del pedido. El estado inicial ("Pendiente") se asigna en la logica
    # de creacion (Tarea 8); aqui solo se restringe a los valores validos.
    estado = Column(String(20), nullable=False)

    # Relaciones hacia el cliente y el producto asociados al pedido.
    cliente = relationship("Cliente", back_populates="pedidos")
    producto = relationship("Producto", back_populates="pedidos")


# ---------------------------------------------------------------------------
# Modelos de autenticacion (modulo de sesion por cookie)
# ---------------------------------------------------------------------------
# Estos modelos son independientes de la logica de negocio (Cliente, Producto,
# Pedido). Al heredar de Base quedan registrados en Base.metadata, por lo que
# crear_tablas() (Base.metadata.create_all) creara sus tablas automaticamente
# sin necesidad de migraciones.


class User(Base):
    """Usuario que puede iniciar sesion en la aplicacion.

    La contrasena NUNCA se guarda en claro: se almacena unicamente su hash
    (bcrypt) en password_hash.
    """

    __tablename__ = "users"

    # id: clave primaria autoincremental.
    id = Column(Integer, primary_key=True, autoincrement=True)
    # username: unico y obligatorio; indexado para acelerar la busqueda al login.
    username = Column(String(50), unique=True, nullable=False, index=True)
    # password_hash: hash bcrypt de la contrasena (nunca la contrasena en claro).
    password_hash = Column(String(255), nullable=False)
    # active: si es False, el usuario no puede autenticarse. Default True tambien
    # a nivel de base de datos (server_default).
    active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    # created_at / updated_at: marcas de tiempo gestionadas por la base de datos.
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    # last_login: ultimo inicio de sesion exitoso; nulo hasta el primer login.
    last_login = Column(DateTime, nullable=True)
    # role_id: FK al rol asignado al usuario. Es nullable=True a proposito para
    # NO romper las filas de usuarios que ya existian antes de anadir Roles; el
    # seed idempotente (roles_service.seed_roles_y_permisos) asignara el rol
    # "Administrador" a todos los usuarios que quedaron con role_id NULL.
    # Indexado para acelerar el join usuario -> rol.
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True, index=True)

    # Relacion inversa hacia las sesiones activas del usuario (opcional, comoda).
    sesiones = relationship("UserSession", back_populates="usuario")
    # Relacion hacia el rol del usuario (uno-a-muchos: un rol tiene varios usuarios).
    role = relationship("Role", back_populates="usuarios")


class UserSession(Base):
    """Sesion activa de un usuario, referenciada por una cookie en el navegador.

    En la base de datos se guarda solo el SHA-256 (hex) del token de sesion
    (token_hash), NUNCA el token en claro: asi, aunque se filtre la tabla, no se
    pueden reconstruir las cookies validas.
    """

    __tablename__ = "user_session"

    # id: clave primaria autoincremental.
    id = Column(Integer, primary_key=True, autoincrement=True)
    # user_id: FK al usuario dueno de la sesion; obligatorio e indexado.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # token_hash: SHA-256 hex (64 caracteres) del token de sesion; unico e indexado.
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    # created_at: momento de creacion de la sesion (gestionado por la BD).
    created_at = Column(DateTime, server_default=func.now())
    # expires_at: momento en que la sesion deja de ser valida; obligatorio.
    expires_at = Column(DateTime, nullable=False)

    # Relacion hacia el usuario dueno de la sesion.
    usuario = relationship("User", back_populates="sesiones")


# ---------------------------------------------------------------------------
# Modelos de Roles y Permisos por opcion de menu (modulo de autorizacion)
# ---------------------------------------------------------------------------
# Estos modelos implementan el control de acceso por opcion de menu:
#   - Permission: cada permiso corresponde a una opcion del menu (Clientes,
#     Productos, etc.). El "codigo" es el identificador de seguridad interno.
#   - Role: agrupa un conjunto de permisos; cada usuario tiene 0..1 rol.
#   - role_permissions: tabla asociativa muchos-a-muchos entre roles y permisos.
# Al heredar de Base quedan registrados en Base.metadata, por lo que
# crear_tablas() (Base.metadata.create_all) creara sus tablas automaticamente
# SIN necesidad de migraciones (decision del proyecto: NO usar Alembic).


# Tabla asociativa muchos-a-muchos entre roles y permisos. La clave primaria
# compuesta (role_id, permission_id) evita filas duplicadas (un mismo permiso
# no se puede asociar dos veces al mismo rol). ondelete="CASCADE" limpia las
# asociaciones automaticamente si se elimina un rol o un permiso.
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column(
        "role_id",
        Integer,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        Integer,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base):
    """Rol de acceso que agrupa un conjunto de permisos de menu.

    Un rol puede asignarse a varios usuarios (relacion uno-a-muchos) y tiene
    varios permisos (relacion muchos-a-muchos via role_permissions).
    """

    __tablename__ = "roles"

    # id: clave primaria autoincremental.
    id = Column(Integer, primary_key=True, autoincrement=True)
    # nombre: unico y obligatorio; indexado para busquedas por nombre.
    nombre = Column(String(50), unique=True, nullable=False, index=True)
    # descripcion opcional del rol.
    descripcion = Column(String(255), nullable=True)
    # activo: si es False, el rol no otorga permisos (permisos_de_usuario
    # devolvera vacio). Default True tambien a nivel de base de datos.
    activo = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    # created_at / updated_at: marcas de tiempo gestionadas por la base de datos.
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relacion muchos-a-muchos con Permission a traves de role_permissions.
    permisos = relationship(
        "Permission", secondary=role_permissions, back_populates="roles"
    )
    # Relacion uno-a-muchos hacia los usuarios que tienen este rol.
    usuarios = relationship("User", back_populates="role")


class Permission(Base):
    """Permiso que habilita el acceso a una opcion de menu.

    El "codigo" es el identificador de seguridad interno (por ejemplo
    "CLIENTES") que el backend comprueba en require_permission; el "nombre" es
    solo la etiqueta visible en la interfaz (por ejemplo "Clientes").
    """

    __tablename__ = "permissions"

    # id: clave primaria autoincremental.
    id = Column(Integer, primary_key=True, autoincrement=True)
    # codigo: identificador de seguridad, unico y obligatorio; indexado.
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    # nombre: etiqueta visible en el menu/formularios (no es el identificador).
    nombre = Column(String(100), nullable=False)
    # descripcion opcional del permiso.
    descripcion = Column(String(255), nullable=True)
    # activo: permite ocultar/deshabilitar un permiso sin borrarlo.
    activo = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Relacion muchos-a-muchos con Role a traves de role_permissions.
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permisos"
    )


def crear_tablas() -> None:
    """Crea las tablas en la base de datos si aun no existen.

    Invoca Base.metadata.create_all usando el engine de database.py. Esta
    funcion NO se ejecuta automaticamente al importar el modulo; debe llamarse
    de forma explicita desde main.py al iniciar la aplicacion (Tarea 10).
    """
    Base.metadata.create_all(bind=engine)
