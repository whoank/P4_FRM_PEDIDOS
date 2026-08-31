# test_productos.py
# Pruebas por ejemplo y de integracion del router de Productos (Tarea 7.3).
#
# Cubre (Req. 5.1, 5.4, 5.6, 6.1, 6.2, 7.1, 7.3):
#   - crear producto (201) y aparece en la lista.
#   - crear con disponible por defecto True (Req. 5.5, 5.6).
#   - listar (Req. 6.1) y lista vacia (Req. 6.2 -> GET devuelve []).
#   - obtener por id y 404.
#   - editar (PUT) y persistencia (Req. 7.1).
#   - filtro ?solo_disponibles=true devuelve solo los disponibles (Req. 7.3).
#   - precio no numerico -> 422 de Pydantic (Req. 5.4).
#   - precio fuera de rango (negativo o > 999999.99) -> 400 (Req. 5.3/7.2).
#   - nombre vacio/solo espacios -> rechazado (400/422).
#
# IMPORTANTE - probar sin PostgreSQL/psycopg:
# En el entorno local NO esta instalado psycopg ni corre PostgreSQL. Se fija
# DATABASE_URL a SQLite en memoria ANTES de importar database.py (que llama a
# create_engine al importarse) y se monta una app FastAPI de prueba que incluye
# SOLO el router de productos, sobrescribiendo get_db con un engine SQLite en
# memoria. No se altera el esquema de produccion. El modelo Producto usa un
# CHECK de precio y server_default text('true') para disponible; en SQLite el
# CHECK se traduce correctamente y el server_default funciona, por lo que
# create_all no requiere ajustes.

import os

# Debe ir ANTES de importar database/models/routers (evita cargar psycopg).
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Base y get_db reales del proyecto; get_db se sobreescribe con la version de prueba.
from database import Base, get_db

# Importar models registra las tablas (Cliente, Producto, Pedido) en Base.metadata.
import models  # noqa: F401

# Router bajo prueba.
from routers import productos as productos_router


@pytest.fixture()
def client():
    """App FastAPI de prueba con SQLite en memoria y el router de productos.

    - Engine SQLite en memoria compartido entre conexiones (StaticPool) para que
      los datos persistan durante toda la prueba.
    - Se crean las tablas con Base.metadata.create_all sobre ESE engine.
    - Se sobrescribe get_db mediante app.dependency_overrides, evitando por
      completo PostgreSQL/psycopg.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(productos_router.router)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Lista vacia al inicio (Req. 6.1, 6.2)
# ---------------------------------------------------------------------------
def test_listar_productos_vacio_devuelve_lista_vacia(client):
    respuesta = client.get("/api/productos")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


# ---------------------------------------------------------------------------
# Crear (201) + aparece en la lista (Req. 5.1, 5.6, 6.1)
# ---------------------------------------------------------------------------
def test_crear_producto_devuelve_201_y_aparece_en_la_lista(client):
    payload = {
        "nombre": "Hamburguesa",
        "descripcion": "Clasica",
        "precio": "55.00",
        "disponible": True,
    }
    respuesta = client.post("/api/productos", json=payload)

    assert respuesta.status_code == 201
    creado = respuesta.json()
    assert creado["id"] > 0
    assert creado["nombre"] == "Hamburguesa"
    assert creado["descripcion"] == "Clasica"
    assert str(creado["precio"]) in ("55.00", "55.0", "55")
    assert creado["disponible"] is True

    # La lista ahora incluye el producto creado (Req. 5.6, 6.1).
    lista = client.get("/api/productos").json()
    assert len(lista) == 1
    assert lista[0]["id"] == creado["id"]
    assert lista[0]["nombre"] == "Hamburguesa"


# ---------------------------------------------------------------------------
# disponible por defecto True cuando no se envia (Req. 5.5)
# ---------------------------------------------------------------------------
def test_crear_producto_sin_disponible_es_true_por_defecto(client):
    payload = {"nombre": "Pizza", "precio": "80.00"}  # sin campo disponible
    respuesta = client.post("/api/productos", json=payload)
    assert respuesta.status_code == 201
    assert respuesta.json()["disponible"] is True


def test_crear_producto_sin_descripcion_es_valido(client):
    # La descripcion es opcional (Req. 5.1).
    payload = {"nombre": "Agua", "precio": "10.00"}
    respuesta = client.post("/api/productos", json=payload)
    assert respuesta.status_code == 201
    assert respuesta.json()["descripcion"] is None


# ---------------------------------------------------------------------------
# Obtener por id (Req. 6.1) y 404
# ---------------------------------------------------------------------------
def test_obtener_producto_por_id(client):
    creado = client.post(
        "/api/productos", json={"nombre": "Taco", "precio": "25.00"}
    ).json()

    respuesta = client.get(f"/api/productos/{creado['id']}")
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Taco"


def test_obtener_producto_inexistente_devuelve_404(client):
    respuesta = client.get("/api/productos/999")
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()


# ---------------------------------------------------------------------------
# Editar (PUT) y verificar persistencia (Req. 7.1)
# ---------------------------------------------------------------------------
def test_editar_producto_actualiza_y_persiste(client):
    creado = client.post(
        "/api/productos",
        json={"nombre": "Taco", "descripcion": "Al pastor", "precio": "25.00"},
    ).json()

    respuesta = client.put(
        f"/api/productos/{creado['id']}",
        json={
            "nombre": "Taco especial",
            "descripcion": "Doble",
            "precio": "30.00",
            "disponible": False,
        },
    )
    assert respuesta.status_code == 200
    actualizado = respuesta.json()
    assert actualizado["nombre"] == "Taco especial"
    assert actualizado["disponible"] is False

    # La persistencia se refleja al volver a leer (Req. 7.1).
    obtenido = client.get(f"/api/productos/{creado['id']}").json()
    assert obtenido["nombre"] == "Taco especial"
    assert obtenido["descripcion"] == "Doble"
    assert obtenido["disponible"] is False


def test_editar_producto_inexistente_devuelve_404(client):
    respuesta = client.put(
        "/api/productos/999", json={"nombre": "X", "precio": "1.00"}
    )
    assert respuesta.status_code == 404


# ---------------------------------------------------------------------------
# Filtro ?solo_disponibles=true (Req. 7.3)
# ---------------------------------------------------------------------------
def test_filtro_solo_disponibles_devuelve_solo_los_disponibles(client):
    # Producto disponible y no disponible.
    client.post(
        "/api/productos", json={"nombre": "Disponible", "precio": "10.00", "disponible": True}
    )
    client.post(
        "/api/productos", json={"nombre": "Agotado", "precio": "20.00", "disponible": False}
    )

    # Sin filtro: se ven los dos.
    todos = client.get("/api/productos").json()
    assert len(todos) == 2

    # Con filtro: solo el disponible (Req. 7.3).
    disponibles = client.get("/api/productos", params={"solo_disponibles": "true"}).json()
    assert len(disponibles) == 1
    assert disponibles[0]["nombre"] == "Disponible"
    assert disponibles[0]["disponible"] is True


# ---------------------------------------------------------------------------
# Precio no numerico -> 422 de Pydantic (Req. 5.4)
# ---------------------------------------------------------------------------
def test_crear_producto_precio_no_numerico_devuelve_422(client):
    respuesta = client.post(
        "/api/productos", json={"nombre": "Cosa", "precio": "abc"}
    )
    assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# Precio fuera de rango -> rechazado (Req. 5.3, 7.2)
# ---------------------------------------------------------------------------
def test_crear_producto_precio_negativo_es_rechazado(client):
    respuesta = client.post(
        "/api/productos", json={"nombre": "Cosa", "precio": "-1.00"}
    )
    # Pydantic (ge=0) da 422; si el precio pasara el esquema, el servicio da 400.
    assert respuesta.status_code in (400, 422)


def test_crear_producto_precio_excede_maximo_es_rechazado(client):
    respuesta = client.post(
        "/api/productos", json={"nombre": "Cosa", "precio": "1000000.00"}
    )
    assert respuesta.status_code in (400, 422)


def test_editar_producto_precio_fuera_de_rango_es_rechazado(client):
    creado = client.post(
        "/api/productos", json={"nombre": "Taco", "precio": "25.00"}
    ).json()
    respuesta = client.put(
        f"/api/productos/{creado['id']}",
        json={"nombre": "Taco", "precio": "-5.00"},
    )
    assert respuesta.status_code in (400, 422)
    # El producto conserva su precio original.
    obtenido = client.get(f"/api/productos/{creado['id']}").json()
    assert str(obtenido["precio"]) in ("25.00", "25.0", "25")


# ---------------------------------------------------------------------------
# Nombre vacio / solo espacios -> rechazado (Req. 5.2)
# ---------------------------------------------------------------------------
def test_crear_producto_nombre_solo_espacios_devuelve_400(client):
    # Solo espacios: Pydantic (min_length=1) no lo detecta; el servicio si -> 400.
    respuesta = client.post(
        "/api/productos", json={"nombre": "   ", "precio": "10.00"}
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El Nombre es obligatorio."


def test_crear_producto_nombre_vacio_es_rechazado(client):
    respuesta = client.post(
        "/api/productos", json={"nombre": "", "precio": "10.00"}
    )
    assert respuesta.status_code in (400, 422)


def test_crear_producto_nombre_excede_longitud_es_rechazado(client):
    respuesta = client.post(
        "/api/productos", json={"nombre": "a" * 101, "precio": "10.00"}
    )
    assert respuesta.status_code in (400, 422)
