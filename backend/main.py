# main.py
# Punto de entrada de la aplicacion backend (FastAPI).
#
# Aqui se ensambla la aplicacion completa (Tarea 10):
#   - Se instancia FastAPI.
#   - Se configura CORS para permitir el origen del frontend (Req. 15).
#   - Se incluyen los cuatro routers (clientes, productos, pedidos, reporte),
#     cada uno con su propio prefijo /api, por lo que NO se agrega prefijo extra.
#   - Al arrancar se espera la conexion a la base de datos y se crea el esquema.

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Infraestructura de base de datos (Tarea 2): reintento de conexion y creacion
# del esquema. crear_tablas() vive en models.py y usa Base.metadata.create_all.
from database import esperar_conexion
from models import crear_tablas

# Los cuatro routers ya definen su propio prefijo /api (por ejemplo
# /api/clientes, /api/productos, /api/pedidos, /api/reporte-diario), asi que se
# incluyen tal cual, sin anadir un prefijo adicional que duplicaria las rutas.
from routers import clientes, pedidos, productos, reporte


# --- Ciclo de vida de la aplicacion (arranque / apagado) -------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Prepara la base de datos al iniciar la aplicacion.

    Se usa el estilo moderno de "lifespan" (context manager asincrono) en lugar
    del ya deprecado @app.on_event("startup").

    Al arrancar:
      1. esperar_conexion() reintenta la conexion, porque la PostgreSQL del host
         puede tardar unos segundos en aceptar conexiones.
      2. crear_tablas() crea el esquema si aun no existe.

    No se capturan los errores a proposito: si la base no esta disponible tras
    los reintentos, la excepcion se propaga y el arranque falla de forma clara.
    Esto es aceptable para un proyecto educativo: es preferible fallar visible y
    temprano a arrancar con una base inaccesible.
    """
    esperar_conexion()
    crear_tablas()
    # El "yield" separa el arranque (arriba) del apagado (abajo). No hay tareas
    # de limpieza especiales al detener la aplicacion.
    yield


# --- Instancia de la aplicacion --------------------------------------------
app = FastAPI(
    title="Control de Pedidos",
    description="API REST para gestionar clientes, productos, pedidos y el reporte diario.",
    version="1.0.0",
    lifespan=lifespan,
)

# --- Configuracion de CORS (Req. 15) ---------------------------------------
# El frontend (React) corre en http://localhost:3000 y consume esta API desde
# el navegador. Sin CORS, el navegador bloquearia esas peticiones de origen
# cruzado. Se permite explicitamente ese origen; se aceptan todos los metodos y
# cabeceras para simplificar el desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# --- Inclusion de los routers ----------------------------------------------
# Cada router ya trae su prefijo /api/..., por eso se incluyen sin prefijo extra.
app.include_router(clientes.router)
app.include_router(productos.router)
app.include_router(pedidos.router)
app.include_router(reporte.router)


# --- Endpoint de health-check ----------------------------------------------
@app.get("/api/health", tags=["health"])
def health():
    """Comprobacion simple de vida del servicio (util para smoke tests)."""
    return {"status": "ok"}
