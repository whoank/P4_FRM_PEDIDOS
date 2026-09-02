# test_properties_pedidos.py
# Pruebas basadas en propiedades (Hypothesis) del router de pedidos (Tareas 8.2, 8.3).
#
# Property 2 (Tarea 8.2) -> Valida Req. 8.4: el precio_unitario de un pedido es
#   el precio vigente del producto al crearlo, y un cambio posterior del precio
#   del producto NO altera el precio_unitario ni el total del pedido ya creado.
# Property 3 (Tarea 8.3) -> Valida Req. 8.2, 8.3: todo pedido nuevo nace con
#   estado "Pendiente" y fecha igual al dia de hoy.
#
# IMPORTANTE - probar sin PostgreSQL/psycopg:
# Fijamos DATABASE_URL a SQLite en memoria ANTES de importar database.py y
# montamos una app FastAPI de prueba con el router de pedidos. Para no acoplar
# con el router de productos (que otro agente implementa en paralelo), los
# productos y clientes se crean/actualizan directamente por ORM con la sesion
# de prueba; los pedidos se crean y consultan a nivel de API (TestClient).
#
# Nota de rendimiento: cada ejemplo de Hypothesis crea una app y un engine
# SQLite en memoria nuevos para aislar el estado entre ejemplos.

import os

# Fijar DATABASE_URL a SQLite ANTES de importar database.py (evita psycopg).
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from datetime import date
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db

import models
from models import Cliente, Producto, Role, User

from routers import pedidos as pedidos_router

# Ajuste de compatibilidad (Roles y Permisos): el router de pedidos usa
# require_permission("PEDIDOS"), que depende de get_current_user y consulta
# permisos_de_usuario(db, usuario). En cada ejemplo de Hypothesis sembramos el
# rol Administrador (todos los permisos) y sobrescribimos get_current_user con un
# admin que lo tiene en la BD de prueba, para no romper las propiedades.
from auth_dependencies import get_current_user
from roles_service import seed_roles_y_permisos
from auth_service import hash_password


def _montar_entorno():
    """Crea una app FastAPI de prueba con SQLite en memoria y el router de pedidos.

    Devuelve (client, TestingSessionLocal, cerrar) donde `cerrar` libera los
    recursos del engine. Se invoca en cada ejemplo de Hypothesis para aislar el
    estado entre ejecuciones.
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
    app.include_router(pedidos_router.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)

    def cerrar():
        client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    return client, TestingSessionLocal, cerrar


def _crear_cliente(SessionLocal):
    db = SessionLocal()
    try:
        cliente = Cliente(nombre="Cliente Prueba", telefono="555", direccion=None)
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
        return cliente.id
    finally:
        db.close()


def _crear_producto(SessionLocal, precio: Decimal):
    db = SessionLocal()
    try:
        producto = Producto(
            nombre="Producto Prueba",
            descripcion=None,
            precio=precio,
            disponible=True,
        )
        db.add(producto)
        db.commit()
        db.refresh(producto)
        return producto.id
    finally:
        db.close()


def _actualizar_precio_producto(SessionLocal, producto_id: int, nuevo_precio: Decimal):
    """Cambia el precio del producto directamente en la BD (sin router de productos)."""
    db = SessionLocal()
    try:
        producto = db.get(Producto, producto_id)
        producto.precio = nuevo_precio
        db.commit()
    finally:
        db.close()


# Generadores validos:
# - Precios: Decimal en [0.00, 999999.99] con 2 decimales (rango del diseno).
# - Cantidades: enteros en [1, 9999] (Req. 8.5).
precios_validos = st.integers(min_value=0, max_value=99999999).map(
    lambda centavos: (Decimal(centavos) / Decimal(100)).quantize(Decimal("0.01"))
)
cantidades_validas = st.integers(min_value=1, max_value=9999)


# ---------------------------------------------------------------------------
# Feature: control-de-pedidos, Property 2: El precio unitario del pedido es el vigente y no cambia despues
# Valida: Requerimientos 8.4
# ---------------------------------------------------------------------------
@settings(max_examples=100, deadline=None)
@given(
    precio_inicial=precios_validos,
    precio_nuevo=precios_validos,
    cantidad=cantidades_validas,
)
def test_property_2_precio_unitario_vigente_e_inmutable(
    precio_inicial, precio_nuevo, cantidad
):
    """El precio_unitario del pedido es el precio vigente del producto al crearlo,
    y un cambio posterior del precio del producto no altera el pedido (Req. 8.4)."""
    client, SessionLocal, cerrar = _montar_entorno()
    try:
        cliente_id = _crear_cliente(SessionLocal)
        producto_id = _crear_producto(SessionLocal, precio_inicial)

        # Crear el pedido con el precio vigente (precio_inicial).
        respuesta = client.post(
            "/api/pedidos",
            json={
                "cliente_id": cliente_id,
                "producto_id": producto_id,
                "cantidad": cantidad,
            },
        )
        assert respuesta.status_code == 201
        pedido = respuesta.json()

        # El precio_unitario copiado debe ser el vigente al crear.
        assert Decimal(str(pedido["precio_unitario"])) == precio_inicial
        # El total debe ser cantidad * precio_inicial.
        esperado = (Decimal(cantidad) * precio_inicial).quantize(Decimal("0.01"))
        assert Decimal(str(pedido["total"])) == esperado

        # Cambiamos el precio del producto DIRECTAMENTE en la BD de prueba.
        _actualizar_precio_producto(SessionLocal, producto_id, precio_nuevo)

        # Volvemos a consultar el pedido: su precio_unitario y total NO cambian.
        lista = client.get("/api/pedidos").json()
        pedido_persistido = next(p for p in lista if p["id"] == pedido["id"])
        assert Decimal(str(pedido_persistido["precio_unitario"])) == precio_inicial
        assert Decimal(str(pedido_persistido["total"])) == esperado
    finally:
        cerrar()


# ---------------------------------------------------------------------------
# Feature: control-de-pedidos, Property 3: Todo pedido nuevo nace Pendiente y con la fecha de hoy
# Valida: Requerimientos 8.2, 8.3
# ---------------------------------------------------------------------------
@settings(max_examples=100, deadline=None)
@given(
    precio=precios_validos,
    cantidad=cantidades_validas,
)
def test_property_3_pedido_nace_pendiente_con_fecha_hoy(precio, cantidad):
    """Todo pedido creado con datos validos tiene estado inicial "Pendiente" y
    fecha igual al dia de hoy (Req. 8.2, 8.3)."""
    client, SessionLocal, cerrar = _montar_entorno()
    try:
        cliente_id = _crear_cliente(SessionLocal)
        producto_id = _crear_producto(SessionLocal, precio)

        respuesta = client.post(
            "/api/pedidos",
            json={
                "cliente_id": cliente_id,
                "producto_id": producto_id,
                "cantidad": cantidad,
            },
        )
        assert respuesta.status_code == 201
        pedido = respuesta.json()

        assert pedido["estado"] == "Pendiente"
        assert pedido["fecha"] == date.today().isoformat()
    finally:
        cerrar()
