# Prueba de humo del despliegue (Docker Compose)

Esta guia describe la **prueba de humo (smoke test)** del despliegue local de
**Control de Pedidos**. Es una **verificacion UNICA de infraestructura**: comprueba que la
configuracion y el arranque funcionan, no la logica de negocio (esa la cubren las pruebas
unitarias y las pruebas basadas en propiedades del backend). Por eso **no se automatiza con
muchas iteraciones**, de forma coherente con la seccion "Pruebas de humo (smoke)" del
`design.md`.

Cubre los requerimientos **14.1**, **14.3** y **15.1**.

> Nota: la ejecucion real de esta prueba la realiza la persona usuaria en su Windows con
> Docker Desktop y el servicio PostgreSQL del host en ejecucion. Los archivos de este
> repositorio (`smoke_test.ps1` y esta guia) son los artefactos de la prueba.

---

## 1. Prerrequisitos

Antes de nada, asegurate de tener:

- **Docker Desktop instalado y en ejecucion en Windows** (backend WSL 2 recomendado). Solo
  el frontend y el backend corren en contenedores.
- **Servicio PostgreSQL instalado y corriendo en el host de Windows**, con la base de datos
  ya creada. PostgreSQL **no** corre en Docker.
- **Archivo `.env` configurado** en la raiz del proyecto (puedes partir de `.env.example`):
  - `DATABASE_URL=postgresql+psycopg://<usuario>:<password>@host.docker.internal:5432/<basedatos>`
    (usa `host.docker.internal`, no `localhost`, porque dentro del contenedor `localhost`
    apunta al propio contenedor).
  - `VITE_API_URL=http://localhost:8000/api`

---

## 2. Levantar la aplicacion

Desde la **raiz del proyecto**, en PowerShell:

```powershell
docker compose up --build
```

Esto construye las imagenes del frontend y del backend y arranca ambos contenedores. El
backend se conecta a la PostgreSQL del host via `host.docker.internal:5432`.

En **otra** terminal, confirma que ambos servicios estan en estado *running*:

```powershell
docker compose ps
```

Deberias ver dos servicios (`backend` y `frontend`) con estado `running` / `Up`, y los
puertos publicados `8000->8000` y `3000->3000`.

---

## 3. Que verificar (comprobacion unica)

Con la aplicacion levantada, comprueba estos tres puntos:

| # | Comprobacion | URL | Esperado |
|---|--------------|-----|----------|
| 1 | Backend vivo | `http://localhost:8000/api/health` | `200` y cuerpo `{"status":"ok"}` |
| 2 | Backend conectado a la PostgreSQL del host | `http://localhost:8000/api/clientes` | `200` (confirma la conexion via `host.docker.internal:5432`) |
| 3 | Frontend responde | `http://localhost:3000` | `200` (la interfaz React carga) |

Que `GET /api/clientes` devuelva `200` es la senal clave: significa que el backend logro
hablar con la base de datos del host. Si la conexion fallara, ese endpoint no responderia
correctamente.

Puedes abrir las URLs en el navegador o usar PowerShell:

```powershell
Invoke-WebRequest -Uri http://localhost:8000/api/health   -UseBasicParsing | Select-Object StatusCode
Invoke-WebRequest -Uri http://localhost:8000/api/clientes -UseBasicParsing | Select-Object StatusCode
Invoke-WebRequest -Uri http://localhost:3000              -UseBasicParsing | Select-Object StatusCode
```

---

## 4. Script automatico (opcional)

Para no comprobar a mano, ejecuta el script incluido en la raiz. Es **idempotente** y
**no destructivo** (solo hace peticiones HTTP de lectura; no arranca, detiene ni modifica
nada):

```powershell
./smoke_test.ps1
```

El script informa `OK` o `FALLO` por cada comprobacion en espanol y termina con:

- **codigo de salida 0** si las tres comprobaciones pasan;
- **codigo de salida 1** si alguna falla.

Parametros opcionales (por si cambias los puertos):

```powershell
./smoke_test.ps1 -BackendUrl http://localhost:8000 -FrontendUrl http://localhost:3000
```

---

## 5. Detener el entorno

Para detener y liberar recursos:

```powershell
docker compose down
```

Esto **no borra datos**: la base de datos vive en el servicio PostgreSQL del host de
Windows, fuera de Docker.

---

## 6. Si algo falla

- **`docker compose ps` no muestra los servicios `running`:** revisa los logs con
  `docker compose logs backend` o `docker compose logs frontend`.
- **`/api/clientes` no devuelve `200`:** suele indicar un problema de conexion a la base de
  datos. Verifica que el servicio PostgreSQL del host este corriendo, que la base exista y
  que `DATABASE_URL` en `.env` use `host.docker.internal:5432` con credenciales correctas.
- **El frontend no responde en `http://localhost:3000`:** confirma que el contenedor
  `frontend` esta `running` y que el puerto `3000` esta publicado.
- **El backend arranca pero tarda:** espera unos segundos a que el servicio termine de
  iniciar y vuelve a ejecutar la comprobacion.
