# database.py
# Configuracion de la conexion a la base de datos PostgreSQL mediante SQLAlchemy.
#
# Aqui se lee DATABASE_URL del entorno y se crean el engine, SessionLocal y la
# Base declarativa, junto con la dependencia get_db() para las sesiones y una
# funcion que reintenta la conexion al arranque.
#
# El backend corre en un contenedor y se conecta a la PostgreSQL del host de
# Windows a traves de host.docker.internal:5432. Como esa base es un servicio
# externo, conviene reintentar la conexion al inicio para tolerar que PostgreSQL
# tarde unos segundos en aceptar conexiones tras un arranque de Windows.

import logging
import os
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

# Logger sencillo para registrar los intentos de conexion al arranque.
logger = logging.getLogger(__name__)

# --- Lectura de la configuracion desde el entorno --------------------------
# La cadena de conexion se lee de la variable de entorno DATABASE_URL, con el
# formato: postgresql+psycopg://<usuario>:<password>@host.docker.internal:5432/<basedatos>
# Se define un valor por defecto solo como referencia educativa; en la practica
# lo aporta el archivo .env / docker-compose.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@host.docker.internal:5432/pedidos",
)

# --- Infraestructura de SQLAlchemy -----------------------------------------
# El engine es el punto central de comunicacion con la base de datos.
# pool_pre_ping=True hace que SQLAlchemy verifique la conexion antes de usarla,
# evitando errores por conexiones que quedaron inactivas.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# SessionLocal es una "fabrica" de sesiones: cada llamada crea una sesion nueva
# para interactuar con la base de datos dentro de una peticion.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarativa: los modelos ORM (Cliente, Producto, Pedido) heredaran de
# esta clase en la Tarea 2.2. Aqui solo la definimos para que models.py la importe.
Base = declarative_base()


# --- Dependencia de sesion para FastAPI ------------------------------------
def get_db():
    """Dependencia que entrega una sesion de base de datos y la cierra al final.

    Se usa como dependencia en los endpoints de FastAPI (Depends(get_db)).
    El patron try/finally garantiza que la sesion se cierre siempre, incluso
    si ocurre un error durante la peticion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Reintento de conexion al arranque -------------------------------------
def esperar_conexion(intentos: int = 10, espera_segundos: float = 2.0) -> None:
    """Intenta conectar a la base de datos varias veces antes de rendirse.

    Como la PostgreSQL del host puede tardar en aceptar conexiones al arranque,
    se prueba a conectar hasta `intentos` veces, esperando `espera_segundos`
    entre cada intento. Si se logra conectar, la funcion retorna; si se agotan
    los intentos, se relanza el ultimo error para que el arranque falle de
    forma clara.

    Args:
        intentos: numero maximo de intentos de conexion.
        espera_segundos: segundos de espera entre intentos.
    """
    ultimo_error: Exception | None = None

    for intento in range(1, intentos + 1):
        try:
            # Abrimos una conexion y ejecutamos una consulta trivial para
            # confirmar que la base realmente responde.
            with engine.connect() as conexion:
                conexion.execute(text("SELECT 1"))
            logger.info("Conexion a la base de datos establecida (intento %s).", intento)
            return
        except OperationalError as error:
            ultimo_error = error
            logger.warning(
                "No se pudo conectar a la base de datos (intento %s/%s). "
                "Reintentando en %s s...",
                intento,
                intentos,
                espera_segundos,
            )
            time.sleep(espera_segundos)

    # Si llegamos aqui, se agotaron los intentos: informamos y relanzamos.
    logger.error("No fue posible conectar a la base de datos tras %s intentos.", intentos)
    if ultimo_error is not None:
        raise ultimo_error
