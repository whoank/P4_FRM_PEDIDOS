# routers/reporte.py
# Router de la API para el Reporte diario de ventas y pedidos (Req. 12).
#
# Expone una unica operacion bajo el prefijo /api:
#   - GET /api/reporte-diario?fecha=YYYY-MM-DD -> resumen del dia seleccionado.
#
# Comportamiento (design.md -> Contratos de API -> Reporte diario):
#   - El parametro `fecha` es OPCIONAL; si se omite se usa el dia actual (Req. 12.1).
#   - Se toman los pedidos cuya Fecha coincide con el dia seleccionado (Req. 12.3),
#     reutilizando la funcion pura services.filtrar_por_fecha (ya probada).
#   - Se calculan `cantidad_pedidos` (cuenta TODOS los del dia, incluidos los
#     Cancelados, Req. 12.4) y `suma_ventas` (suma solo los NO cancelados; 0 si
#     no hay pedidos o todos estan cancelados, Req. 12.5) con services.resumir_reporte.
#   - Si no hay pedidos ese dia: cantidad_pedidos 0, suma_ventas 0, pedidos []
#     (el mensaje "no hay pedidos para ese dia" lo muestra el frontend, Req. 12.6).
#
# FastAPI parsea automaticamente el query param `fecha` (formato YYYY-MM-DD) a un
# objeto date cuando se tipa como `date | None`.

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

# get_db entrega una sesion de base de datos por peticion (database.py).
from database import get_db

# Modelo ORM (models.py).
from models import Pedido

# Esquema de respuesta del reporte y del pedido (schemas.py).
from schemas import PedidoRespuesta, ResumenReporte

# Reglas de negocio puras reutilizadas desde la capa de servicios (Tarea 4).
from services import filtrar_por_fecha, resumir_reporte

# Dependencia de autorizacion: protege el endpoint exigiendo el permiso
# "REPORTE_DIARIO" (require_permission valida sesion 401 + 403 si falta).
from auth_dependencies import require_permission

# APIRouter con prefijo comun y etiqueta para la documentacion automatica.
# main.py incluira este router en la Tarea 10.
router = APIRouter(prefix="/api", tags=["reporte"])


# ---------------------------------------------------------------------------
# Helper: construir PedidoRespuesta con cliente_nombre y producto_nombre
# ---------------------------------------------------------------------------
# Mapeo local pequeno (en lugar de acoplar con routers/pedidos.py). Toma los
# nombres desnormalizados de las relaciones ORM del pedido (Req. 8.9, 11.1).
def _a_respuesta(pedido: Pedido) -> PedidoRespuesta:
    """Mapea un objeto ORM Pedido al esquema de respuesta, con los nombres."""
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


# ---------------------------------------------------------------------------
# GET /api/reporte-diario -> resumen del dia (Req. 12.1 .. 12.6)
# ---------------------------------------------------------------------------
@router.get("/reporte-diario", response_model=ResumenReporte)
def reporte_diario(
    fecha: date | None = None,
    db: Session = Depends(get_db),
    _usuario=Depends(require_permission("REPORTE_DIARIO")),
) -> ResumenReporte:
    """Devuelve el resumen de pedidos y ventas de un dia.

    - `fecha` opcional (YYYY-MM-DD); si se omite, se usa el dia actual (Req. 12.1).
    - Filtra los pedidos por la fecha seleccionada (Req. 12.3).
    - `cantidad_pedidos` cuenta todos los del dia, incluidos los Cancelados (Req. 12.4).
    - `suma_ventas` suma solo los NO cancelados; 0 si no hay o todos cancelados (Req. 12.5).
    - Si no hay pedidos ese dia, devuelve lista vacia y ceros (Req. 12.6).
    """
    # (1) Dia seleccionado: el recibido o, si se omite, el dia actual (Req. 12.1, 12.2).
    dia = fecha if fecha is not None else date.today()

    # (2) Cargamos los pedidos y nos quedamos con los del dia usando la funcion
    # pura ya probada (Req. 12.3). Se podria filtrar en SQL, pero reutilizar
    # filtrar_por_fecha mantiene la logica en un solo lugar y facilita las pruebas.
    todos = db.query(Pedido).all()
    pedidos_del_dia = filtrar_por_fecha(todos, dia)

    # (3) Conteo total (incluye cancelados) y suma de ventas (excluye cancelados),
    # reutilizando resumir_reporte (Req. 12.4, 12.5).
    resumen = resumir_reporte(pedidos_del_dia)

    # (4) Armamos la respuesta. La lista puede quedar vacia si no hay pedidos del
    # dia (Req. 12.6); el mensaje al usuario lo muestra el frontend.
    return ResumenReporte(
        fecha=dia,
        cantidad_pedidos=resumen.cantidad_pedidos,
        suma_ventas=resumen.suma_ventas,
        pedidos=[_a_respuesta(pedido) for pedido in pedidos_del_dia],
    )
