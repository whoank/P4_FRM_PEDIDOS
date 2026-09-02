# test_roles.py
# Pruebas por ejemplo / integracion del sistema de "Roles y Permisos" por opcion
# de menu (autorizacion) de la app "Control de Pedidos".
#
# Cubre la gestion de roles (routers/roles.py), la asignacion de rol a usuarios
# (routers/usuarios.py) y el calculo de permisos efectivos (roles_service +
# routers/auth.py /auth/me). Sigue el MISMO patron que las pruebas existentes
# (ver tests/test_usuarios.py como referencia):
#
#   - Primera linea util: fijar DATABASE_URL a SQLite en memoria ANTES de
#     importar database.py (que llama a create_engine al importarse), para
#     evitar cargar psycopg / PostgreSQL.
#   - Engine SQLite con StaticPool y check_same_thread=False (datos compartidos
#     entre conexiones durante toda la prueba).
#   - App FastAPI de prueba que incluye los routers reales, sobrescribiendo
#     get_db (sesion de prueba) y get_current_user (usuario simulado).
#
# DETALLE CLAVE DE AUTORIZACION (documentado):
# Los endpoints usan Depends(require_permission("X")), que internamente depende
# de get_current_user. Sobrescribir get_current_user fija QUIEN es el usuario
# autenticado, PERO require_permission sigue consultando permisos_de_usuario(db,
# usuario) contra la BD de prueba. Por eso el usuario simulado DEBE tener, en la
# BD de prueba, un rol con los permisos reales para pasar (403 en caso
# contrario). Aprovechamos esto para probar tanto el acceso permitido como el
# denegado, cambiando cual usuario resuelve el override de get_current_user
# mediante el helper `set_usuario_actual`.

import os

# Fijar DATABASE_URL a SQLite ANTES de importar database.py (evita psycopg).
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import joinedload, sessionmaker
from sqlalchemy.pool import StaticPool

# Base y get_db reales; get_db se sobrescribe con la version de prueba.
from database import Base, get_db

# Importar models registra TODAS las tablas (incluidas users, roles, permissions
# y la asociativa role_permissions) en Base.metadata.
import models  # noqa: F401
from models import Permission, Role, User

# Routers reales bajo prueba.
from routers import roles as roles_router
from routers import usuarios as usuarios_router
from routers import auth as auth_router

# Dependencia de autenticacion a sobrescribir.
from auth_dependencies import get_current_user

# Servicios del modulo de autorizacion y de hashing seguro.
from roles_service import (
    ROL_ADMINISTRADOR,
    permisos_de_usuario,
    seed_roles_y_permisos,
)
from auth_service import hash_password


@pytest.fixture()
def entorno():
    """App FastAPI de prueba con SQLite en memoria y los routers de roles/usuarios/auth.

    Devuelve la tupla (client, TestingSessionLocal, set_usuario_actual, ids):
      - client: TestClient para llamar a la API.
      - TestingSessionLocal: fabrica de sesiones ligada al engine de prueba, para
        operar la BD directamente por ORM y llamar a permisos_de_usuario.
      - set_usuario_actual(user_id): cambia QUE usuario resuelve el override de
        get_current_user (para simular distintos roles/permisos en cada caso).
      - ids: diccionario con ids utiles sembrados por la fixture:
          {"admin", "rol_admin"}.

    Sembrado inicial (con seed_roles_y_permisos, idempotente):
      - Catalogo completo de permisos (CLIENTES, PRODUCTOS, PEDIDOS,
        REPORTE_DIARIO, ADMINISTRACION, USUARIOS, ROLES).
      - Rol "Administrador" con TODOS los permisos.
      - Un usuario "admin" ACTIVO con el rol Administrador (para los casos de
        acceso total y como usuario actual por defecto).
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    # Estado mutable: id del usuario que actualmente "esta autenticado".
    estado = {"user_id": None}

    # --- Sembrado inicial de permisos, rol Administrador y usuario admin ------
    db_inicial = TestingSessionLocal()
    try:
        # Creamos primero el usuario admin (sin rol); el seed le asignara el rol
        # Administrador porque queda con role_id NULL (comportamiento del seed).
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            active=True,
        )
        db_inicial.add(admin)
        db_inicial.commit()

        # Siembra idempotente: catalogo de permisos + rol Administrador con todos
        # los permisos + asignacion del rol a los usuarios con role_id NULL (admin).
        seed_roles_y_permisos(db_inicial)

        # Recuperamos ids ya asignados.
        admin = db_inicial.query(User).filter(User.username == "admin").first()
        rol_admin = (
            db_inicial.query(Role).filter(Role.nombre == ROL_ADMINISTRADOR).first()
        )
        ids = {"admin": admin.id, "rol_admin": rol_admin.id}
        # Por defecto, el usuario actual es el administrador.
        estado["user_id"] = admin.id
    finally:
        db_inicial.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user():
        # Devuelve el usuario "actual" consultado en una sesion nueva ligada a la
        # BD de prueba (StaticPool comparte datos). Cambiar estado["user_id"] con
        # set_usuario_actual altera quien resuelve esta dependencia.
        #
        # IMPORTANTE: require_permission accede luego a usuario.role y a
        # rol.permisos. Como esta funcion cierra la sesion antes de devolver el
        # objeto, cargamos de forma ANTICIPADA (joinedload) el rol y sus permisos
        # para evitar un DetachedInstanceError al hacer lazy-load tras el cierre.
        db = TestingSessionLocal()
        try:
            return (
                db.query(User)
                .options(joinedload(User.role).joinedload(Role.permisos))
                .filter(User.id == estado["user_id"])
                .first()
            )
        finally:
            db.close()

    def set_usuario_actual(user_id: int) -> None:
        """Fija que usuario resolvera get_current_user en las siguientes llamadas."""
        estado["user_id"] = user_id

    app = FastAPI()
    app.include_router(roles_router.router)
    app.include_router(usuarios_router.router)
    app.include_router(auth_router.router)
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client, TestingSessionLocal, set_usuario_actual, ids

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# Helpers para preparar datos por ORM (roles y usuarios) en la BD de prueba
# ---------------------------------------------------------------------------
def _crear_rol(SessionLocal, nombre, codigos_permisos, activo=True, descripcion=None):
    """Crea un rol con los permisos indicados (por codigo) y devuelve su id.

    Los permisos deben existir en el catalogo (sembrado por seed_roles_y_permisos).
    """
    db = SessionLocal()
    try:
        permisos = (
            db.query(Permission).filter(Permission.codigo.in_(set(codigos_permisos))).all()
            if codigos_permisos
            else []
        )
        rol = Role(nombre=nombre, descripcion=descripcion, activo=activo)
        rol.permisos = permisos
        db.add(rol)
        db.commit()
        db.refresh(rol)
        return rol.id
    finally:
        db.close()


def _crear_usuario(SessionLocal, username, role_id=None, active=True):
    """Crea un usuario (opcionalmente con rol) y devuelve su id."""
    db = SessionLocal()
    try:
        usuario = User(
            username=username,
            password_hash=hash_password("secreta1"),
            active=active,
            role_id=role_id,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario.id
    finally:
        db.close()


# ===========================================================================
# Caso 1: Crear un rol correctamente (requisito: crear rol con permisos)
# ===========================================================================
def test_crear_rol_correctamente(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # El usuario actual (admin) tiene el permiso ROLES.

    respuesta = client.post(
        "/api/roles",
        json={
            "nombre": "Operador",
            "descripcion": "Operacion diaria",
            "activo": True,
            "permisos": ["CLIENTES", "PRODUCTOS", "PEDIDOS"],
        },
    )
    assert respuesta.status_code == 201
    creado = respuesta.json()

    # La respuesta trae los 3 permisos y cantidad_permisos == 3.
    assert creado["nombre"] == "Operador"
    assert creado["activo"] is True
    assert creado["cantidad_permisos"] == 3
    codigos = {p["codigo"] for p in creado["permisos"]}
    assert codigos == {"CLIENTES", "PRODUCTOS", "PEDIDOS"}


# ===========================================================================
# Caso 2: Listar roles (requisito: listar roles existentes)
# ===========================================================================
def test_listar_roles(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # Creamos dos roles adicionales por API.
    client.post("/api/roles", json={"nombre": "Operador", "permisos": ["PEDIDOS"]})
    client.post("/api/roles", json={"nombre": "Cajero", "permisos": ["CLIENTES"]})

    respuesta = client.get("/api/roles")
    assert respuesta.status_code == 200
    nombres = {r["nombre"] for r in respuesta.json()}
    # Debe incluir el rol Administrador (seed) y los dos creados.
    assert {"Administrador", "Operador", "Cajero"}.issubset(nombres)


# ===========================================================================
# Caso 3 y 5: Editar un rol reemplazando permisos (agregar y quitar)
# ===========================================================================
def test_editar_rol_reemplaza_permisos(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # Creamos un rol con 3 permisos.
    creado = client.post(
        "/api/roles",
        json={"nombre": "Operador", "permisos": ["CLIENTES", "PRODUCTOS", "PEDIDOS"]},
    ).json()
    rol_id = creado["id"]

    # Editamos: cambiamos nombre/descripcion y REEMPLAZAMOS los permisos por ["PEDIDOS"].
    respuesta = client.put(
        f"/api/roles/{rol_id}",
        json={
            "nombre": "Operador Basico",
            "descripcion": "Solo pedidos",
            "activo": True,
            "permisos": ["PEDIDOS"],
        },
    )
    assert respuesta.status_code == 200
    actualizado = respuesta.json()

    # Refleja exactamente 1 permiso tras el reemplazo.
    assert actualizado["nombre"] == "Operador Basico"
    assert actualizado["cantidad_permisos"] == 1
    codigos = {p["codigo"] for p in actualizado["permisos"]}
    assert codigos == {"PEDIDOS"}
    # Assert explicito (caso 5): los permisos quitados ya no estan.
    assert "CLIENTES" not in codigos
    assert "PRODUCTOS" not in codigos


# ===========================================================================
# Caso 4: Nombre de rol duplicado -> 400 con mensaje con tilde
# ===========================================================================
def test_nombre_rol_duplicado(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # Primer alta correcta.
    assert (
        client.post("/api/roles", json={"nombre": "Operador", "permisos": []}).status_code
        == 201
    )
    # Segundo alta con el mismo nombre -> 400.
    respuesta = client.post("/api/roles", json={"nombre": "Operador", "permisos": []})
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Ya existe un rol con ese nombre."


# ===========================================================================
# Caso 6: Permiso inexistente al crear/editar -> 400 con mensaje con tilde
# ===========================================================================
def test_permiso_inexistente_al_crear(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    respuesta = client.post(
        "/api/roles", json={"nombre": "RolInvalido", "permisos": ["NO_EXISTE"]}
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Uno o más permisos no son válidos."


def test_permiso_inexistente_al_editar(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    creado = client.post(
        "/api/roles", json={"nombre": "Operador", "permisos": ["PEDIDOS"]}
    ).json()
    # PUT con un codigo inexistente -> 400.
    respuesta = client.put(
        f"/api/roles/{creado['id']}",
        json={"nombre": "Operador", "activo": True, "permisos": ["NO_EXISTE"]},
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["detail"] == "Uno o más permisos no son válidos."


# ===========================================================================
# Caso 7: Usuario SIN el permiso -> 403 (roles y usuarios)
# ===========================================================================
def test_usuario_sin_permiso_roles_recibe_403(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # Rol que NO incluye ROLES (solo CLIENTES) y un usuario con ese rol.
    rol_id = _crear_rol(SessionLocal, "SoloClientes", ["CLIENTES"])
    user_id = _crear_usuario(SessionLocal, "sin_roles", role_id=rol_id)

    # Cambiamos el usuario autenticado al que NO tiene el permiso ROLES.
    set_usuario_actual(user_id)
    respuesta = client.get("/api/roles")
    assert respuesta.status_code == 403


def test_usuario_sin_permiso_usuarios_recibe_403(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # Rol que NO incluye USUARIOS (solo PEDIDOS) y un usuario con ese rol.
    rol_id = _crear_rol(SessionLocal, "SoloPedidos", ["PEDIDOS"])
    user_id = _crear_usuario(SessionLocal, "sin_usuarios", role_id=rol_id)

    set_usuario_actual(user_id)
    respuesta = client.get("/api/usuarios")
    assert respuesta.status_code == 403


# ===========================================================================
# Caso 8: Usuario CON el permiso -> 200 (roles y usuarios)
# ===========================================================================
def test_usuario_con_permiso_roles_ok(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # Rol que SI incluye ROLES y un usuario con ese rol.
    rol_id = _crear_rol(SessionLocal, "GestorRoles", ["ROLES"])
    user_id = _crear_usuario(SessionLocal, "con_roles", role_id=rol_id)

    set_usuario_actual(user_id)
    respuesta = client.get("/api/roles")
    assert respuesta.status_code == 200


def test_usuario_con_permiso_usuarios_ok(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # Rol que SI incluye USUARIOS y un usuario con ese rol.
    rol_id = _crear_rol(SessionLocal, "GestorUsuarios", ["USUARIOS"])
    user_id = _crear_usuario(SessionLocal, "con_usuarios", role_id=rol_id)

    set_usuario_actual(user_id)
    respuesta = client.get("/api/usuarios")
    assert respuesta.status_code == 200


# ===========================================================================
# Caso 9: El administrador tiene acceso total (roles y usuarios)
# ===========================================================================
def test_administrador_acceso_total(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # El usuario actual por defecto es admin (rol Administrador con TODOS los permisos).
    assert client.get("/api/roles").status_code == 200
    assert client.get("/api/usuarios").status_code == 200
    # Tambien puede consultar el catalogo de permisos (protegido con ROLES).
    assert client.get("/api/permisos").status_code == 200


# ===========================================================================
# Caso 10: Un rol INACTIVO no se puede asignar a un usuario -> 400 con tilde
# ===========================================================================
def test_rol_inactivo_no_asignable(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # El usuario actual (admin) tiene USUARIOS, asi que puede intentar asignar rol.
    rol_inactivo_id = _crear_rol(SessionLocal, "Deshabilitado", ["PEDIDOS"], activo=False)
    # Usuario destino al que intentaremos asignarle el rol inactivo.
    destino_id = _crear_usuario(SessionLocal, "destino", role_id=None)

    respuesta = client.patch(
        f"/api/usuarios/{destino_id}/rol", json={"role_id": rol_inactivo_id}
    )
    assert respuesta.status_code == 400
    assert (
        respuesta.json()["detail"] == "El rol seleccionado no existe o no está activo."
    )


# ===========================================================================
# Caso 11: permisos_de_usuario devuelve los permisos efectivos (base de /auth/me)
# ===========================================================================
def test_permisos_de_usuario_directo(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno

    # (a) Usuario con rol ACTIVO que tiene CLIENTES y PEDIDOS -> {CLIENTES, PEDIDOS}.
    rol_activo_id = _crear_rol(SessionLocal, "RolActivo", ["CLIENTES", "PEDIDOS"])
    user_con_rol = _crear_usuario(SessionLocal, "con_rol_activo", role_id=rol_activo_id)

    # (b) Usuario SIN rol -> set() vacio.
    user_sin_rol = _crear_usuario(SessionLocal, "sin_rol", role_id=None)

    # (c) Usuario con rol INACTIVO -> set() vacio (el rol inactivo no otorga permisos).
    rol_inactivo_id = _crear_rol(SessionLocal, "RolInactivo", ["CLIENTES"], activo=False)
    user_rol_inactivo = _crear_usuario(
        SessionLocal, "con_rol_inactivo", role_id=rol_inactivo_id
    )

    db = SessionLocal()
    try:
        assert permisos_de_usuario(db, db.get(User, user_con_rol)) == {
            "CLIENTES",
            "PEDIDOS",
        }
        assert permisos_de_usuario(db, db.get(User, user_sin_rol)) == set()
        assert permisos_de_usuario(db, db.get(User, user_rol_inactivo)) == set()
    finally:
        db.close()


# ===========================================================================
# Caso 11 (por API): GET /auth/me expone role + permissions coherentes
# ===========================================================================
def test_auth_me_expone_permisos(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    rol_id = _crear_rol(SessionLocal, "RolMe", ["CLIENTES", "PEDIDOS"])
    user_id = _crear_usuario(SessionLocal, "usuario_me", role_id=rol_id)

    set_usuario_actual(user_id)
    respuesta = client.get("/auth/me")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["username"] == "usuario_me"
    assert cuerpo["role"]["nombre"] == "RolMe"
    # permissions es la lista de codigos efectivos (ordenada por el router).
    assert set(cuerpo["permissions"]) == {"CLIENTES", "PEDIDOS"}


# ===========================================================================
# Caso 12: Salvaguarda - no dejar el sistema sin acceso administrativo
# ===========================================================================
def test_no_dejar_sin_admin_al_desactivar_unico_rol_con_roles(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # El seed dejo: rol Administrador (con ROLES) + usuario admin ACTIVO con ese rol.
    # Es el UNICO rol activo que otorga ROLES a un usuario activo, asi que
    # desactivarlo debe rechazarse con 400 (salvaguarda).
    respuesta = client.patch(
        f"/api/roles/{ids['rol_admin']}/estado", json={"activo": False}
    )
    assert respuesta.status_code == 400
    assert (
        respuesta.json()["detail"]
        == "No se puede desactivar: el sistema quedaría sin acceso administrativo."
    )


def test_desactivar_rol_con_roles_permitido_si_existe_otro_soporte(entorno):
    client, SessionLocal, set_usuario_actual, ids = entorno
    # Creamos OTRO rol activo con ROLES y se lo asignamos a OTRO usuario activo.
    # Asi el sistema conserva acceso administrativo aunque desactivemos uno.
    otro_rol_id = _crear_rol(SessionLocal, "AdminSecundario", ["ROLES"])
    _crear_usuario(SessionLocal, "admin2", role_id=otro_rol_id, active=True)

    # Ahora desactivar el rol Administrador SI debe permitirse (200), porque
    # AdminSecundario sigue dando ROLES a un usuario activo.
    respuesta = client.patch(
        f"/api/roles/{ids['rol_admin']}/estado", json={"activo": False}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False
