# Dockerfile del backend (FastAPI + Uvicorn)
#
# Este Dockerfile construye la imagen del contenedor del backend. Es
# intencionalmente simple y educativo. La base de datos PostgreSQL NO vive
# aqui: es un servicio del host de Windows al que el backend se conecta via
# host.docker.internal (eso lo configura .env / docker-compose, no este
# Dockerfile). Por eso aqui no se definen variables de base de datos.

# 1) Imagen base: Python 3.12 en su variante "slim" (mas ligera).
#    Elegida en design.md para el servicio backend.
FROM python:3.12-slim

# 2) Directorio de trabajo dentro del contenedor. Todos los comandos y rutas
#    relativas siguientes se resuelven a partir de /app.
WORKDIR /app

# 3) Copiar PRIMERO solo requirements.txt e instalar dependencias.
#    Se hace antes de copiar el resto del codigo para aprovechar la cache de
#    capas de Docker: si el codigo cambia pero las dependencias no, esta capa
#    de instalacion se reutiliza y el build es mucho mas rapido.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4) Copiar el resto del codigo del backend (main.py, database.py, models.py,
#    schemas.py, services.py, routers/, etc.) al directorio de trabajo.
COPY . .

# 5) Exponer el puerto 8000, donde Uvicorn servira la API.
#    (EXPOSE es documental; la publicacion real del puerto la hace
#    docker-compose con "8000:8000".)
EXPOSE 8000

# 6) Comando de arranque: levantar la app FastAPI con Uvicorn.
#    - "main:app" -> objeto "app" definido en main.py (su lifespan espera la
#      conexion a la BD y crea el esquema al iniciar).
#    - "--host 0.0.0.0" -> escuchar en todas las interfaces para que el puerto
#      publicado sea accesible desde el host.
#    - "--port 8000" -> puerto interno del contenedor.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
