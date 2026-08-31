# test_properties.py
# Pruebas basadas en propiedades (Property-Based Testing) con Hypothesis para la
# capa de servicios pura (services.py). Cubren las propiedades de correctitud
# asignadas a la Tarea 4: 1, 4, 5, 6, 7, 8, 9, 10, 12 y 13.
#
# Cada prueba lleva la etiqueta EXACTA:
#   # Feature: control-de-pedidos, Property {numero}: {texto}
#
# Todas usan al menos 100 ejemplos (max_examples>=100). services.py es puro
# (no importa el ORM ni psycopg), por lo que estas pruebas se ejecutan sin
# necesidad de base de datos.

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from services import (
    ESTADOS_VALIDOS,
    calcular_total,
    es_estado_valido,
    filtrar_por_fecha,
    producto_seleccionable,
    resumir_reporte,
    validar_campo_obligatorio,
    validar_cantidad,
    validar_longitud_maxima,
    validar_precio,
)

# ---------------------------------------------------------------------------
# Objetos de prueba (duck typing: solo exponen los atributos necesarios)
# ---------------------------------------------------------------------------


@dataclass
class ProductoFake:
    disponible: bool


@dataclass
class PedidoFake:
    estado: str
    total: Decimal
    fecha: date


# ---------------------------------------------------------------------------
# Estrategias reutilizables
# ---------------------------------------------------------------------------

# Precios validos: Decimal en [0, 999999.99] con 2 decimales.
precios_validos = st.integers(min_value=0, max_value=99999999).map(
    lambda centavos: (Decimal(centavos) / Decimal(100)).quantize(Decimal("0.01"))
)

# Cantidades validas: enteros en [1, 9999].
cantidades_validas = st.integers(min_value=1, max_value=9999)

# Estados: los 4 validos.
estados_validos_st = st.sampled_from(sorted(ESTADOS_VALIDOS))


# ---------------------------------------------------------------------------
# Property 1
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 1: El total es siempre cantidad por precio unitario
@settings(max_examples=200)
@given(cantidad=cantidades_validas, precio=precios_validos)
def test_property_1_total_es_cantidad_por_precio(cantidad: int, precio: Decimal):
    """Valida: Requerimientos 9.1, 9.2.

    Para toda cantidad entera 1..9999 y todo precio Decimal 0..999999.99, el
    total calculado es exactamente cantidad * precio, con aritmetica Decimal
    (sin errores de redondeo).
    """
    esperado = Decimal(cantidad) * precio
    resultado = calcular_total(cantidad, precio)
    assert resultado == esperado
    assert isinstance(resultado, Decimal)


# ---------------------------------------------------------------------------
# Property 4
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 4: Asignar un estado válido se persiste y se refleja (round trip)
@settings(max_examples=100)
@given(estado=estados_validos_st)
def test_property_4_estado_valido_es_aceptado(estado: str):
    """Valida: Requerimientos 10.1.

    Cada estado del conjunto valido {Pendiente, Preparando, Entregado,
    Cancelado} es aceptado por es_estado_valido (round trip: se reconoce como
    valido para poder persistirse y reflejarse).
    """
    assert es_estado_valido(estado) is True


# ---------------------------------------------------------------------------
# Property 5
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 5: Un estado inválido es rechazado y se conserva el anterior
@settings(max_examples=200)
@given(estado=st.text())
def test_property_5_estado_invalido_es_rechazado(estado: str):
    """Valida: Requerimientos 10.3.

    Para toda cadena arbitraria que no pertenezca al conjunto valido (incluida
    la cadena vacia), es_estado_valido devuelve False, por lo que el cambio se
    rechaza y se conservaria el estado anterior.
    """
    if estado not in ESTADOS_VALIDOS:
        assert es_estado_valido(estado) is False


# ---------------------------------------------------------------------------
# Property 6
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 6: Los productos no disponibles no se pueden pedir
@settings(max_examples=100)
@given(disponible=st.booleans())
def test_property_6_solo_productos_disponibles_son_seleccionables(disponible: bool):
    """Valida: Requerimientos 7.3, 8.8.

    producto_seleccionable devuelve True si y solo si el producto tiene
    disponible = True. Se prueba tanto con un objeto tipo Producto como con el
    booleano directo.
    """
    producto = ProductoFake(disponible=disponible)
    assert producto_seleccionable(producto) is disponible
    assert producto_seleccionable(disponible) is disponible


# ---------------------------------------------------------------------------
# Property 7
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 7: La cantidad fuera del rango 1..9999 es rechazada
@settings(max_examples=200)
@given(
    cantidad=st.one_of(
        st.integers(),  # incluye negativos, 0, >9999 y validos
        st.floats(allow_nan=False, allow_infinity=False),  # no enteros
        st.text(),  # no numericos
    )
)
def test_property_7_cantidad_fuera_de_rango_es_rechazada(cantidad):
    """Valida: Requerimientos 8.5.

    validar_cantidad devuelve None solo para enteros en [1, 9999]; cualquier
    otro valor (0, negativos, >9999, no enteros, no numericos) produce un
    mensaje de error.
    """
    es_entero_valido = (
        isinstance(cantidad, int)
        and not isinstance(cantidad, bool)
        and 1 <= cantidad <= 9999
    )
    resultado = validar_cantidad(cantidad)
    if es_entero_valido:
        assert resultado is None
    else:
        assert resultado == "La Cantidad debe ser un numero entero entre 1 y 9999."


# ---------------------------------------------------------------------------
# Property 8
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 8: Los campos obligatorios vacíos o solo con espacios son rechazados
@settings(max_examples=200)
@given(
    espacios=st.text(alphabet=st.sampled_from([" ", "\t", "\n", "\r", "\f", "\v"]))
)
def test_property_8_campos_obligatorios_vacios_o_espacios_rechazados(espacios: str):
    """Valida: Requerimientos 2.2, 2.3, 4.2, 5.2.

    Toda cadena vacia o compuesta unicamente por espacios en blanco es rechazada
    para un campo obligatorio (devuelve un mensaje de error, nunca None).
    """
    resultado = validar_campo_obligatorio(espacios, "Nombre")
    assert resultado == "El Nombre es obligatorio."


# ---------------------------------------------------------------------------
# Property 9
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 9: Los campos que exceden su longitud máxima son rechazados
@settings(max_examples=200)
@given(data=st.data(), maximo=st.integers(min_value=1, max_value=200))
def test_property_9_longitud_excedida_es_rechazada(data, maximo: int):
    """Valida: Requerimientos 2.4, 5.2.

    Para toda cadena cuya longitud supere el maximo del campo, se devuelve un
    mensaje de error; para longitudes dentro del limite, se devuelve None.
    """
    # Cadena que supera el maximo.
    excedida = data.draw(st.text(min_size=maximo + 1, max_size=maximo + 50))
    assert validar_longitud_maxima(excedida, maximo, "Nombre") is not None

    # Cadena dentro del limite (0..maximo) es aceptada.
    dentro = data.draw(st.text(min_size=0, max_size=maximo))
    assert validar_longitud_maxima(dentro, maximo, "Nombre") is None


# ---------------------------------------------------------------------------
# Property 10
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 10: El precio fuera del rango permitido es rechazado
@settings(max_examples=200)
@given(
    precio=st.decimals(
        allow_nan=False, allow_infinity=False, places=2,
        min_value=Decimal("-1000000"), max_value=Decimal("2000000"),
    )
)
def test_property_10_precio_fuera_de_rango_es_rechazado(precio: Decimal):
    """Valida: Requerimientos 5.3, 7.2.

    validar_precio devuelve un mensaje de error para precios < 0 o > 999999.99,
    y None para precios dentro de [0, 999999.99].
    """
    resultado = validar_precio(precio)
    if precio < Decimal("0") or precio > Decimal("999999.99"):
        assert resultado == (
            "El Precio debe ser igual o mayor que 0 y no mayor que 999999.99."
        )
    else:
        assert resultado is None


# ---------------------------------------------------------------------------
# Property 12
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 12: El reporte diario solo incluye pedidos de la fecha seleccionada
@settings(max_examples=150)
@given(
    fechas=st.lists(
        st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
        min_size=0,
        max_size=30,
    ),
    fecha_sel=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)),
)
def test_property_12_reporte_solo_incluye_fecha_seleccionada(fechas, fecha_sel):
    """Valida: Requerimientos 12.3.

    filtrar_por_fecha devuelve exactamente los pedidos cuya fecha es igual a la
    fecha seleccionada, y ninguno de otra fecha.
    """
    pedidos = [
        PedidoFake(estado="Pendiente", total=Decimal("10.00"), fecha=f) for f in fechas
    ]
    resultado = filtrar_por_fecha(pedidos, fecha_sel)

    # Todos los del resultado son de la fecha seleccionada.
    assert all(p.fecha == fecha_sel for p in resultado)
    # No falta ninguno: el conteo coincide con los que tienen esa fecha.
    esperados = [p for p in pedidos if p.fecha == fecha_sel]
    assert len(resultado) == len(esperados)


# ---------------------------------------------------------------------------
# Property 13
# ---------------------------------------------------------------------------

# Feature: control-de-pedidos, Property 13: El reporte cuenta todos los pedidos y suma solo los no cancelados
@settings(max_examples=200)
@given(
    pedidos_data=st.lists(
        st.tuples(
            estados_validos_st,
            precios_validos,
        ),
        min_size=0,
        max_size=30,
    )
)
def test_property_13_reporte_cuenta_todos_y_suma_no_cancelados(pedidos_data):
    """Valida: Requerimientos 12.4, 12.5.

    resumir_reporte cuenta TODOS los pedidos (incluidos los Cancelados) y suma
    solo los `.total` de los que NO estan Cancelados. La suma es 0 si la lista
    esta vacia o si todos estan Cancelados.
    """
    pedidos = [
        PedidoFake(estado=estado, total=total, fecha=date(2025, 1, 1))
        for estado, total in pedidos_data
    ]
    resumen = resumir_reporte(pedidos)

    # cantidad_pedidos cuenta todos.
    assert resumen.cantidad_pedidos == len(pedidos)

    # suma_ventas suma solo los no cancelados.
    esperado = sum(
        (p.total for p in pedidos if p.estado != "Cancelado"), Decimal("0")
    )
    assert resumen.suma_ventas == esperado

    # Si no hay pedidos o todos estan cancelados, la suma es 0.
    if not pedidos or all(p.estado == "Cancelado" for p in pedidos):
        assert resumen.suma_ventas == Decimal("0")
