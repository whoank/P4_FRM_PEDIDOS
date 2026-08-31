# test_properties_productos.py
# Prueba basada en propiedades (Hypothesis) para el recurso Producto (Tarea 7.2).
#
# Contiene UNICAMENTE la Property 11 del design.md (Correctness Properties).
#
# Enfoque usado: NIVEL DE ESQUEMA (Pydantic). Se construye ProductoCrear a
# partir de datos que NO incluyen el campo `disponible` y se verifica que el
# valor predeterminado resultante sea True. Es el enfoque mas simple,
# determinista y rapido, y es suficiente para validar la Property 11 (Req. 5.5):
# el valor por defecto de `disponible` vive en el esquema ProductoCrear, que es
# justamente lo que el router usa al crear un producto sin ese campo.
#
# Sin PostgreSQL/psycopg: este archivo solo importa schemas.py (Pydantic puro),
# por lo que no necesita base de datos. Aun asi, se fija DATABASE_URL a SQLite
# en memoria por si alguna importacion transitiva tocara database.py.

import os

# Precaucion defensiva (schemas.py no importa database, pero mantenemos el patron).
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from schemas import ProductoCrear


# Nombres validos: 1..100 caracteres que NO queden vacios tras strip().
# Se filtra para descartar cadenas compuestas solo por espacios en blanco.
nombres_validos = st.text(min_size=1, max_size=100).filter(
    lambda s: s.strip() != ""
)

# Precios validos: Decimal en [0, 999999.99] con 2 decimales.
# Se generan a partir de centavos enteros para garantizar exactamente 2 decimales
# y mantenerse dentro del rango permitido por el esquema (max_digits=8).
precios_validos = st.integers(min_value=0, max_value=99999999).map(
    lambda centavos: (Decimal(centavos) / Decimal(100)).quantize(Decimal("0.01"))
)


# Feature: control-de-pedidos, Property 11: Disponible es verdadero por defecto
#
# Property 11 valida Req. 5.5: para todo Producto creado sin especificar
# disponible, el resultado tiene disponible == True.
# **Validates: Requirements 5.5**
@settings(max_examples=200)
@given(nombre=nombres_validos, precio=precios_validos)
def test_property_11_disponible_true_por_defecto(nombre: str, precio: Decimal) -> None:
    # Datos SIN el campo `disponible`: se omite intencionalmente para probar el
    # valor predeterminado.
    datos_sin_disponible = {"nombre": nombre, "precio": precio}

    producto = ProductoCrear(**datos_sin_disponible)

    # Para todo producto creado sin especificar disponible, disponible es True.
    assert producto.disponible is True
