# test_examples.py
# Pruebas por ejemplo y de integracion (casos concretos y de borde) del backend.
#
# Tarea 6.2: CRUD de clientes con FastAPI TestClient (Req. 2.1, 2.6, 3.1, 3.2,
# 4.1, 4.3). Se cubre: crear (201), listar (incluye el creado), obtener por id,
# editar (PUT) y verificar persistencia, ademas de los casos de rechazo
# (nombre vacio/solo espacios, telefono vacio, longitud excedida) y lista vacia.
#
# IMPORTANTE - probar sin PostgreSQL/psycopg:
# En el entorno local NO esta instalado psycopg ni corre PostgreSQL. Para poder
# ejecutar estas pruebas montamos una app FastAPI de prueba que incluye SOLO el
# router de clientes y sobrescribimos la dependencia get_db para usar una base
# SQLite en memoria. Asi las pruebas no requieren psycopg ni una base real y no
# se altera el esquema de produccion (solo se crean las tablas sobre el engine
# de prueba). El modelo Cliente no usa defaults ni CHECK problematicos para
# SQLite, por lo que create_all funciona sin ajustes.

import os

# IMPORTANTE: fijar DATABASE_URL a SQLite ANTES de importar database.py.
# database.py llama a create_engine(DATABASE_URL) al importarse, y SQLAlchemy
# carga el driver de la URL de forma inmediata. Con la URL de PostgreSQL por
# defecto eso intentaria importar psycopg (no instalado en este entorno) y
# fallaria al recolectar las pruebas. Al apuntar a SQLite en memoria evitamos
# por completo psycopg sin modificar el codigo de produccion. El engine real de
# database.py no se usa en las pruebas: get_db se sobrescribe con un engine
# de prueba propio (ver la fixture `client`).
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker
from sqlalchemy.pool import StaticPool

# Base y get_db reales del proyecto; get_db se sobreescribe con la version de prueba.
from database import Base, get_db

# Importar models registra las tablas (Cliente, Producto, Pedido, User, Role,
# Permission, ...) en Base.metadata.
import models  # noqa: F401
from models import Role, User

# Router bajo prueba.
from routers import clientes as clientes_router

# Ajuste de compatibilidad (Roles y Permisos): los endpoints ahora usan
# require_permission("CLIENTES"), que internamente depende de get_current_user y
# consulta permisos_de_usuario(db, usuario). Para no romper estas pruebas de
# negocio, sembramos el catalogo de permisos + rol Administrador (con TODOS los
# permisos) y sobrescribimos get_current_user para devolver un usuario admin que,
# EN LA BD DE PRUEBA, tiene ese rol. Asi todos los endpoints protegidos pasan la
# autorizacion sin cambiar los asserts de negocio.
from auth_dependencies import get_current_user
from roles_service import seed_roles_y_permisos
from auth_service import hash_password


@pytest.fixture()
def client():
    """Crea una app FastAPI de prueba con SQLite en memoria y el router de clientes.

    - Engine SQLite en memoria compartido entre conexiones (StaticPool) para que
      los datos persistan durante toda la prueba.
    - Se crean las tablas con Base.metadata.create_all sobre ESE engine.
    - Se sobrescribe get_db con una sesion ligada al engine de prueba mediante
      app.dependency_overrides, evitando por completo PostgreSQL/psycopg.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Crear el esquema sobre el engine de prueba.
    Base.metadata.create_all(bind=engine)

    # Sembrar permisos + rol Administrador y crear un usuario admin con ese rol
    # (para superar require_permission). El seed asigna el rol Administrador a
    # todos los usuarios con role_id NULL, incluido el admin recien creado.
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
        # Usuario admin (con rol Administrador en la BD de prueba) para pasar la
        # autorizacion de require_permission en los endpoints protegidos. Cargamos
        # de forma anticipada (joinedload) el rol y sus permisos para evitar un
        # DetachedInstanceError al leerlos tras cerrar esta sesion.
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
    app.include_router(clientes_router.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    # Limpieza: liberar tablas y recursos del engine de prueba.
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Lista vacia al inicio (Req. 3.1, 3.2)
# ---------------------------------------------------------------------------
def test_listar_clientes_vacio_devuelve_lista_vacia(client):
    respuesta = client.get("/api/clientes")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


# ---------------------------------------------------------------------------
# Crear (201) + listar incluye el creado (Req. 2.1, 2.6, 3.1)
# ---------------------------------------------------------------------------
def test_crear_cliente_devuelve_201_y_aparece_en_la_lista(client):
    payload = {"nombre": "Ana Perez", "telefono": "555-1234", "direccion": "Calle 1 #23"}
    respuesta = client.post("/api/clientes", json=payload)

    assert respuesta.status_code == 201
    creado = respuesta.json()
    assert creado["id"] > 0
    assert creado["nombre"] == "Ana Perez"
    assert creado["telefono"] == "555-1234"
    assert creado["direccion"] == "Calle 1 #23"

    # La lista ahora incluye el cliente creado (Req. 2.6, 3.1).
    lista = client.get("/api/clientes").json()
    assert len(lista) == 1
    assert lista[0]["id"] == creado["id"]
    assert lista[0]["nombre"] == "Ana Perez"


def test_crear_cliente_sin_direccion_es_valido(client):
    # La direccion es opcional (Req. 2.1).
    payload = {"nombre": "Luis", "telefono": "999"}
    respuesta = client.post("/api/clientes", json=payload)
    assert respuesta.status_code == 201
    assert respuesta.json()["direccion"] is None


# ---------------------------------------------------------------------------
# Obtener por id (Req. 3.1) y 404
# ---------------------------------------------------------------------------
def test_obtener_cliente_por_id(client):
    creado = client.post(
        "/api/clientes", json={"nombre": "Ana", "telefono": "555"}
    ).json()

    respuesta = client.get(f"/api/clientes/{creado['id']}")
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Ana"


def test_obtener_cliente_inexistente_devuelve_404(client):
    respuesta = client.get("/api/clientes/999")
    assert respuesta.status_code == 404
    assert "detail" in respuesta.json()


# ---------------------------------------------------------------------------
# Editar (PUT) y verificar persistencia (Req. 4.1, 4.3)
# ---------------------------------------------------------------------------
def test_editar_cliente_actualiza_y_persiste(client):
    creado = client.post(
        "/api/clientes",
        json={"nombre": "Ana", "telefono": "555", "direccion": "Calle 1"},
    ).json()

    # Actualizamos los datos (Req. 4.1).
    respuesta = client.put(
        f"/api/clientes/{creado['id']}",
        json={"nombre": "Ana Maria", "telefono": "777", "direccion": "Calle 2"},
    )
    assert respuesta.status_code == 200
    actualizado = respuesta.json()
    assert actualizado["nombre"] == "Ana Maria"
    assert actualizado["telefono"] == "777"

    # La persistencia se refleja al volver a leer (Req. 4.3).
    lista = client.get("/api/clientes").json()
    assert len(lista) == 1
    assert lista[0]["nombre"] == "Ana Maria"
    assert lista[0]["telefono"] == "777"
    assert lista[0]["direccion"] == "Calle 2"


def test_editar_cliente_inexistente_devuelve_404(client):
    respuesta = client.put(
        "/api/clientes/999", json={"nombre": "X", "telefono": "1"}
    )
    assert respuesta.status_code == 404


# ---------------------------------------------------------------------------
# Rechazos por reglas de negocio (Req. 2.2, 2.3, 2.4, 4.2)
# ---------------------------------------------------------------------------
def test_crear_cliente_nombre_solo_espacios_devuelve_400(client):
    # Nombre compuesto solo por espacios: Pydantic (min_length=1) no lo detecta,
    # la regla de negocio del router si -> 400 con mensaje descriptivo (Req. 2.2).
    respuesta = client.post(
        "/api/clientes", json={"nombre": "   ", "telefono": "555"}
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El Nombre es obligatorio."


def test_crear_cliente_nombre_vacio_es_rechazado(client):
    # Nombre vacio: rechazado por esquema (422) o negocio (400). Ambos son rechazo.
    respuesta = client.post(
        "/api/clientes", json={"nombre": "", "telefono": "555"}
    )
    assert respuesta.status_code in (400, 422)


def test_crear_cliente_telefono_solo_espacios_devuelve_400(client):
    respuesta = client.post(
        "/api/clientes", json={"nombre": "Ana", "telefono": "   "}
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El Telefono es obligatorio."


def test_editar_cliente_nombre_vacio_es_rechazado(client):
    creado = client.post(
        "/api/clientes", json={"nombre": "Ana", "telefono": "555"}
    ).json()
    respuesta = client.put(
        f"/api/clientes/{creado['id']}", json={"nombre": "   ", "telefono": "555"}
    )
    # Rechazo de la actualizacion (Req. 4.2); el cliente conserva sus datos.
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El Nombre es obligatorio."
    # Verificamos que no se modifico.
    lista = client.get("/api/clientes").json()
    assert lista[0]["nombre"] == "Ana"


def test_crear_cliente_nombre_excede_longitud_es_rechazado(client):
    # Nombre de 101 caracteres: excede el maximo (100) -> rechazado (Req. 2.4).
    respuesta = client.post(
        "/api/clientes", json={"nombre": "a" * 101, "telefono": "555"}
    )
    assert respuesta.status_code in (400, 422)


def test_crear_cliente_telefono_excede_longitud_es_rechazado(client):
    # Telefono de 21 caracteres: excede el maximo (20) -> rechazado (Req. 2.4).
    respuesta = client.post(
        "/api/clientes", json={"nombre": "Ana", "telefono": "1" * 21}
    )
    assert respuesta.status_code in (400, 422)
