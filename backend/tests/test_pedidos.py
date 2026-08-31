# test_pedidos.py
# Pruebas por ejemplo / integracion del router de pedidos (Tarea 8.4).
#
# Cubre (Req. 8.1, 8.6, 8.7, 8.8, 8.9, 10.1, 10.3, 11.1, 11.2):
#   - crear pedido valido y verificar total, estado "Pendiente" y fecha de hoy.
#   - pedido sin cliente / cliente inexistente -> 400.
#   - producto inexistente -> 400; producto no disponible -> 400 con mensaje.
#   - cambio de estado valido (PATCH) -> 200; invalido -> 400 y conserva anterior.
#   - lista vacia al inicio y listado con nombres tras crear.
#
# IMPORTANTE - probar sin PostgreSQL/psycopg:
# En el entorno local NO esta instalado psycopg ni corre PostgreSQL. Fijamos
# DATABASE_URL a SQLite en memoria ANTES de importar database.py (que llama a
# create_engine al importarse) y montamos una app FastAPI de prueba que incluye
# solo el router de pedidos, sobrescribiendo get_db con un engine SQLite propio.
# Los datos de prueba (clientes y productos) se insertan directamente por ORM
# con la sesion de prueba, en lugar de depender de otros routers (que otro
# agente esta implementando en paralelo).

import os

# Fijar DATABASE_URL a SQLite ANTES de importar database.py (evita psycopg).
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Base y get_db reales; get_db se sobrescribe con la version de prueba.
from database import Base, get_db

# Importar models registra las tablas (Cliente, Producto, Pedido) en Base.metadata.
import models
from models import Cliente, Producto

# Router bajo prueba.
from routers import pedidos as pedidos_router


@pytest.fixture()
def entorno():
    """Crea una app FastAPI de prueba con SQLite en memoria y el router de pedidos.

    Devuelve una tupla (client, TestingSessionLocal) para que las pruebas puedan
    insertar datos base (clientes/productos) directamente por ORM y tambien
    llamar a la API mediante el TestClient.
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
    app.include_router(pedidos_router.router)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Helpers para preparar datos base por ORM (sin depender de otros routers)
# ---------------------------------------------------------------------------
def _crear_cliente(SessionLocal, nombre="Ana Perez", telefono="555-1234"):
    db = SessionLocal()
    try:
        cliente = Cliente(nombre=nombre, telefono=telefono, direccion="Calle 1")
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente.id
    finally:
        db.close()


def _crear_producto(SessionLocal, nombre="Hamburguesa", precio="55.00", disponible=True):
    db = SessionLocal()
    try:
        producto = Producto(
            nombre=nombre,
            descripcion="Clasica",
            precio=Decimal(precio),
            disponible=disponible,
        )
        db.add(producto)
        db.commit()
        db.refresh(producto)
        return producto.id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Lista vacia al inicio (Req. 11.2)
# ---------------------------------------------------------------------------
def test_listar_pedidos_vacio_devuelve_lista_vacia(entorno):
    client, _ = entorno
    respuesta = client.get("/api/pedidos")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


# ---------------------------------------------------------------------------
# Crear pedido valido: total, estado y fecha (Req. 8.1, 8.9, 9.1)
# ---------------------------------------------------------------------------
def test_crear_pedido_valido_calcula_total_estado_y_fecha(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal, precio="55.00")

    respuesta = client.post(
        "/api/pedidos",
        json={"cliente_id": cliente_id, "producto_id": producto_id, "cantidad": 3},
    )
    assert respuesta.status_code == 201
    pedido = respuesta.json()

    # Total = cantidad * precio (3 * 55.00 = 165.00) (Req. 9.1).
    assert Decimal(str(pedido["total"])) == Decimal("165.00")
    assert Decimal(str(pedido["precio_unitario"])) == Decimal("55.00")
    # Estado inicial "Pendiente" (Req. 8.3) y fecha de hoy (Req. 8.2).
    assert pedido["estado"] == "Pendiente"
    assert pedido["fecha"] == date.today().isoformat()
    # Datos desnormalizados presentes (Req. 8.9).
    assert pedido["cliente_nombre"] == "Ana Perez"
    assert pedido["producto_nombre"] == "Hamburguesa"


# ---------------------------------------------------------------------------
# Cliente inexistente -> 400 (Req. 8.6)
# ---------------------------------------------------------------------------
def test_crear_pedido_cliente_inexistente_devuelve_400(entorno):
    client, SessionLocal = entorno
    producto_id = _crear_producto(SessionLocal)

    respuesta = client.post(
        "/api/pedidos",
        json={"cliente_id": 999, "producto_id": producto_id, "cantidad": 1},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El Cliente no existe."


# ---------------------------------------------------------------------------
# Producto inexistente -> 400 (Req. 8.7)
# ---------------------------------------------------------------------------
def test_crear_pedido_producto_inexistente_devuelve_400(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)

    respuesta = client.post(
        "/api/pedidos",
        json={"cliente_id": cliente_id, "producto_id": 999, "cantidad": 1},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El Producto no existe."


# ---------------------------------------------------------------------------
# Producto no disponible -> 400 con mensaje del diseno (Req. 8.8)
# ---------------------------------------------------------------------------
def test_crear_pedido_producto_no_disponible_devuelve_400(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal, disponible=False)

    respuesta = client.post(
        "/api/pedidos",
        json={"cliente_id": cliente_id, "producto_id": producto_id, "cantidad": 2},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El Producto no esta disponible."


# ---------------------------------------------------------------------------
# Listar incluye el creado con nombres (Req. 11.1)
# ---------------------------------------------------------------------------
def test_listar_pedidos_incluye_creado_con_nombres(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal, nombre="Luis")
    producto_id = _crear_producto(SessionLocal, nombre="Pizza", precio="80.00")

    client.post(
        "/api/pedidos",
        json={"cliente_id": cliente_id, "producto_id": producto_id, "cantidad": 2},
    )

    lista = client.get("/api/pedidos").json()
    assert len(lista) == 1
    assert lista[0]["cliente_nombre"] == "Luis"
    assert lista[0]["producto_nombre"] == "Pizza"
    assert Decimal(str(lista[0]["total"])) == Decimal("160.00")


# ---------------------------------------------------------------------------
# Cambio de estado valido -> 200 y refleja el nuevo estado (Req. 10.1, 10.2)
# ---------------------------------------------------------------------------
def test_cambiar_estado_valido_actualiza(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal)

    creado = client.post(
        "/api/pedidos",
        json={"cliente_id": cliente_id, "producto_id": producto_id, "cantidad": 1},
    ).json()

    respuesta = client.patch(
        f"/api/pedidos/{creado['id']}/estado", json={"estado": "Preparando"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "Preparando"

    # Se refleja en el listado (Req. 10.2).
    lista = client.get("/api/pedidos").json()
    assert lista[0]["estado"] == "Preparando"


# ---------------------------------------------------------------------------
# Cambio de estado invalido -> 400 y conserva el estado anterior (Req. 10.3)
# ---------------------------------------------------------------------------
def test_cambiar_estado_invalido_devuelve_400_y_conserva_anterior(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal)

    creado = client.post(
        "/api/pedidos",
        json={"cliente_id": cliente_id, "producto_id": producto_id, "cantidad": 1},
    ).json()

    respuesta = client.patch(
        f"/api/pedidos/{creado['id']}/estado", json={"estado": "Enviado"}
    )
    assert respuesta.status_code == 400
    assert (
        respuesta.json()["detail"]
        == "El Estado debe ser uno de: Pendiente, Preparando, Entregado, Cancelado."
    )

    # El estado anterior ("Pendiente") se conserva (Req. 10.3).
    lista = client.get("/api/pedidos").json()
    assert lista[0]["estado"] == "Pendiente"


def test_cambiar_estado_vacio_devuelve_400_y_conserva_anterior(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal)

    creado = client.post(
        "/api/pedidos",
        json={"cliente_id": cliente_id, "producto_id": producto_id, "cantidad": 1},
    ).json()

    respuesta = client.patch(
        f"/api/pedidos/{creado['id']}/estado", json={"estado": ""}
    )
    assert respuesta.status_code == 400
    lista = client.get("/api/pedidos").json()
    assert lista[0]["estado"] == "Pendiente"


def test_cambiar_estado_pedido_inexistente_devuelve_404(entorno):
    client, _ = entorno
    respuesta = client.patch("/api/pedidos/999/estado", json={"estado": "Entregado"})
    assert respuesta.status_code == 404
