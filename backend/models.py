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
    ForeignKey,
    Integer,
    Numeric,
    String,
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


def crear_tablas() -> None:
    """Crea las tablas en la base de datos si aun no existen.

    Invoca Base.metadata.create_all usando el engine de database.py. Esta
    funcion NO se ejecuta automaticamente al importar el modulo; debe llamarse
    de forma explicita desde main.py al iniciar la aplicacion (Tarea 10).
    """
    Base.metadata.create_all(bind=engine)
