# Implementation Plan: Control de Pedidos

## Overview

Este plan convierte el diseño de **Control de Pedidos** en una serie de tareas de codificación incrementales para un agente de desarrollo. El orden sigue el flujo natural del proyecto: primero la base del backend (proyecto, base de datos, modelos, esquemas), luego la capa de servicios pura (con sus pruebas basadas en propiedades), después los routers de la API, a continuación el frontend (cliente HTTP, layout, secciones y estilo visual) y, por último, la contenerización con Docker y la prueba de humo.

Stack fijado por el diseño: **backend** FastAPI + Python (SQLAlchemy, Pydantic, Hypothesis), **frontend** React (Vite + React Testing Library), **base de datos** PostgreSQL como servicio del host de Windows (el backend se conecta vía `host.docker.internal:5432`). El frontend y el backend se orquestan con Docker Compose; PostgreSQL NO corre en Docker.

Cada tarea construye sobre las anteriores y termina integrada; no queda código huérfano. Las sub-tareas marcadas con `*` son de prueba y son opcionales. Las pruebas basadas en propiedades se etiquetan con el formato `# Feature: control-de-pedidos, Property {número}`.

## Tasks

- [x] 1. Preparar la estructura del proyecto backend
  - Crear la carpeta `backend/` con los archivos base: `main.py`, `database.py`, `models.py`, `schemas.py`, `services.py` y la carpeta `routers/` con `__init__.py`.
  - Crear `backend/requirements.txt` con las dependencias: `fastapi`, `uvicorn`, `sqlalchemy`, `psycopg`, `pydantic`, `hypothesis`, `pytest`.
  - Crear la carpeta `backend/tests/` con `__init__.py`, `test_properties.py` y `test_examples.py` vacíos (placeholders).
  - _Requerimientos: 14.2, 15.1_

- [x] 2. Configurar la conexión a la base de datos y el esquema
  - [x] 2.1 Implementar `database.py` (conexión SQLAlchemy)
    - Leer `DATABASE_URL` del entorno y crear el `engine`, `SessionLocal` y `Base` declarativa.
    - Implementar una dependencia `get_db()` para las sesiones y una función que reintente la conexión al inicio (tolerar que PostgreSQL del host tarde en aceptar conexiones).
    - _Requerimientos: 14.1, 14.3_

  - [x] 2.2 Implementar los modelos ORM en `models.py`
    - Definir `Cliente` (id, nombre VARCHAR(100), telefono VARCHAR(20), direccion VARCHAR(200) nullable).
    - Definir `Producto` (id, nombre VARCHAR(100), descripcion VARCHAR(500) nullable, precio NUMERIC(8,2) con CHECK 0..999999.99, disponible BOOLEAN NOT NULL DEFAULT TRUE).
    - Definir `Pedido` (id, cliente_id FK, producto_id FK, cantidad INTEGER CHECK 1..9999, precio_unitario NUMERIC(8,2), total NUMERIC(12,2), fecha DATE DEFAULT CURRENT_DATE, estado VARCHAR(20) CHECK en los 4 valores).
    - Crear las tablas al inicio si no existen (`Base.metadata.create_all`).
    - _Requerimientos: 14.3, 8.2, 8.3, 8.4_

- [x] 3. Definir los esquemas Pydantic en `schemas.py`
  - Crear esquemas de request/response para Cliente (con validación de longitud: nombre 1..100, telefono 1..20, direccion <=200).
  - Crear esquemas para Producto (nombre 1..100, descripcion <=500, precio Decimal 0..999999.99, disponible con default `True`).
  - Crear esquemas para Pedido: request de creación (`cliente_id`, `producto_id`, `cantidad` entero 1..9999), request de cambio de estado (`estado`), y response completo (incluye `cliente_nombre`, `producto_nombre`, `precio_unitario`, `total`, `fecha`, `estado`).
  - Crear el esquema `ResumenReporte` (fecha, cantidad_pedidos, suma_ventas, pedidos).
  - _Requerimientos: 2.1, 2.4, 5.1, 5.5, 8.1, 8.5, 15.2_

- [x] 4. Implementar la capa de servicios pura en `services.py`
  - [x] 4.1 Implementar `calcular_total` y `es_estado_valido`
    - `calcular_total(cantidad, precio_unitario)` devuelve `cantidad * precio_unitario` usando `Decimal` (sin punto flotante).
    - `es_estado_valido(estado)` devuelve `True` solo para {Pendiente, Preparando, Entregado, Cancelado}.
    - _Requerimientos: 9.1, 9.2, 10.3_

  - [x]* 4.2 Prueba de propiedad para `calcular_total`
    - `# Feature: control-de-pedidos, Property 1: El total es siempre cantidad por precio unitario`
    - **Property 1** — Valida: Requerimientos 9.1, 9.2 (mínimo 100 iteraciones con Hypothesis; cantidades 1..9999 y precios 0..999999.99 con aritmética Decimal).

  - [x]* 4.3 Prueba de propiedad para `es_estado_valido` (estado válido round trip)
    - `# Feature: control-de-pedidos, Property 4: Asignar un estado válido se persiste y se refleja (round trip)`
    - **Property 4** — Valida: Requerimientos 10.1 (los 4 estados válidos se aceptan).

  - [x]* 4.4 Prueba de propiedad para `es_estado_valido` (estado inválido rechazado)
    - `# Feature: control-de-pedidos, Property 5: Un estado inválido es rechazado y se conserva el anterior`
    - **Property 5** — Valida: Requerimientos 10.3 (cadenas fuera del conjunto, incluida la vacía, se rechazan).

  - [x] 4.5 Implementar `producto_seleccionable` y validaciones de campos
    - `producto_seleccionable(producto)` devuelve `True` solo si `disponible = True`.
    - Funciones puras de validación: campo obligatorio no vacío ni solo espacios; longitud máxima por campo; rango de precio; rango y tipo de cantidad. Devuelven el mensaje de error en español correspondiente.
    - _Requerimientos: 7.3, 8.8, 2.2, 2.3, 4.2, 5.2, 2.4, 5.3, 7.2, 8.5_

  - [x]* 4.6 Prueba de propiedad para productos seleccionables
    - `# Feature: control-de-pedidos, Property 6: Los productos no disponibles no se pueden pedir`
    - **Property 6** — Valida: Requerimientos 7.3, 8.8.

  - [x]* 4.7 Prueba de propiedad para cantidad fuera de rango
    - `# Feature: control-de-pedidos, Property 7: La cantidad fuera del rango 1..9999 es rechazada`
    - **Property 7** — Valida: Requerimientos 8.5.

  - [x]* 4.8 Prueba de propiedad para campos obligatorios vacíos o con espacios
    - `# Feature: control-de-pedidos, Property 8: Los campos obligatorios vacíos o solo con espacios son rechazados`
    - **Property 8** — Valida: Requerimientos 2.2, 2.3, 4.2, 5.2.

  - [x]* 4.9 Prueba de propiedad para longitud máxima excedida
    - `# Feature: control-de-pedidos, Property 9: Los campos que exceden su longitud máxima son rechazados`
    - **Property 9** — Valida: Requerimientos 2.4, 5.2.

  - [x]* 4.10 Prueba de propiedad para precio fuera de rango
    - `# Feature: control-de-pedidos, Property 10: El precio fuera del rango permitido es rechazado`
    - **Property 10** — Valida: Requerimientos 5.3, 7.2.

  - [x] 4.11 Implementar `resumir_reporte`
    - `resumir_reporte(pedidos)` devuelve el conteo total (incluye cancelados) y la suma de `total` excluyendo los pedidos con estado `Cancelado` (0 si todos cancelados o lista vacía).
    - _Requerimientos: 12.4, 12.5_

  - [x]* 4.12 Prueba de propiedad para el filtrado por fecha del reporte
    - `# Feature: control-de-pedidos, Property 12: El reporte diario solo incluye pedidos de la fecha seleccionada`
    - **Property 12** — Valida: Requerimientos 12.3.

  - [x]* 4.13 Prueba de propiedad para conteo y suma del reporte
    - `# Feature: control-de-pedidos, Property 13: El reporte cuenta todos los pedidos y suma solo los no cancelados`
    - **Property 13** — Valida: Requerimientos 12.4, 12.5.

- [x] 5. Checkpoint - Verificar la capa de servicios
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implementar el router de clientes
  - [x] 6.1 Crear `routers/clientes.py` con GET, POST, GET/{id}, PUT/{id}
    - Usar la capa de servicios para validaciones de negocio; devolver 400 con `detail` en español, 404 si no existe, 422 por validación Pydantic.
    - _Requerimientos: 2.1, 2.2, 2.3, 2.4, 2.6, 3.1, 4.1, 4.2, 4.3, 15.3, 16.1_

  - [x]* 6.2 Pruebas por ejemplo del CRUD de clientes
    - Crear, listar, editar y verificar persistencia; caso de nombre/teléfono vacío y longitud excedida; lista vacía.
    - _Requerimientos: 2.1, 2.6, 3.1, 3.2, 4.1, 4.3_

- [x] 7. Implementar el router de productos
  - [x] 7.1 Crear `routers/productos.py` con GET (con `?solo_disponibles=true`), POST, GET/{id}, PUT/{id}
    - Aplicar default `disponible = true`; validar rango de precio y nombre; filtrar por disponibles cuando se solicita.
    - _Requerimientos: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 6.1, 7.1, 7.2, 7.3, 15.3, 16.1_

  - [x]* 7.2 Prueba de propiedad: disponible verdadero por defecto
    - `# Feature: control-de-pedidos, Property 11: Disponible es verdadero por defecto`
    - **Property 11** — Valida: Requerimientos 5.5.

  - [x]* 7.3 Pruebas por ejemplo del CRUD de productos
    - Crear, listar, editar; precio no numérico (5.4); filtro `solo_disponibles`; lista vacía.
    - _Requerimientos: 5.1, 5.4, 5.6, 6.1, 6.2, 7.1, 7.3_

- [x] 8. Implementar el router de pedidos
  - [x] 8.1 Crear `routers/pedidos.py` con GET, POST y PATCH/{id}/estado
    - En POST: validar cliente/producto existentes y producto disponible; copiar el precio vigente del producto a `precio_unitario`; calcular `total` con `calcular_total`; asignar `fecha` de hoy y estado `Pendiente`.
    - En PATCH estado: validar con `es_estado_valido`; conservar el estado anterior si es inválido (400).
    - En GET: incluir `cliente_nombre` y `producto_nombre`.
    - _Requerimientos: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 9.1, 10.1, 10.2, 10.3, 11.1, 15.3, 16.1_

  - [x]* 8.2 Prueba de propiedad: precio unitario vigente e inmutable
    - `# Feature: control-de-pedidos, Property 2: El precio unitario del pedido es el vigente y no cambia después`
    - **Property 2** — Valida: Requerimientos 8.4.

  - [x]* 8.3 Prueba de propiedad: pedido nace Pendiente con fecha de hoy
    - `# Feature: control-de-pedidos, Property 3: Todo pedido nuevo nace Pendiente y con la fecha de hoy`
    - **Property 3** — Valida: Requerimientos 8.2, 8.3.

  - [x]* 8.4 Pruebas por ejemplo de pedidos
    - Crear pedido válido y verificar total/estado/fecha (8.1, 8.9); pedido sin cliente (8.6); sin producto (8.7); producto no disponible (8.8); cambio de estado válido e inválido (10.1, 10.3); lista vacía (11.2).
    - _Requerimientos: 8.1, 8.6, 8.7, 8.8, 8.9, 10.1, 10.3, 11.2_

- [x] 9. Implementar el router de reporte diario
  - [x] 9.1 Crear `routers/reporte.py` con GET `/api/reporte-diario`
    - Aceptar `?fecha=YYYY-MM-DD`; usar el día actual si se omite; filtrar pedidos por fecha y usar `resumir_reporte` para conteo y suma.
    - _Requerimientos: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x]* 9.2 Pruebas por ejemplo del reporte diario
    - Día por defecto (hoy); cambio de día; conteo incluye cancelados; suma excluye cancelados y es 0 si todos cancelados; mensaje/lista vacía si no hay pedidos.
    - _Requerimientos: 12.1, 12.2, 12.4, 12.5, 12.6_

- [x] 10. Ensamblar la aplicación FastAPI
  - [x] 10.1 Implementar `main.py`
    - Instanciar FastAPI, configurar CORS para `http://localhost:3000`, incluir los routers de clientes, productos, pedidos y reporte bajo el prefijo `/api`, y crear el esquema al inicio.
    - _Requerimientos: 15.1, 15.2, 15.3, 16.1_

- [x] 11. Checkpoint - Verificar el backend completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Preparar la estructura del proyecto frontend
  - Crear el proyecto React con Vite en `frontend/` y la estructura `src/` con `App.jsx`, `api.js`, `main.jsx` y la carpeta `src/secciones/`.
  - Definir en `src/index.css` (o `styles.css`) las variables CSS de la guía de estilo (`:root`): tokens de color, tipografía, radios, sombras y espaciado.
  - _Requerimientos: 14.2, 15.1_

- [x] 13. Implementar el cliente HTTP centralizado
  - [x] 13.1 Implementar `src/api.js`
    - Leer `VITE_API_URL` del entorno; exponer funciones para clientes, productos, pedidos y reporte; interpretar `detail` en los errores del backend; producir el mensaje "No fue posible conectar con el servidor." ante fallos de red.
    - _Requerimientos: 15.1, 15.2, 16.1, 16.2_

  - [x]* 13.2 Pruebas del cliente HTTP
    - Verificar extracción de `detail` y el mensaje de error de conexión.
    - _Requerimientos: 16.1, 16.2_

- [x] 14. Implementar el layout y el menú lateral
  - [x] 14.1 Implementar `App.jsx` y `MenuLateral`
    - `App` mantiene en estado la sección activa, muestra `Inicio` por defecto y renderiza el menú lateral y la sección seleccionada.
    - `MenuLateral` muestra Inicio, Clientes, Productos, Pedidos y Reporte diario, resalta la sección activa (fondo primario + acento a la izquierda) y notifica el cambio; aplicar los estilos del sidebar (fondo oscuro, ancho fijo).
    - _Requerimientos: 1.1, 1.2, 1.3, 13.1_

  - [x]* 14.2 Pruebas del menú lateral y sección activa
    - Render de las opciones, cambio de sección y resaltado del ítem activo.
    - _Requerimientos: 1.1, 1.2, 1.3, 13.1_

- [x] 15. Implementar la sección Inicio
  - Implementar `secciones/Inicio.jsx` con accesos directos a Clientes, Productos, Pedidos y Reporte diario, dentro de tarjetas blancas.
  - _Requerimientos: 13.1, 13.2_

- [x] 16. Implementar la sección Clientes
  - [x] 16.1 Implementar `secciones/Clientes.jsx`
    - Listar clientes (tabla en tarjeta), formulario de alta/edición (etiqueta encima del input, foco de acento, botón primario), mensaje cuando no hay clientes, y mostrar errores de validación conservando los datos ingresados.
    - _Requerimientos: 2.1, 2.5, 2.6, 3.1, 3.2, 4.1, 4.3, 16.1_

  - [x]* 16.2 Pruebas de la sección Clientes
    - Conservación de datos del formulario ante error de validación (2.5, 16.1).
    - _Requerimientos: 2.5, 16.1_

- [x] 17. Implementar la sección Productos
  - Implementar `secciones/Productos.jsx`: listar productos, formulario de alta/edición (incluye Disponible), mensaje cuando no hay productos, y mostrar errores conservando lo ingresado.
  - _Requerimientos: 5.1, 5.2, 5.6, 6.1, 6.2, 7.1, 16.1_

- [x] 18. Implementar la sección Pedidos
  - [x] 18.1 Implementar `secciones/Pedidos.jsx`
    - Formulario de creación con selección de cliente, selección de producto (solo disponibles), y cantidad; previsualización del Total que se recalcula al cambiar la cantidad; lista de pedidos; control para cambiar el estado; mostrar errores conservando lo ingresado.
    - _Requerimientos: 8.1, 8.5, 8.6, 8.7, 8.8, 9.2, 9.3, 10.1, 10.2, 11.1, 11.2, 16.1_

  - [x]* 18.2 Pruebas de la previsualización del total
    - Verificar que el Total mostrado se recalcula al cambiar la cantidad.
    - _Requerimientos: 9.2, 9.3_

- [x] 19. Implementar la sección Reporte diario
  - Implementar `secciones/ReporteDiario.jsx`: selector de día (por defecto hoy), tabla de pedidos del día, conteo total y suma de ventas (excluye cancelados), y mensaje cuando no hay pedidos.
  - _Requerimientos: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 20. Aplicar la guía de estilo visual a formularios y tablas
  - Estilizar formularios (tarjetas blancas, etiqueta encima, anillo de foco de acento, botón primario azul/cian, mensajes de error en rojo) y tablas (encabezado gris, filas con borde sutil, acciones en color de acento) usando las variables CSS definidas.
  - _Requerimientos: 1.3, 2.5, 13.2, 16.1_

- [x] 21. Checkpoint - Verificar el frontend completo
  - Ensure all tests pass, ask the user if questions arise.

- [x] 22. Contenerización con Docker
  - [x] 22.1 Crear el `Dockerfile` y `.dockerignore` del backend
    - Imagen base `python:3.12-slim`, instalar `requirements.txt`, exponer el puerto 8000 y ejecutar Uvicorn; `.dockerignore` excluye venv, `__pycache__`, tests.
    - _Requerimientos: 14.1, 14.2_

  - [x] 22.2 Crear el `Dockerfile` y `.dockerignore` del frontend
    - Imagen base `node:20`, instalar dependencias, exponer el puerto 3000 y servir la SPA (servidor de Vite); `.dockerignore` excluye `node_modules`, `build`.
    - _Requerimientos: 14.1, 14.2_

  - [x] 22.3 Crear `docker-compose.yml` y `.env` en la raíz
    - Definir solo los servicios `frontend` (3000:3000) y `backend` (8000:8000); el backend lee `DATABASE_URL` (apuntando a `host.docker.internal:5432`) y el frontend lee `VITE_API_URL`; sin servicio `db` ni volúmenes.
    - Crear `.env` de ejemplo con `DATABASE_URL` (host.docker.internal) y `VITE_API_URL=http://localhost:8000/api`.
    - _Requerimientos: 14.1, 14.2, 14.3, 15.1_

- [x] 23. Prueba de humo del despliegue
  - [x]* 23.1 Script o guía de prueba de humo de `docker compose up`
    - Verificar (comprobación única) que ambos contenedores arrancan, que `GET /api/clientes` responde 200 (confirmando la conexión a PostgreSQL del host) y que el frontend responde en `http://localhost:3000`.
    - _Requerimientos: 14.1, 14.3, 15.1_

- [x] 24. Checkpoint final - Verificar todo el sistema
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Las tareas marcadas con `*` son de prueba y opcionales; pueden omitirse para un MVP más rápido, pero se recomienda ejecutarlas.
- Cada tarea referencia requerimientos específicos para trazabilidad.
- Las pruebas basadas en propiedades (Hypothesis, mínimo 100 iteraciones) cubren las 13 propiedades de correctitud de la capa de servicios pura y llevan la etiqueta `# Feature: control-de-pedidos, Property {número}`.
- Las pruebas por ejemplo/integración cubren el CRUD y los endpoints; las pruebas del frontend usan React Testing Library.
- Los checkpoints permiten validación incremental antes de avanzar.
- La base de datos PostgreSQL es un servicio del host de Windows; solo el frontend y el backend se contenerizan.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "12"] },
    { "id": 1, "tasks": ["2.1", "2.2", "13.1"] },
    { "id": 2, "tasks": ["3", "13.2", "14.1"] },
    { "id": 3, "tasks": ["4.1", "4.5", "4.11", "14.2", "15"] },
    { "id": 4, "tasks": ["4.2", "4.3", "4.4", "4.6", "4.7", "4.8", "4.9", "4.10", "4.12", "4.13", "16.1", "17"] },
    { "id": 5, "tasks": ["6.1", "7.1", "8.1", "9.1", "16.2", "18.1"] },
    { "id": 6, "tasks": ["6.2", "7.2", "7.3", "8.2", "8.3", "8.4", "9.2", "10.1", "18.2", "19", "20"] },
    { "id": 7, "tasks": ["22.1", "22.2", "22.3"] },
    { "id": 8, "tasks": ["23.1"] }
  ]
}
```
