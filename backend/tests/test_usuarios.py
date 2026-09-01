# test_usuarios.py
# Pruebas por ejemplo / integracion del router de gestion de usuarios.
#
# Cubre el alta, listado, activacion/desactivacion (baja logica), cambio de
# contrasena y la invalidacion de sesiones asociada, ademas de la garantia de
# que los hashes nunca aparecen en las respuestas JSON.
#
# IMPORTANTE - probar sin PostgreSQL/psycopg:
# En el entorno local NO esta instalado psycopg ni corre PostgreSQL. Fijamos
# DATABASE_URL a SQLite en memoria ANTES de importar database.py (que llama a
# create_engine al importarse) y montamos una app FastAPI de prueba que incluye
# solo el router de usuarios, sobrescribiendo get_db con un engine SQLite propio
# y get_current_user para simular un administrador autenticado.

import os

# Fijar DATABASE_URL a SQLite ANTES de importar database.py (evita psycopg).
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Base y get_db reales; get_db se sobrescribe con la version de prueba.
from database import Base, get_db

# Importar models registra las tablas (incluidas users y user_session) en Base.metadata.
import models
from models import User, UserSession

# Router bajo prueba y dependencia de autenticacion a sobrescribir.
from routers import usuarios as usuarios_router
from auth_dependencies import get_current_user

# Servicios de autenticacion usados para verificar hashes y sesiones a bajo nivel.
from auth_service import (
    hash_password,
    verificar_password,
    crear_sesion,
    obtener_usuario_por_token,
)


@pytest.fixture()
def entorno():
    """Crea una app FastAPI de prueba con SQLite en memoria y el router de usuarios.

    Sobrescribe get_db (sesion de prueba) y get_current_user (administrador
    autenticado simulado), de modo que los endpoints protegidos respondan sin
    necesitar una cookie real. Devuelve (client, TestingSessionLocal) para que
    las pruebas puedan operar la BD directamente por ORM y llamar a la API.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    # Creamos un usuario administrador en la BD de prueba para simular la sesion.
    db_inicial = TestingSessionLocal()
    try:
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            active=True,
        )
        db_inicial.add(admin)
        db_inicial.commit()
        db_inicial.refresh(admin)
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
        # Devuelve el administrador consultado en una sesion nueva (robusto):
        # asi el objeto esta asociado a la BD de prueba compartida (StaticPool).
        db = TestingSessionLocal()
        try:
            return db.get(User, admin_id)
        finally:
            db.close()

    app = FastAPI()
    app.include_router(usuarios_router.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Helper para crear un usuario via API (POST /api/usuarios)
# ---------------------------------------------------------------------------
def _crear_usuario_api(client, username, password, password_confirmacion=None):
    """Crea un usuario mediante la API y devuelve la respuesta HTTP.

    Si no se indica password_confirmacion, se usa la misma password (caso feliz).
    Nunca se registra la contrasena en logs.
    """
    if password_confirmacion is None:
        password_confirmacion = password
    return client.post(
        "/api/usuarios",
        json={
            "username": username,
            "password": password,
            "password_confirmacion": password_confirmacion,
        },
    )


# ---------------------------------------------------------------------------
# Caso 1: Crear usuario correctamente + aparece en el listado (y caso 4: activo)
# ---------------------------------------------------------------------------
def test_crear_usuario_correctamente_y_aparece_en_listado(entorno):
    client, _ = entorno

    respuesta = _crear_usuario_api(client, "nuevo", "secreta1")
    assert respuesta.status_code == 201
    creado = respuesta.json()

    # La respuesta trae id, username y estado activo (caso 1 y caso 4).
    assert "id" in creado
    assert creado["username"] == "nuevo"
    assert creado["active"] is True

    # El usuario aparece en el listado GET /api/usuarios.
    lista = client.get("/api/usuarios").json()
    usernames = [u["username"] for u in lista]
    assert "nuevo" in usernames


# ---------------------------------------------------------------------------
# Caso 4 (explicito): el usuario recien creado queda activo
# ---------------------------------------------------------------------------
def test_usuario_nuevo_queda_activo(entorno):
    client, _ = entorno

    creado = _crear_usuario_api(client, "activo_por_defecto", "secreta1").json()
    # Afirmamos de forma explicita que active es True al crearse.
    assert creado["active"] is True


# ---------------------------------------------------------------------------
# Caso 2: Impedir usuarios duplicados -> 400 con mensaje con tilde
# ---------------------------------------------------------------------------
def test_impedir_usuarios_duplicados(entorno):
    client, _ = entorno

    # Primer alta correcta.
    assert _crear_usuario_api(client, "nuevo", "secreta1").status_code == 201

    # Segundo alta con el mismo username -> 400.
    respuesta = _crear_usuario_api(client, "nuevo", "secreta1")
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "El nombre de usuario ya está en uso."


# ---------------------------------------------------------------------------
# Caso 3: password y confirmacion no coinciden -> 400 con mensaje con tilde
# ---------------------------------------------------------------------------
def test_password_y_confirmacion_no_coinciden(entorno):
    client, _ = entorno

    respuesta = _crear_usuario_api(
        client, "desalineado", "secreta1", password_confirmacion="otra1234"
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Las contraseñas no coinciden."


# ---------------------------------------------------------------------------
# Caso 5: Desactivar usuario -> 200 y active == False
# ---------------------------------------------------------------------------
def test_desactivar_usuario(entorno):
    client, _ = entorno

    creado = _crear_usuario_api(client, "a_desactivar", "secreta1").json()

    respuesta = client.patch(f"/api/usuarios/{creado['id']}/desactivar")
    assert respuesta.status_code == 200
    assert respuesta.json()["active"] is False


# ---------------------------------------------------------------------------
# Caso 6: Usuario desactivado no puede iniciar sesion (validacion a nivel de estado)
# ---------------------------------------------------------------------------
def test_usuario_desactivado_no_puede_iniciar_sesion(entorno):
    client, SessionLocal = entorno

    creado = _crear_usuario_api(client, "sin_login", "secreta1").json()

    # Creamos una sesion ANTES de desactivar y comprobamos que el token resuelve.
    db = SessionLocal()
    try:
        usuario = db.get(User, creado["id"])
        token = crear_sesion(db, usuario)
        assert obtener_usuario_por_token(db, token) is not None
    finally:
        db.close()

    # Desactivamos via API (baja logica + invalidacion de sesiones).
    assert client.patch(f"/api/usuarios/{creado['id']}/desactivar").status_code == 200

    # El usuario queda inactivo y el token ya no resuelve (login real lo rechazaria).
    db = SessionLocal()
    try:
        usuario = db.get(User, creado["id"])
        assert usuario.active is False
        # obtener_usuario_por_token devuelve None si el usuario esta inactivo
        # y/o la sesion fue invalidada.
        assert obtener_usuario_por_token(db, token) is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Caso 7: Activar usuario nuevamente -> 200 y active == True
# ---------------------------------------------------------------------------
def test_activar_usuario_nuevamente(entorno):
    client, _ = entorno

    creado = _crear_usuario_api(client, "a_reactivar", "secreta1").json()

    # Primero lo desactivamos y luego lo volvemos a activar.
    assert client.patch(f"/api/usuarios/{creado['id']}/desactivar").status_code == 200

    respuesta = client.patch(f"/api/usuarios/{creado['id']}/activar")
    assert respuesta.status_code == 200
    assert respuesta.json()["active"] is True


# ---------------------------------------------------------------------------
# Casos 8, 9 y 10: Cambiar contrasena; la anterior deja de funcionar; la nueva funciona
# ---------------------------------------------------------------------------
def test_cambiar_password_y_verificar_hashes(entorno):
    client, SessionLocal = entorno

    creado = _crear_usuario_api(client, "cambia_pass", "vieja123").json()

    # Caso 8: cambio de contrasena correcto -> 200 y mensaje con tilde.
    respuesta = client.patch(
        f"/api/usuarios/{creado['id']}/password",
        json={"password": "nueva123", "password_confirmacion": "nueva123"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["detail"] == "Contraseña actualizada."

    # Volvemos a consultar el usuario en la BD para ver el hash actualizado.
    db = SessionLocal()
    try:
        usuario = db.get(User, creado["id"])
        # Caso 9: la contrasena anterior deja de funcionar.
        assert verificar_password("vieja123", usuario.password_hash) is False
        # Caso 10: la nueva contrasena funciona.
        assert verificar_password("nueva123", usuario.password_hash) is True
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Caso 11: Las sesiones se invalidan al desactivar
# ---------------------------------------------------------------------------
def test_sesiones_se_invalidan_al_desactivar(entorno):
    client, SessionLocal = entorno

    creado = _crear_usuario_api(client, "invalida_desactivar", "secreta1").json()
    user_id = creado["id"]

    # Creamos una sesion con la misma TestingSessionLocal (StaticPool en memoria
    # comparte datos con el override de get_db).
    db = SessionLocal()
    try:
        usuario = db.get(User, user_id)
        token = crear_sesion(db, usuario)
        # La sesion recien creada debe resolver al usuario.
        assert obtener_usuario_por_token(db, token) is not None
    finally:
        db.close()

    # Desactivamos via API: debe invalidar TODAS las sesiones del usuario.
    assert client.patch(f"/api/usuarios/{user_id}/desactivar").status_code == 200

    db = SessionLocal()
    try:
        # No queda ninguna UserSession del usuario.
        assert db.query(UserSession).filter_by(user_id=user_id).count() == 0
        # Y el token ya no resuelve a ningun usuario.
        assert obtener_usuario_por_token(db, token) is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Caso 12: Las sesiones se invalidan al cambiar la contrasena
# ---------------------------------------------------------------------------
def test_sesiones_se_invalidan_al_cambiar_password(entorno):
    client, SessionLocal = entorno

    creado = _crear_usuario_api(client, "invalida_password", "vieja123").json()
    user_id = creado["id"]

    # Creamos una sesion antes del cambio de contrasena.
    db = SessionLocal()
    try:
        usuario = db.get(User, user_id)
        token = crear_sesion(db, usuario)
        assert obtener_usuario_por_token(db, token) is not None
    finally:
        db.close()

    # Cambiamos la contrasena via API: debe invalidar todas las sesiones.
    respuesta = client.patch(
        f"/api/usuarios/{user_id}/password",
        json={"password": "nueva123", "password_confirmacion": "nueva123"},
    )
    assert respuesta.status_code == 200

    db = SessionLocal()
    try:
        # No queda ninguna UserSession del usuario.
        assert db.query(UserSession).filter_by(user_id=user_id).count() == 0
        # Y el token anterior ya no resuelve.
        assert obtener_usuario_por_token(db, token) is None
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Caso 13: Los hashes nunca aparecen en las respuestas JSON
# ---------------------------------------------------------------------------
def test_hashes_nunca_aparecen_en_respuestas(entorno):
    client, _ = entorno

    # En la respuesta del POST no deben existir claves sensibles.
    creado = _crear_usuario_api(client, "sin_hash", "secreta1").json()
    assert "password_hash" not in creado
    assert "token_hash" not in creado

    # En cada item del listado tampoco deben existir claves sensibles.
    lista = client.get("/api/usuarios").json()
    for item in lista:
        assert "password_hash" not in item
        assert "token_hash" not in item
