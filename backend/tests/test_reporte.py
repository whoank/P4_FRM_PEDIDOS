# test_reporte.py
# Pruebas por ejemplo / integracion del router del reporte diario (Tarea 9.2).
#
# Cubre (Req. 12.1, 12.2, 12.3, 12.4, 12.5, 12.6):
#   - Dia por defecto (sin query `fecha`) = hoy (Req. 12.1).
#   - Cambio de dia con `?fecha=` (Req. 12.2).
#   - Filtrado por fecha: solo los pedidos de esa fecha (Req. 12.3).
#   - Conteo incluye Cancelados (Req. 12.4).
#   - Suma excluye Cancelados y es 0 si todos estan Cancelados (Req. 12.5).
#   - Dia sin pedidos -> cantidad 0, suma 0, lista vacia (Req. 12.6).
#
# IMPORTANTE - probar sin PostgreSQL/psycopg:
# En el entorno local NO esta instalado psycopg ni corre PostgreSQL. Fijamos
# DATABASE_URL a SQLite en memoria ANTES de importar database.py (que llama a
# create_engine al importarse) y montamos una app FastAPI de prueba que incluye
# solo el router de reporte, sobrescribiendo get_db con un engine SQLite propio.
# Los datos de prueba (clientes, productos, pedidos con distintas fechas y
# estados) se insertan directamente por ORM con la sesion de prueba. Se asigna
# EXPLICITAMENTE .fecha y .estado a cada pedido (no dependemos del server_default
# de fecha, que en SQLite no aplica igual que en PostgreSQL).

import os

# Fijar DATABASE_URL a SQLite ANTES de importar database.py (evita psycopg).
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker
from sqlalchemy.pool import StaticPool

# Base y get_db reales; get_db se sobrescribe con la version de prueba.
from database import Base, get_db

# Importar models registra las tablas (Cliente, Producto, Pedido, User, Role,
# Permission, ...) en Base.metadata.
import models
from models import Cliente, Pedido, Producto, Role, User

# Router bajo prueba.
from routers import reporte as reporte_router

# Ajuste de compatibilidad (Roles y Permisos): el endpoint usa
# require_permission("REPORTE_DIARIO"), que depende de get_current_user y
# consulta permisos_de_usuario(db, usuario). Sembramos rol Administrador (todos
# los permisos) y sobrescribimos get_current_user con un admin que lo tiene en la
# BD de prueba, para no romper los asserts de negocio.
from auth_dependencies import get_current_user
from roles_service import seed_roles_y_permisos
from auth_service import hash_password


@pytest.fixture()
def entorno():
    """App FastAPI de prueba con SQLite en memoria y el router de reporte.

    Devuelve (client, TestingSessionLocal) para insertar datos base por ORM y
    llamar a la API mediante el TestClient.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    # Sembrar permisos + rol Administrador y crear un usuario admin con ese rol.
    db_inicial = TestingSessionLocal()
    try:
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            active=True,
        )
        db_inicial.add(admin)
        db_inicial.commit()
        seed_roles_y_permisos(db_inicial)
        admin = db_inicial.query(User).filter(User.username == "admin").first()
        admin_id = admin.id
    finally:
        db_inicial.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user():
        # joinedload del rol + permisos para evitar DetachedInstanceError al
        # leerlos en require_permission tras cerrar esta sesion.
        db = TestingSessionLocal()
        try:
            return (
                db.query(User)
                .options(joinedload(User.role).joinedload(Role.permisos))
                .filter(User.id == admin_id)
                .first()
            )
        finally:
            db.close()

    app = FastAPI()
    app.include_router(reporte_router.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Helpers para preparar datos por ORM (sin depender de otros routers)
# ---------------------------------------------------------------------------
def _crear_cliente(SessionLocal, nombre="Ana Perez"):
    db = SessionLocal()
    try:
        cliente = Cliente(nombre=nombre, telefono="555-1234", direccion="Calle 1")
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente.id
    finally:
        db.close()


def _crear_producto(SessionLocal, nombre="Hamburguesa", precio="55.00"):
    db = SessionLocal()
    try:
        producto = Producto(
            nombre=nombre,
            descripcion="Clasica",
            precio=Decimal(precio),
            disponible=True,
        )
        db.add(producto)
        db.commit()
        db.refresh(producto)
        return producto.id
    finally:
        db.close()


def _crear_pedido(
    SessionLocal,
    cliente_id,
    producto_id,
    cantidad,
    precio_unitario,
    fecha,
    estado="Pendiente",
):
    """Inserta un pedido por ORM asignando EXPLICITAMENTE fecha y estado.

    El total se calcula aqui (cantidad * precio_unitario) con Decimal para no
    depender de la logica del router de pedidos.
    """
    db = SessionLocal()
    try:
        precio = Decimal(precio_unitario)
        pedido = Pedido(
            cliente_id=cliente_id,
            producto_id=producto_id,
            cantidad=cantidad,
            precio_unitario=precio,
            total=Decimal(cantidad) * precio,
            fecha=fecha,
            estado=estado,
        )
        db.add(pedido)
        db.commit()
        db.refresh(pedido)
        return pedido.id
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Dia por defecto (sin query `fecha`) = hoy (Req. 12.1)
# ---------------------------------------------------------------------------
def test_reporte_sin_fecha_usa_el_dia_actual(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal, precio="55.00")

    hoy = date.today()
    ayer = hoy - timedelta(days=1)
    # Un pedido de hoy y uno de ayer: sin `fecha`, solo debe salir el de hoy.
    _crear_pedido(SessionLocal, cliente_id, producto_id, 3, "55.00", hoy)
    _crear_pedido(SessionLocal, cliente_id, producto_id, 1, "55.00", ayer)

    respuesta = client.get("/api/reporte-diario")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert cuerpo["fecha"] == hoy.isoformat()
    assert cuerpo["cantidad_pedidos"] == 1
    assert Decimal(str(cuerpo["suma_ventas"])) == Decimal("165.00")
    assert len(cuerpo["pedidos"]) == 1
    assert cuerpo["pedidos"][0]["fecha"] == hoy.isoformat()


# ---------------------------------------------------------------------------
# Cambio de dia con `?fecha=` (Req. 12.2)
# ---------------------------------------------------------------------------
def test_reporte_con_fecha_devuelve_los_de_ese_dia(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal, precio="10.00")

    hoy = date.today()
    otro_dia = date(2025, 1, 15)
    _crear_pedido(SessionLocal, cliente_id, producto_id, 2, "10.00", hoy)
    _crear_pedido(SessionLocal, cliente_id, producto_id, 5, "10.00", otro_dia)

    respuesta = client.get(f"/api/reporte-diario?fecha={otro_dia.isoformat()}")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert cuerpo["fecha"] == otro_dia.isoformat()
    assert cuerpo["cantidad_pedidos"] == 1
    assert Decimal(str(cuerpo["suma_ventas"])) == Decimal("50.00")
    assert len(cuerpo["pedidos"]) == 1


# ---------------------------------------------------------------------------
# Filtrado por fecha: solo los de esa fecha (Req. 12.3)
# ---------------------------------------------------------------------------
def test_reporte_filtra_solo_los_pedidos_de_la_fecha(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal, precio="20.00")

    dia_a = date(2025, 3, 1)
    dia_b = date(2025, 3, 2)
    dia_c = date(2025, 3, 3)
    _crear_pedido(SessionLocal, cliente_id, producto_id, 1, "20.00", dia_a)
    _crear_pedido(SessionLocal, cliente_id, producto_id, 2, "20.00", dia_b)
    _crear_pedido(SessionLocal, cliente_id, producto_id, 3, "20.00", dia_b)
    _crear_pedido(SessionLocal, cliente_id, producto_id, 4, "20.00", dia_c)

    respuesta = client.get(f"/api/reporte-diario?fecha={dia_b.isoformat()}")
    cuerpo = respuesta.json()

    assert cuerpo["cantidad_pedidos"] == 2
    # Todos los pedidos devueltos son del dia B y solo de ese dia.
    assert all(p["fecha"] == dia_b.isoformat() for p in cuerpo["pedidos"])
    # Suma = 2*20 + 3*20 = 100.00
    assert Decimal(str(cuerpo["suma_ventas"])) == Decimal("100.00")


# ---------------------------------------------------------------------------
# Conteo incluye Cancelados (Req. 12.4)
# ---------------------------------------------------------------------------
def test_conteo_incluye_cancelados(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal, precio="30.00")

    dia = date(2025, 4, 10)
    _crear_pedido(SessionLocal, cliente_id, producto_id, 1, "30.00", dia, "Entregado")
    _crear_pedido(SessionLocal, cliente_id, producto_id, 2, "30.00", dia, "Cancelado")
    _crear_pedido(SessionLocal, cliente_id, producto_id, 3, "30.00", dia, "Pendiente")

    respuesta = client.get(f"/api/reporte-diario?fecha={dia.isoformat()}")
    cuerpo = respuesta.json()

    # cantidad_pedidos cuenta TODOS los del dia, incluido el Cancelado.
    assert cuerpo["cantidad_pedidos"] == 3
    # suma_ventas excluye el Cancelado: 1*30 + 3*30 = 120.00 (no cuenta 2*30).
    assert Decimal(str(cuerpo["suma_ventas"])) == Decimal("120.00")


# ---------------------------------------------------------------------------
# Suma excluye Cancelados y es 0 si todos estan Cancelados (Req. 12.5)
# ---------------------------------------------------------------------------
def test_suma_es_cero_si_todos_cancelados(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal, precio="99.00")

    dia = date(2025, 5, 5)
    _crear_pedido(SessionLocal, cliente_id, producto_id, 2, "99.00", dia, "Cancelado")
    _crear_pedido(SessionLocal, cliente_id, producto_id, 4, "99.00", dia, "Cancelado")

    respuesta = client.get(f"/api/reporte-diario?fecha={dia.isoformat()}")
    cuerpo = respuesta.json()

    # Se cuentan los 2 pedidos, pero la suma es 0 porque todos estan Cancelados.
    assert cuerpo["cantidad_pedidos"] == 2
    assert Decimal(str(cuerpo["suma_ventas"])) == Decimal("0")
    assert len(cuerpo["pedidos"]) == 2


# ---------------------------------------------------------------------------
# Dia sin pedidos -> cantidad 0, suma 0, lista vacia (Req. 12.6)
# ---------------------------------------------------------------------------
def test_reporte_dia_sin_pedidos_devuelve_ceros_y_lista_vacia(entorno):
    client, SessionLocal = entorno
    cliente_id = _crear_cliente(SessionLocal)
    producto_id = _crear_producto(SessionLocal, precio="15.00")

    # Hay un pedido en otra fecha, pero el dia consultado no tiene ninguno.
    _crear_pedido(SessionLocal, cliente_id, producto_id, 1, "15.00", date(2025, 6, 1))

    dia_vacio = date(2025, 6, 2)
    respuesta = client.get(f"/api/reporte-diario?fecha={dia_vacio.isoformat()}")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert cuerpo["fecha"] == dia_vacio.isoformat()
    assert cuerpo["cantidad_pedidos"] == 0
    assert Decimal(str(cuerpo["suma_ventas"])) == Decimal("0")
    assert cuerpo["pedidos"] == []
