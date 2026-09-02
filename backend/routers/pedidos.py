# routers/pedidos.py
# Router de la API para el recurso Pedido (Req. 8, 9, 10, 11).
#
# Expone las operaciones de pedidos bajo el prefijo /api/pedidos:
#   - GET    /api/pedidos              -> lista todos los pedidos (con nombres).
#   - POST   /api/pedidos              -> crea un pedido (201).
#   - PATCH  /api/pedidos/{id}/estado  -> cambia el estado de un pedido.
#
# Reglas de negocio (design.md -> Contratos de API -> Pedidos, y Error Handling):
#   - El cliente y el producto deben existir; si no, 400/404 con mensaje en espanol.
#   - El producto debe estar disponible (producto_seleccionable); si no, 400.
#   - Al crear, se COPIA el precio vigente del producto a precio_unitario (Req. 8.4),
#     se calcula el total con calcular_total (Req. 9.1), y se asignan fecha=hoy
#     (Req. 8.2) y estado="Pendiente" (Req. 8.3).
#   - Al cambiar el estado se valida con es_estado_valido; si es invalido se
#     conserva el estado anterior y se devuelve 400 (Req. 10.3).
#
# La validacion "de forma" de Pydantic (cantidad 1..9999) sigue aplicando y
# produce 422 si la cantidad esta fuera de rango (Req. 8.5).

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

# get_db entrega una sesion de base de datos por peticion (database.py).
from database import get_db

# Modelos ORM (models.py).
from models import Cliente, Pedido, Producto

# Esquemas Pydantic de request/response para Pedido (schemas.py).
from schemas import PedidoCrear, PedidoRespuesta

# Reglas de negocio puras reutilizadas desde la capa de servicios.
from services import ESTADOS_VALIDOS, calcular_total, es_estado_valido, producto_seleccionable

# Dependencia de autorizacion: protege todos los endpoints exigiendo el permiso
# "PEDIDOS" (require_permission valida sesion 401 + 403 si falta el permiso).
from auth_dependencies import require_permission

# APIRouter con prefijo comun y etiqueta para la documentacion automatica.
# main.py incluira este router en la Tarea 10.
router = APIRouter(prefix="/api/pedidos", tags=["pedidos"])


# ---------------------------------------------------------------------------
# Modelo de request para el cambio de estado
# ---------------------------------------------------------------------------
# Decision de diseno: aunque schemas.PedidoCambiarEstado tipa `estado` como el
# Enum EstadoPedido (lo que daria 422 de Pydantic ante un valor fuera del
# conjunto), el Req. 10.3 exige devolver un 400 con un mensaje en espanol y
# CONSERVAR el estado anterior ante cualquier cadena invalida (incluida la
# vacia). Para poder cumplir ese criterio con un valor arbitrario, aqui el
# endpoint recibe `estado` como str y valida con es_estado_valido, devolviendo
# el 400 con el mensaje del diseno. Asi el contrato de error queda uniforme.
class CambiarEstadoRequest(BaseModel):
    """Request para cambiar el estado de un pedido.

    `estado` se recibe como str (no como Enum) para permitir validar con
    es_estado_valido y devolver 400 + mensaje en espanol ante valores
    invalidos, conservando el estado anterior (Req. 10.3).
    """

    estado: str


# Mensaje de estado invalido, exactamente como lo define el design.md.
MENSAJE_ESTADO_INVALIDO = (
    "El Estado debe ser uno de: Pendiente, Preparando, Entregado, Cancelado."
)


# ---------------------------------------------------------------------------
# Helper: construir PedidoRespuesta con cliente_nombre y producto_nombre
# ---------------------------------------------------------------------------
def _a_respuesta(pedido: Pedido) -> PedidoRespuesta:
    """Mapea un objeto ORM Pedido al esquema de respuesta con nombres.

    Toma cliente_nombre y producto_nombre de las relaciones ORM del pedido
    (pedido.cliente / pedido.producto), cumpliendo Req. 8.9 y 11.1.
    """
    return PedidoRespuesta(
        id=pedido.id,
        cliente_id=pedido.cliente_id,
        cliente_nombre=pedido.cliente.nombre,
        producto_id=pedido.producto_id,
        producto_nombre=pedido.producto.nombre,
        cantidad=pedido.cantidad,
        precio_unitario=pedido.precio_unitario,
        total=pedido.total,
        fecha=pedido.fecha,
        estado=pedido.estado,
    )


def _obtener_pedido_o_404(pedido_id: int, db: Session) -> Pedido:
    """Busca un pedido por id o lanza 404 con mensaje descriptivo (Req. 15.3, 16.1)."""
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El Pedido no existe.",
        )
    return pedido


# ---------------------------------------------------------------------------
# GET /api/pedidos -> lista de pedidos con nombres (Req. 11.1)
# ---------------------------------------------------------------------------
@router.get("", response_model=list[PedidoRespuesta])
def listar_pedidos(
    db: Session = Depends(get_db), _usuario=Depends(require_permission("PEDIDOS"))
) -> list[PedidoRespuesta]:
    """Devuelve todos los pedidos con cliente_nombre y producto_nombre.

    Si no hay pedidos devuelve una lista vacia; el mensaje de "no hay pedidos"
    lo muestra el frontend (Req. 11.2).
    """
    pedidos = db.query(Pedido).all()
    return [_a_respuesta(pedido) for pedido in pedidos]


# ---------------------------------------------------------------------------
# POST /api/pedidos -> crea un pedido (Req. 8.1 .. 8.9, 9.1)
# ---------------------------------------------------------------------------
@router.post("", response_model=PedidoRespuesta, status_code=status.HTTP_201_CREATED)
def crear_pedido(
    datos: PedidoCrear,
    db: Session = Depends(get_db),
    _usuario=Depends(require_permission("PEDIDOS")),
) -> PedidoRespuesta:
    """Crea un nuevo pedido aplicando las reglas de negocio y lo devuelve (201).

    Flujo:
      1. Valida que el cliente exista (Req. 8.6) -> 400 si no.
      2. Valida que el producto exista (Req. 8.7) -> 400 si no.
      3. Valida que el producto este disponible (Req. 8.8) -> 400 si no.
      4. Copia precio_unitario = precio vigente del producto (Req. 8.4).
      5. Calcula total = cantidad * precio_unitario (Req. 9.1).
      6. Asigna fecha = hoy (Req. 8.2) y estado = "Pendiente" (Req. 8.3).
    La cantidad (1..9999) ya la valida Pydantic (Req. 8.5).
    """
    # (1) El cliente es obligatorio y debe existir (Req. 8.6). Devolvemos 400 con
    # mensaje en espanol; se elige "El Cliente no existe." por ser mas preciso
    # cuando llega un id que no corresponde a ningun cliente.
    cliente = db.get(Cliente, datos.cliente_id)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El Cliente no existe.",
        )

    # (2) El producto es obligatorio y debe existir (Req. 8.7).
    producto = db.get(Producto, datos.producto_id)
    if producto is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El Producto no existe.",
        )

    # (3) El producto debe estar disponible (Req. 8.8). Reutilizamos la regla
    # pura producto_seleccionable de la capa de servicios.
    if not producto_seleccionable(producto):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El Producto no esta disponible.",
        )

    # (4) Copiamos el precio vigente del producto para conservar el historico:
    # cambios posteriores del precio del producto NO afectaran a este pedido.
    precio_unitario = producto.precio

    # (5) Total = cantidad * precio_unitario, con aritmetica Decimal (Req. 9.1).
    total = calcular_total(datos.cantidad, precio_unitario)

    # (6) Fecha de hoy y estado inicial "Pendiente". Asignamos fecha de forma
    # EXPLICITA (no dependemos del server_default de la BD, que en SQLite podria
    # no aplicar del mismo modo que en PostgreSQL).
    pedido = Pedido(
        cliente_id=cliente.id,
        producto_id=producto.id,
        cantidad=datos.cantidad,
        precio_unitario=precio_unitario,
        total=total,
        fecha=date.today(),
        estado="Pendiente",
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return _a_respuesta(pedido)


# ---------------------------------------------------------------------------
# PATCH /api/pedidos/{id}/estado -> cambia el estado (Req. 10.1, 10.2, 10.3)
# ---------------------------------------------------------------------------
@router.patch("/{pedido_id}/estado", response_model=PedidoRespuesta)
def cambiar_estado(
    pedido_id: int,
    datos: CambiarEstadoRequest,
    db: Session = Depends(get_db),
    _usuario=Depends(require_permission("PEDIDOS")),
) -> PedidoRespuesta:
    """Cambia el estado de un pedido validando el conjunto de valores permitidos.

    - 404 si el pedido no existe.
    - 400 (conservando el estado anterior) si el estado es invalido o vacio,
      con el mensaje del diseno (Req. 10.3).
    - 200 con el pedido actualizado si el estado es valido (Req. 10.1, 10.2).
    """
    # 404 si no existe.
    pedido = _obtener_pedido_o_404(pedido_id, db)

    # Regla de negocio (Req. 10.3): estado invalido o vacio -> 400 y se conserva
    # el estado anterior (no se toca el pedido en la BD).
    if not es_estado_valido(datos.estado):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MENSAJE_ESTADO_INVALIDO,
        )

    # Estado valido: se guarda y se refleja (Req. 10.1).
    pedido.estado = datos.estado
    db.commit()
    db.refresh(pedido)
    return _a_respuesta(pedido)
