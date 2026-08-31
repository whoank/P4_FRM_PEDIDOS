# services.py
# Capa de servicios con las reglas de negocio PURAS (sin acceso a base de datos):
# calcular_total, es_estado_valido, resumir_reporte, producto_seleccionable,
# filtrar_por_fecha y las validaciones de campos.
#
# Estas funciones son puras y faciles de probar (incluyendo pruebas basadas en
# propiedades con Hypothesis). Por eso este modulo NO importa database.py,
# models.py ni el driver psycopg: asi la capa de logica de negocio queda
# desacoplada del ORM y de la base de datos.
#
# Para no acoplar con el ORM, las funciones que operan sobre "pedidos" o
# "productos" usan duck typing: solo esperan objetos con los atributos que
# necesitan (por ejemplo .estado, .total, .fecha o .disponible). De este modo
# sirven tanto para los modelos ORM reales como para objetos de prueba.
#
# Los montos de dinero usan Decimal (nunca float) para evitar errores de
# redondeo (Req. 9.1, 9.2).

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional, Union

# ---------------------------------------------------------------------------
# Conjunto de estados validos
# ---------------------------------------------------------------------------
# Se define localmente (en vez de importar el Enum de schemas.py) para mantener
# la capa de servicios lo mas simple y desacoplada posible. Son los 4 valores
# del ciclo de vida de un Pedido (Req. 10).
ESTADOS_VALIDOS: frozenset[str] = frozenset(
    {"Pendiente", "Preparando", "Entregado", "Cancelado"}
)

# Estado que excluye un pedido de la suma de ventas del reporte (Req. 12.5).
ESTADO_CANCELADO = "Cancelado"

# Limites de negocio reutilizados por las validaciones.
PRECIO_MINIMO = Decimal("0")
PRECIO_MAXIMO = Decimal("999999.99")
CANTIDAD_MINIMA = 1
CANTIDAD_MAXIMA = 9999


# ---------------------------------------------------------------------------
# 4.1 Calculo del total y validez del estado
# ---------------------------------------------------------------------------


def calcular_total(cantidad: int, precio_unitario: Decimal) -> Decimal:
    """Calcula el Total de un pedido como cantidad * precio_unitario (Req. 9.1, 9.2).

    Usa aritmetica Decimal para evitar errores de redondeo con dinero. La
    cantidad (entero) se convierte a Decimal antes de multiplicar para que el
    resultado sea siempre un Decimal exacto.
    """
    return Decimal(cantidad) * precio_unitario


def es_estado_valido(estado: str) -> bool:
    """Indica si un estado pertenece al conjunto valido (Req. 10.3).

    Devuelve True solo para exactamente {Pendiente, Preparando, Entregado,
    Cancelado}. Cualquier otra cadena (incluida la vacia) devuelve False.
    """
    return estado in ESTADOS_VALIDOS


# ---------------------------------------------------------------------------
# 4.5 Producto seleccionable y validaciones de campos
# ---------------------------------------------------------------------------


def producto_seleccionable(producto: object) -> bool:
    """Indica si un producto puede incluirse en un pedido (Req. 7.3, 8.8).

    Es seleccionable solo si su indicador `disponible` es True. Para no depender
    del ORM, acepta:
      - un objeto con atributo `.disponible` (por ejemplo el modelo Producto), o
      - directamente un valor booleano.
    """
    if isinstance(producto, bool):
        disponible = producto
    else:
        disponible = getattr(producto, "disponible", False)
    return disponible is True


def validar_campo_obligatorio(valor: Optional[str], nombre_campo: str) -> Optional[str]:
    """Valida que un campo obligatorio no este vacio ni contenga solo espacios.

    Devuelve un mensaje de error en espanol si el valor es None, cadena vacia o
    esta compuesto unicamente por espacios en blanco; devuelve None si es valido
    (Req. 2.2, 2.3, 4.2, 5.2).
    """
    if valor is None or valor.strip() == "":
        return f"El {nombre_campo} es obligatorio."
    return None


def validar_longitud_maxima(
    valor: Optional[str], maximo: int, nombre_campo: str
) -> Optional[str]:
    """Valida que un campo no supere su longitud maxima permitida.

    Devuelve un mensaje de error en espanol si la longitud del valor supera el
    maximo; devuelve None si es valido o si el valor es None (Req. 2.4, 5.2).
    """
    if valor is not None and len(valor) > maximo:
        return f"El {nombre_campo} no debe superar {maximo} caracteres."
    return None


def validar_precio(precio: Decimal) -> Optional[str]:
    """Valida que el precio este dentro del rango permitido (Req. 5.3, 7.2).

    Rechaza precios menores que 0 o mayores que 999999.99. Devuelve el mensaje de
    error en espanol o None si el precio es valido.
    """
    if precio < PRECIO_MINIMO or precio > PRECIO_MAXIMO:
        return "El Precio debe ser igual o mayor que 0 y no mayor que 999999.99."
    return None


def validar_cantidad(cantidad: object) -> Optional[str]:
    """Valida que la cantidad sea un entero entre 1 y 9999 (Req. 8.5).

    Rechaza valores que no sean enteros (incluidos los booleanos y los flotantes)
    y los enteros fuera del rango [1, 9999]. Devuelve el mensaje de error en
    espanol o None si la cantidad es valida.
    """
    mensaje = "La Cantidad debe ser un numero entero entre 1 y 9999."
    # bool es subclase de int, pero no es una cantidad valida.
    if isinstance(cantidad, bool) or not isinstance(cantidad, int):
        return mensaje
    if cantidad < CANTIDAD_MINIMA or cantidad > CANTIDAD_MAXIMA:
        return mensaje
    return None


# ---------------------------------------------------------------------------
# 4.11 Resumen del reporte diario
# ---------------------------------------------------------------------------


@dataclass
class ResumenServicio:
    """Resultado del resumen del reporte (calculado por la capa de servicios).

    - cantidad_pedidos: total de pedidos (incluye los Cancelados) (Req. 12.4).
    - suma_ventas: suma de los `total` de los pedidos NO cancelados (Req. 12.5).
    """

    cantidad_pedidos: int
    suma_ventas: Decimal


def resumir_reporte(pedidos: list) -> ResumenServicio:
    """Resume una lista de pedidos: conteo total y suma de ventas (Req. 12.4, 12.5).

    - cantidad_pedidos cuenta TODOS los pedidos, incluidos los Cancelados.
    - suma_ventas suma el `.total` solo de los pedidos cuyo `.estado` no sea
      'Cancelado'. Es 0 si la lista esta vacia o si todos estan Cancelados.

    Usa duck typing: cada elemento debe exponer `.estado` y `.total`.
    """
    cantidad_pedidos = len(pedidos)
    suma_ventas = Decimal("0")
    for pedido in pedidos:
        if pedido.estado != ESTADO_CANCELADO:
            suma_ventas += pedido.total
    return ResumenServicio(cantidad_pedidos=cantidad_pedidos, suma_ventas=suma_ventas)


def filtrar_por_fecha(pedidos: list, fecha: date) -> list:
    """Filtra los pedidos cuya `.fecha` coincide con la fecha seleccionada (Req. 12.3).

    Funcion pura auxiliar para el reporte diario: devuelve exactamente los
    pedidos del dia indicado (y ninguno de otras fechas), conservando el orden
    original. La reutilizara el router del reporte (Tarea 9). Usa duck typing:
    cada elemento debe exponer `.fecha`.
    """
    return [pedido for pedido in pedidos if pedido.fecha == fecha]
