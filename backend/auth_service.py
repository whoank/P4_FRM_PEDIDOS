# auth_service.py
# Logica pura y de acceso a datos del modulo de autenticacion por sesion.
#
# Responsabilidades:
#   - Hashear y verificar contrasenas con bcrypt (nunca se guarda la clave en claro).
#   - Generar tokens de sesion criptograficamente seguros y su hash SHA-256.
#   - Crear, resolver e invalidar sesiones en la tabla user_session.
#   - Sembrar el usuario inicial de forma idempotente.
#
# Regla de seguridad: NUNCA se registran (log) ni se devuelven contrasenas ni
# tokens en claro. En la base de datos se guarda solo el hash del token.

import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from auth_config import SESSION_EXPIRATION_MINUTES
from models import User, UserSession


# --- Hashing de contrasenas -------------------------------------------------
def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt de una contrasena en claro.

    bcrypt incorpora un salt aleatorio dentro del propio hash, por lo que no hay
    que gestionarlo aparte. El resultado se guarda en User.password_hash.
    """
    import bcrypt

    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verificar_password(password: str, password_hash: str) -> bool:
    """Comprueba si una contrasena en claro coincide con su hash bcrypt.

    Devuelve False (en lugar de propagar la excepcion) si el hash almacenado es
    invalido o esta corrupto, para que el flujo de login trate esos casos como
    credenciales incorrectas.
    """
    import bcrypt

    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, TypeError):
        return False


# --- Tokens de sesion -------------------------------------------------------
def generar_token() -> str:
    """Genera un token de sesion aleatorio y criptograficamente seguro.

    Se entrega en claro al cliente (en la cookie); en la base de datos solo se
    guarda su hash (ver hash_token).
    """
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Devuelve el SHA-256 (hex) de un token, para guardarlo/buscarlo en la BD.

    Se usa SHA-256 (no bcrypt) porque el token ya es aleatorio y de alta entropia:
    solo necesitamos un digest fijo para indexar y comparar, sin coste de fuerza
    bruta relevante.
    """
    return hashlib.sha256(token.encode()).hexdigest()


# --- Gestion de sesiones ----------------------------------------------------
def crear_sesion(db: Session, user: User) -> str:
    """Crea una sesion para el usuario y devuelve el TOKEN en claro.

    Guarda en user_session el hash del token y su expiracion, actualiza
    last_login del usuario y commitea. El token en claro se devuelve para que el
    router lo coloque en la cookie; nunca se persiste en claro.
    """
    token = generar_token()
    ahora = datetime.utcnow()
    sesion = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=ahora + timedelta(minutes=SESSION_EXPIRATION_MINUTES),
    )
    db.add(sesion)
    # Registramos el ultimo inicio de sesion exitoso.
    user.last_login = ahora
    db.commit()
    return token


def obtener_usuario_por_token(db: Session, token: str) -> User | None:
    """Resuelve el usuario asociado a un token de sesion, o None si no es valido.

    Devuelve None si: no hay token, no existe la sesion, la sesion expiro o el
    usuario esta inactivo. Todas las consultas son parametrizadas via ORM.
    """
    if not token:
        return None

    sesion = (
        db.query(UserSession)
        .filter(UserSession.token_hash == hash_token(token))
        .first()
    )
    if sesion is None:
        return None

    # La sesion debe seguir vigente.
    if sesion.expires_at <= datetime.utcnow():
        return None

    # El usuario debe existir y estar activo.
    user = db.get(User, sesion.user_id)
    if user is None or not user.active:
        return None

    return user


def invalidar_sesion(db: Session, token: str) -> None:
    """Elimina la sesion asociada a un token, si existe (logout).

    Es segura de llamar aunque el token sea vacio o no corresponda a ninguna
    sesion: en ese caso no hace nada.
    """
    if not token:
        return

    sesion = (
        db.query(UserSession)
        .filter(UserSession.token_hash == hash_token(token))
        .first()
    )
    if sesion is not None:
        db.delete(sesion)
        db.commit()


# --- Seed idempotente del usuario inicial -----------------------------------
def crear_usuario_inicial(db: Session) -> None:
    """Crea el usuario inicial "juan123" solo si aun no existe (idempotente).

    Se invoca al arranque despues de crear_tablas(). Si el usuario ya existe, no
    hace nada, por lo que arrancar varias veces no duplica el usuario. La
    contrasena se usa solo inline para generar el hash; no se guarda en claro ni
    en variables de entorno.
    """
    existente = db.query(User).filter(User.username == "juan123").first()
    if existente is not None:
        return

    usuario = User(
        username="juan123",
        password_hash=hash_password("321juan"),
        active=True,
    )
    db.add(usuario)
    db.commit()

def invalidar_sesiones_usuario(db: Session, user_id: int) -> None:
    """Elimina TODAS las sesiones activas de un usuario (por user_id).

    Se usa al dar de baja un usuario o al cambiar su contrasena, para forzar
    que deba iniciar sesion de nuevo. Idempotente: si no hay sesiones, no hace
    nada. La consulta es parametrizada via ORM (nada de SQL crudo) y no registra
    ningun dato sensible.
    """
    # Borrado masivo por user_id: elimina 0..N filas segun cuantas sesiones haya.
    db.query(UserSession).filter(UserSession.user_id == user_id).delete()
    db.commit()
