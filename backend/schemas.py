# schemas.py
# Modelos Pydantic (v2) para la validacion de entrada/salida (request/response)
# de Cliente, Producto, Pedido y el resumen del reporte diario.
#
# Estos esquemas son INDEPENDIENTES del ORM: no importan models.py ni database.py.
# Solo dependen de Pydantic y de la libreria estandar (datetime.date, decimal.Decimal).
# Los montos usan Decimal (no float) para evitar errores de redondeo con dinero.
#
# Nota sobre la validacion: aqui se aplican las restricciones "de forma" (longitud
# minima/maxima, rangos numericos, tipos). El rechazo autoritativo de cadenas
# compuestas SOLO por espacios y de otras reglas de negocio vive en la capa de
# servicios (Tarea 4) y en los routers (Tareas 6-9).

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Tipos reutilizables
# ---------------------------------------------------------------------------


class EstadoPedido(str, Enum):
    """Los cuatro estados validos del ciclo de vida de un Pedido (Req. 10).

    Hereda de str para que el valor serializado en JSON sea la cadena directa
    (por ejemplo, "Pendiente") y para poder compararlo comodamente con strings.
    """

    PENDIENTE = "Pendiente"
    PREPARANDO = "Preparando"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"


# Alias de tipo para el precio: Decimal entre 0 y 999999.99 con 2 decimales.
# max_digits=8 y decimal_places=2 permiten hasta 999999.99 (6 enteros + 2 decimales).
Precio = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=Decimal("999999.99"), max_digits=8, decimal_places=2),
]

# Alias de tipo para el total del pedido: puede ser mayor que el precio unitario
# (cantidad * precio), por eso admite mas digitos (hasta 9999 * 999999.99).
Monto = Annotated[
    Decimal,
    Field(ge=Decimal("0"), max_digits=12, decimal_places=2),
]

# Alias de tipo para la cantidad: entero entre 1 y 9999 (Req. 8.5).
Cantidad = Annotated[int, Field(ge=1, le=9999)]


# ---------------------------------------------------------------------------
# Esquemas de Cliente (Req. 2, 3, 4)
# ---------------------------------------------------------------------------


class ClienteBase(BaseModel):
    """Campos comunes de un Cliente para request de creacion y edicion.

    - nombre: obligatorio, 1..100 caracteres (Req. 2.1, 2.4).
    - telefono: obligatorio, 1..20 caracteres (Req. 2.1, 2.4).
    - direccion: opcional, hasta 200 caracteres (Req. 2.1, 2.4).
    """

    nombre: str = Field(min_length=1, max_length=100)
    telefono: str = Field(min_length=1, max_length=20)
    direccion: Optional[str] = Field(default=None, max_length=200)


class ClienteCrear(ClienteBase):
    """Request para crear (POST) o editar (PUT) un Cliente."""


class ClienteRespuesta(ClienteBase):
    """Response de Cliente: agrega el id asignado por la base de datos."""

    id: int

    # Permite construir el esquema directamente desde un objeto ORM (Cliente).
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Esquemas de Producto (Req. 5, 6, 7)
# ---------------------------------------------------------------------------


class ProductoBase(BaseModel):
    """Campos comunes de un Producto para request de creacion y edicion.

    - nombre: obligatorio, 1..100 caracteres (Req. 5.1).
    - descripcion: opcional, hasta 500 caracteres (Req. 5.1).
    - precio: Decimal en rango 0..999999.99 con 2 decimales (Req. 5.1, 5.3).
    - disponible: bool con valor predeterminado True (Req. 5.5).
    """

    nombre: str = Field(min_length=1, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    precio: Precio
    disponible: bool = True


class ProductoCrear(ProductoBase):
    """Request para crear (POST) o editar (PUT) un Producto."""


class ProductoRespuesta(ProductoBase):
    """Response de Producto: agrega el id asignado por la base de datos."""

    id: int

    # Permite construir el esquema directamente desde un objeto ORM (Producto).
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Esquemas de Pedido (Req. 8, 9, 10, 11)
# ---------------------------------------------------------------------------


class PedidoCrear(BaseModel):
    """Request para crear un Pedido (POST).

    El backend NO recibe precio ni total: los calcula al crear el pedido
    (Tarea 8) usando el precio vigente del producto. Aqui solo llegan las
    referencias al cliente y al producto, y la cantidad.

    - cliente_id: id del Cliente (Req. 8.1, 8.6).
    - producto_id: id del Producto (Req. 8.1, 8.7).
    - cantidad: entero entre 1 y 9999 (Req. 8.1, 8.5).
    """

    cliente_id: int
    producto_id: int
    cantidad: Cantidad


class PedidoCambiarEstado(BaseModel):
    """Request para cambiar el Estado de un Pedido (PATCH).

    Se tipa con el Enum EstadoPedido para restringir a los 4 valores validos y
    dar un contrato claro. La confirmacion autoritativa de la regla de negocio
    (y la conservacion del estado anterior ante un valor invalido) vive en los
    servicios/router (Tarea 8), coherente con Req. 10.3.
    """

    estado: EstadoPedido


class PedidoRespuesta(BaseModel):
    """Response completo de un Pedido con datos del cliente y del producto.

    Incluye los nombres desnormalizados (cliente_nombre, producto_nombre) para
    que el frontend muestre la lista sin consultas adicionales (Req. 8.9, 11.1).
    """

    id: int
    cliente_id: int
    cliente_nombre: str
    producto_id: int
    producto_nombre: str
    cantidad: Cantidad
    precio_unitario: Precio
    total: Monto
    fecha: date
    estado: EstadoPedido

    # Permite construir el esquema desde un objeto ORM (Pedido) cuando el router
    # completa cliente_nombre y producto_nombre a partir de las relaciones.
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Esquema del Reporte diario (Req. 12)
# ---------------------------------------------------------------------------


class ResumenReporte(BaseModel):
    """Resumen del reporte diario de ventas (Req. 12).

    - fecha: dia seleccionado del reporte (Req. 12.1, 12.3).
    - cantidad_pedidos: total de pedidos del dia, incluidos los Cancelados (Req. 12.4).
    - suma_ventas: suma de los Total excluyendo los pedidos Cancelados; 0 si no
      hay pedidos o todos estan Cancelados (Req. 12.5).
    - pedidos: lista de pedidos del dia (response completo).
    """

    fecha: date
    cantidad_pedidos: int = Field(ge=0)
    suma_ventas: Monto
    pedidos: list[PedidoRespuesta]
