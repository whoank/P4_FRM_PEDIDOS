# Requirements Document

## Introduction

**Control de Pedidos** es una aplicación web sencilla y educativa pensada para un pequeño negocio de comida. Hoy el negocio recibe pedidos por WhatsApp y los registra a mano, lo que provoca pedidos olvidados, errores en los totales y dificultad para conocer las ventas del día.

La aplicación permite administrar clientes, productos y pedidos desde una sola interfaz. Ofrece un menú lateral para navegar entre Inicio, Clientes, Productos, Pedidos y Reporte diario. El sistema calcula automáticamente los totales de cada pedido, permite cambiar el estado de un pedido a lo largo de su ciclo de vida y muestra las ventas y los pedidos del día.

El proyecto está diseñado para ser pequeño, educativo y fácil de implementar. Usará React en el frontend, FastAPI con Python en el backend y PostgreSQL como base de datos, y se ejecutará localmente en Windows.

## Definición del Problema

- El negocio registra los pedidos manualmente a partir de mensajes de WhatsApp.
- El registro manual causa pedidos olvidados y errores al calcular los totales.
- No existe una forma rápida de conocer cuántos pedidos y cuántas ventas se generaron en el día.
- Se necesita un sistema centralizado para administrar clientes, productos y pedidos, y para consultar el resumen diario.

## Glossary

- **Sistema**: La aplicación web Control de Pedidos en su conjunto (frontend, backend y base de datos).
- **Cliente**: Persona que realiza pedidos, con los datos Nombre, Teléfono y Dirección.
- **Producto**: Artículo de comida disponible para pedir, con los datos Nombre, Descripción, Precio y Disponible.
- **Pedido**: Solicitud de un Cliente que incluye un Producto, Cantidad, Precio unitario, Total, Fecha y Estado.
- **Estado_Pedido**: Valor del ciclo de vida de un Pedido; uno de: Pendiente, Preparando, Entregado, Cancelado.
- **Total**: Resultado de multiplicar la Cantidad por el Precio unitario de un Pedido.
- **Menu_Lateral**: Componente de navegación con las opciones Inicio, Clientes, Productos, Pedidos y Reporte diario.
- **Reporte_Diario**: Vista que muestra los pedidos y las ventas de un día determinado.
- **Usuario**: Persona del negocio que opera la aplicación (administrador o encargado).
- **Precio_Unitario**: Precio de una unidad de un Producto en el momento de crear un Pedido.
- **Disponible**: Indicador booleano que señala si un Producto puede incluirse en nuevos Pedidos.

## Requirements

### Requerimiento 1: Navegación mediante menú lateral

**Historia de Usuario:** Como Usuario del negocio, quiero un menú lateral, para navegar rápidamente entre las secciones de la aplicación.

#### Criterios de Aceptación

1. THE Sistema SHALL mostrar un Menu_Lateral con las opciones Inicio, Clientes, Productos, Pedidos y Reporte diario.
2. WHEN el Usuario selecciona una opción del Menu_Lateral, THE Sistema SHALL mostrar la sección correspondiente a esa opción.
3. THE Sistema SHALL indicar visualmente en el Menu_Lateral la sección que está activa.

### Requerimiento 2: Registro de clientes

**Historia de Usuario:** Como Usuario del negocio, quiero registrar clientes, para asociar los pedidos a la persona que los realiza.

#### Criterios de Aceptación

1. WHEN el Usuario envía el formulario de Cliente con un Nombre de 1 a 100 caracteres, un Teléfono de 1 a 20 caracteres y, opcionalmente, una Dirección de hasta 200 caracteres, THE Sistema SHALL crear un nuevo Cliente con esos datos.
2. IF el Usuario envía el formulario de Cliente con el campo Nombre vacío o compuesto únicamente por espacios en blanco, THEN THE Sistema SHALL rechazar el registro y mostrar un mensaje que indique que el Nombre es obligatorio.
3. IF el Usuario envía el formulario de Cliente con el campo Teléfono vacío o compuesto únicamente por espacios en blanco, THEN THE Sistema SHALL rechazar el registro y mostrar un mensaje que indique que el Teléfono es obligatorio.
4. IF el Usuario envía el formulario de Cliente con un Nombre de más de 100 caracteres, un Teléfono de más de 20 caracteres o una Dirección de más de 200 caracteres, THEN THE Sistema SHALL rechazar el registro y mostrar un mensaje que indique el campo excedido y su longitud máxima permitida.
5. IF el Sistema rechaza el registro de un Cliente por datos inválidos, THEN THE Sistema SHALL conservar los datos ingresados en el formulario sin crear un nuevo Cliente.
6. WHEN el registro de un Cliente se completa correctamente, THE Sistema SHALL mostrar el nuevo Cliente en la lista de Clientes.

### Requerimiento 3: Listado de clientes

**Historia de Usuario:** Como Usuario del negocio, quiero ver la lista de clientes, para consultar sus datos de contacto.

#### Criterios de Aceptación

1. WHEN el Usuario abre la sección Clientes, THE Sistema SHALL mostrar la lista de Clientes registrados con Nombre, Teléfono y Dirección.
2. WHILE no exista ningún Cliente registrado, THE Sistema SHALL mostrar un mensaje que indique que no hay Clientes registrados.

### Requerimiento 4: Edición de clientes

**Historia de Usuario:** Como Usuario del negocio, quiero editar los datos de un cliente, para mantener la información actualizada.

#### Criterios de Aceptación

1. WHEN el Usuario guarda cambios en un Cliente existente con Nombre y Teléfono válidos, THE Sistema SHALL actualizar los datos de ese Cliente.
2. IF el Usuario guarda cambios en un Cliente con el campo Nombre vacío, THEN THE Sistema SHALL rechazar la actualización y mostrar un mensaje que indique que el Nombre es obligatorio.
3. WHEN la actualización de un Cliente se completa correctamente, THE Sistema SHALL mostrar los datos actualizados en la lista de Clientes.

### Requerimiento 5: Registro de productos

**Historia de Usuario:** Como Usuario del negocio, quiero registrar productos, para ofrecerlos en los pedidos.

#### Criterios de Aceptación

1. WHEN el Usuario envía el formulario de Producto con Nombre de entre 1 y 100 caracteres, Descripción de hasta 500 caracteres, Precio entre 0.00 y 999999.99 con hasta 2 decimales, y Disponible, THE Sistema SHALL crear un nuevo Producto con esos datos.
2. IF el Usuario envía el formulario de Producto con el campo Nombre vacío o con más de 100 caracteres, THEN THE Sistema SHALL rechazar el registro, conservar los datos ingresados en el formulario y mostrar un mensaje que indique que el Nombre es obligatorio y no debe superar 100 caracteres.
3. IF el Usuario envía el formulario de Producto con un Precio menor que 0 o mayor que 999999.99, THEN THE Sistema SHALL rechazar el registro, conservar los datos ingresados en el formulario y mostrar un mensaje que indique que el Precio debe ser igual o mayor que 0 y no mayor que 999999.99.
4. IF el Usuario envía el formulario de Producto con un Precio que no es un valor numérico, THEN THE Sistema SHALL rechazar el registro, conservar los datos ingresados en el formulario y mostrar un mensaje que indique que el Precio debe ser un valor numérico.
5. WHERE el Usuario no especifica un valor para Disponible al enviar el formulario de Producto, THE Sistema SHALL asignar al Producto el valor Disponible verdadero de forma predeterminada.
6. WHEN el registro de un Producto se completa correctamente, THE Sistema SHALL mostrar el nuevo Producto en la lista de Productos.

### Requerimiento 6: Listado de productos

**Historia de Usuario:** Como Usuario del negocio, quiero ver la lista de productos, para consultar sus precios y disponibilidad.

#### Criterios de Aceptación

1. WHEN el Usuario abre la sección Productos, THE Sistema SHALL mostrar la lista de Productos con Nombre, Descripción, Precio y Disponible.
2. WHILE no exista ningún Producto registrado, THE Sistema SHALL mostrar un mensaje que indique que no hay Productos registrados.

### Requerimiento 7: Edición de productos

**Historia de Usuario:** Como Usuario del negocio, quiero editar los datos de un producto, para mantener actualizados sus precios y disponibilidad.

#### Criterios de Aceptación

1. WHEN el Usuario guarda cambios en un Producto existente con Nombre válido y Precio igual o mayor que 0, THE Sistema SHALL actualizar los datos de ese Producto.
2. IF el Usuario guarda cambios en un Producto con un Precio menor que 0, THEN THE Sistema SHALL rechazar la actualización y mostrar un mensaje que indique que el Precio debe ser igual o mayor que 0.
3. WHEN el Usuario marca un Producto como no Disponible, THE Sistema SHALL excluir ese Producto de las opciones seleccionables al crear nuevos Pedidos.

### Requerimiento 8: Creación de pedidos

**Historia de Usuario:** Como Usuario del negocio, quiero crear pedidos, para registrar las solicitudes de los clientes de forma ordenada.

#### Criterios de Aceptación

1. WHEN el Usuario envía el formulario de Pedido con un Cliente seleccionado, un Producto seleccionado y una Cantidad entera comprendida entre 1 y 9999, THE Sistema SHALL crear un nuevo Pedido con esos datos.
2. WHEN el Sistema crea un Pedido, THE Sistema SHALL asignar la Fecha actual al Pedido.
3. WHEN el Sistema crea un Pedido, THE Sistema SHALL asignar el Estado_Pedido inicial con el valor Pendiente.
4. WHEN el Sistema crea un Pedido, THE Sistema SHALL registrar como Precio_Unitario del Pedido el valor del Precio del Producto seleccionado vigente en el momento de la creación.
5. IF el Usuario envía el formulario de Pedido con una Cantidad que no sea un número entero comprendido entre 1 y 9999, THEN THE Sistema SHALL rechazar la creación, conservar los datos ingresados en el formulario y mostrar un mensaje que indique que la Cantidad debe ser un número entero entre 1 y 9999.
6. IF el Usuario envía el formulario de Pedido sin seleccionar un Cliente, THEN THE Sistema SHALL rechazar la creación, conservar los datos ingresados en el formulario y mostrar un mensaje que indique que el Cliente es obligatorio.
7. IF el Usuario envía el formulario de Pedido sin seleccionar un Producto, THEN THE Sistema SHALL rechazar la creación, conservar los datos ingresados en el formulario y mostrar un mensaje que indique que el Producto es obligatorio.
8. IF el Usuario envía el formulario de Pedido con un Producto cuyo indicador Disponible es falso, THEN THE Sistema SHALL rechazar la creación, conservar los datos ingresados en el formulario y mostrar un mensaje que indique que el Producto no está disponible.
9. WHEN la creación de un Pedido se completa correctamente, THE Sistema SHALL mostrar el nuevo Pedido en la lista de Pedidos con Cliente, Producto, Cantidad, Precio_Unitario, Total, Fecha y Estado_Pedido.

### Requerimiento 9: Cálculo automático del total

**Historia de Usuario:** Como Usuario del negocio, quiero que el total del pedido se calcule automáticamente, para evitar errores de cálculo manual.

#### Criterios de Aceptación

1. WHEN el Sistema crea un Pedido, THE Sistema SHALL calcular el Total como el producto de la Cantidad por el Precio_Unitario.
2. WHEN el Usuario modifica la Cantidad de un Pedido durante su creación, THE Sistema SHALL recalcular el Total con la nueva Cantidad.
3. THE Sistema SHALL mostrar el Total calculado en el formulario del Pedido antes de guardarlo.

### Requerimiento 10: Cambio de estado de un pedido

**Historia de Usuario:** Como Usuario del negocio, quiero cambiar el estado de un pedido, para reflejar su avance desde que se recibe hasta que se entrega.

#### Criterios de Aceptación

1. WHEN el Usuario cambia el Estado_Pedido de un Pedido a uno de los valores Pendiente, Preparando, Entregado o Cancelado, THE Sistema SHALL guardar el nuevo Estado_Pedido y reflejar el Estado_Pedido actualizado del Pedido en la lista de Pedidos.
2. THE Sistema SHALL mostrar el Estado_Pedido actual de cada Pedido en la lista de Pedidos.
3. IF el Usuario intenta asignar a un Pedido un Estado_Pedido vacío o distinto de Pendiente, Preparando, Entregado o Cancelado, THEN THE Sistema SHALL rechazar el cambio, conservar el Estado_Pedido anterior y mostrar un mensaje que indique que el Estado_Pedido debe ser uno de los valores Pendiente, Preparando, Entregado o Cancelado.

### Requerimiento 11: Listado de pedidos

**Historia de Usuario:** Como Usuario del negocio, quiero ver la lista de pedidos, para consultar el detalle de cada solicitud.

#### Criterios de Aceptación

1. WHEN el Usuario abre la sección Pedidos, THE Sistema SHALL mostrar la lista de Pedidos con Cliente, Producto, Cantidad, Precio_Unitario, Total, Fecha y Estado_Pedido.
2. WHILE no exista ningún Pedido registrado, THE Sistema SHALL mostrar un mensaje que indique que no hay Pedidos registrados.

### Requerimiento 12: Reporte diario de ventas y pedidos

**Historia de Usuario:** Como Usuario del negocio, quiero ver las ventas y los pedidos del día, para conocer el desempeño diario del negocio.

#### Criterios de Aceptación

1. WHEN el Usuario abre la sección Reporte diario sin haber elegido un día, THE Sistema SHALL usar el día actual como día seleccionado de forma predeterminada.
2. WHEN el Usuario cambia el día seleccionado en la sección Reporte diario, THE Sistema SHALL actualizar la información mostrada para reflejar el nuevo día seleccionado.
3. THE Sistema SHALL mostrar los Pedidos cuya Fecha corresponde al día seleccionado.
4. THE Sistema SHALL mostrar la cantidad total de Pedidos del día seleccionado.
5. THE Sistema SHALL mostrar la suma de los Total de los Pedidos del día seleccionado que no tengan el Estado_Pedido Cancelado, y SHALL mostrar el valor 0 cuando todos los Pedidos del día estén Cancelados.
6. WHILE no exista ningún Pedido en el día seleccionado, THE Sistema SHALL mostrar un mensaje que indique que no hay Pedidos para ese día.

### Requerimiento 13: Pantalla de inicio

**Historia de Usuario:** Como Usuario del negocio, quiero una pantalla de inicio, para tener una vista general al abrir la aplicación.

#### Criterios de Aceptación

1. WHEN el Usuario abre la aplicación, THE Sistema SHALL mostrar la sección Inicio de forma predeterminada.
2. THE Sistema SHALL mostrar en la sección Inicio accesos a las secciones Clientes, Productos, Pedidos y Reporte diario.

## Requerimientos No Funcionales

### Requerimiento 14: Facilidad de implementación local

**Historia de Usuario:** Como estudiante que implementa el proyecto, quiero que la aplicación se ejecute localmente en Windows, para poder desarrollarla y probarla en mi equipo.

#### Criterios de Aceptación

1. THE Sistema SHALL ejecutarse en un entorno local sobre Windows.
2. THE Sistema SHALL usar React en el frontend, FastAPI con Python en el backend y PostgreSQL como base de datos.
3. THE Sistema SHALL persistir Clientes, Productos y Pedidos en la base de datos PostgreSQL.

### Requerimiento 15: Comunicación entre frontend y backend

**Historia de Usuario:** Como estudiante que implementa el proyecto, quiero una comunicación clara entre el frontend y el backend, para entender el flujo de datos.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer una interfaz de programación (API) en el backend para las operaciones de Clientes, Productos y Pedidos.
2. WHEN el frontend solicita datos al backend, THE Sistema SHALL responder en formato JSON.
3. IF el backend recibe una solicitud con datos inválidos, THEN THE Sistema SHALL responder con un código de error y un mensaje descriptivo.

### Requerimiento 16: Manejo de errores

**Historia de Usuario:** Como Usuario del negocio, quiero mensajes claros cuando algo falla, para saber qué corregir.

#### Criterios de Aceptación

1. IF ocurre un error al guardar un Cliente, un Producto o un Pedido, THEN THE Sistema SHALL mostrar un mensaje de error descriptivo y conservar los datos ingresados en el formulario.
2. IF el frontend no puede comunicarse con el backend, THEN THE Sistema SHALL mostrar un mensaje que indique que no fue posible conectar con el servidor.

## Casos de Uso Principales

1. **Registrar un cliente**: El Usuario abre la sección Clientes, completa Nombre, Teléfono y Dirección, y guarda. El Sistema crea el Cliente y lo muestra en la lista.
2. **Registrar un producto**: El Usuario abre la sección Productos, completa Nombre, Descripción, Precio y Disponible, y guarda. El Sistema crea el Producto y lo muestra en la lista.
3. **Crear un pedido**: El Usuario abre la sección Pedidos, selecciona un Cliente y un Producto, indica la Cantidad y el Sistema calcula el Total automáticamente. Al guardar, el Pedido queda con Estado Pendiente y la Fecha actual.
4. **Actualizar el estado de un pedido**: El Usuario abre la sección Pedidos, selecciona un Pedido y cambia su Estado_Pedido (por ejemplo, de Pendiente a Preparando y luego a Entregado).
5. **Consultar el reporte diario**: El Usuario abre la sección Reporte diario y consulta los Pedidos del día, la cantidad total de Pedidos y la suma de ventas del día.
6. **Editar un cliente o producto**: El Usuario abre la sección correspondiente, selecciona un registro, modifica sus datos y guarda los cambios.

## Requerimientos de Administración (Extensión)

> Esta sección extiende el sistema con un módulo de Administración y Gestión de Usuarios. Se agrega como una extensión independiente y NO modifica los Requerimientos 1 a 16 ni las reglas de Clientes, Productos, Pedidos y Reporte diario.

### Glosario (Extensión)

- **Administrador**: Usuario autenticado que accede a la sección Administración para gestionar los Usuarios de acceso a la aplicación.
- **Usuario_Acceso**: Cuenta que puede iniciar sesión en la aplicación; tiene Nombre_Usuario, contraseña (almacenada solo como hash), Estado_Usuario, fecha de creación, fecha de actualización y, si existe, último acceso.
- **Estado_Usuario**: Valor del Usuario_Acceso; uno de: Activo, Inactivo (corresponde al campo `active`).
- **Sesion**: Sesión de acceso vigente de un Usuario_Acceso, respaldada por una cookie HttpOnly.

### Requerimiento 17: Navegación a Administración y Gestión de Usuarios

**Historia de Usuario:** Como Administrador, quiero una sección Administración con la opción Gestión de Usuarios, para administrar las cuentas de acceso a la aplicación.

#### Criterios de Aceptación

1. THE Sistema SHALL mostrar en el Menu_Lateral una opción Administración, además de las opciones existentes.
2. WHEN el Administrador selecciona Administración, THE Sistema SHALL mostrar un acceso a la opción Gestión de Usuarios.
3. WHEN el Administrador selecciona Gestión de Usuarios, THE Sistema SHALL mostrar la pantalla de administración de Usuarios_Acceso.
4. THE Sistema SHALL mantener sin cambios las secciones Inicio, Clientes, Productos, Pedidos y Reporte diario.

### Requerimiento 18: Listado de usuarios

**Historia de Usuario:** Como Administrador, quiero ver la lista de usuarios, para conocer quién puede acceder a la aplicación y su estado.

#### Criterios de Aceptación

1. WHEN el Administrador abre Gestión de Usuarios, THE Sistema SHALL mostrar la lista de Usuarios_Acceso con ID, Nombre_Usuario, Estado_Usuario, fecha de creación y último acceso (si existe).
2. THE Sistema SHALL mostrar el Estado_Usuario como "Activo" cuando `active` es verdadero y como "Inactivo" cuando `active` es falso.
3. THE Sistema SHALL NOT incluir el hash de contraseña ni el hash del token de sesión en las respuestas de la API ni en la interfaz.

### Requerimiento 19: Creación de usuarios

**Historia de Usuario:** Como Administrador, quiero crear usuarios, para dar acceso a nuevas personas.

#### Criterios de Aceptación

1. WHEN el Administrador envía el formulario de creación con Nombre_Usuario y contraseña, y la contraseña coincide con su confirmación, THE Sistema SHALL crear un nuevo Usuario_Acceso.
2. WHEN el Sistema crea un Usuario_Acceso, THE Sistema SHALL asignarle el Estado_Usuario Activo de forma predeterminada.
3. WHEN el Sistema crea un Usuario_Acceso, THE Sistema SHALL almacenar únicamente el hash de la contraseña usando el mecanismo de hash existente del proyecto, y SHALL NOT almacenar la contraseña en texto plano.
4. IF el Administrador envía el formulario con el Nombre_Usuario vacío, THEN THE Sistema SHALL rechazar la creación y mostrar un mensaje que indique que el Nombre_Usuario es obligatorio.
5. IF el Administrador envía el formulario con la contraseña vacía, THEN THE Sistema SHALL rechazar la creación y mostrar un mensaje que indique que la contraseña es obligatoria.
6. IF la contraseña y su confirmación no coinciden, THEN THE Sistema SHALL rechazar la creación y mostrar un mensaje que indique que las contraseñas no coinciden.
7. IF ya existe un Usuario_Acceso con el mismo Nombre_Usuario, THEN THE Sistema SHALL rechazar la creación y mostrar un mensaje que indique que el Nombre_Usuario ya está en uso.

### Requerimiento 20: Activación de usuarios (dar de alta)

**Historia de Usuario:** Como Administrador, quiero dar de alta un usuario, para permitirle iniciar sesión nuevamente.

#### Criterios de Aceptación

1. WHEN el Administrador da de alta un Usuario_Acceso Inactivo, THE Sistema SHALL establecer su Estado_Usuario en Activo (`active` verdadero).
2. WHILE un Usuario_Acceso tenga Estado_Usuario Activo, THE Sistema SHALL permitirle iniciar sesión con credenciales correctas.

### Requerimiento 21: Desactivación de usuarios (dar de baja)

**Historia de Usuario:** Como Administrador, quiero dar de baja un usuario, para revocar su acceso sin borrar su registro.

#### Criterios de Aceptación

1. WHEN el Administrador da de baja un Usuario_Acceso Activo, THE Sistema SHALL establecer su Estado_Usuario en Inactivo (`active` falso).
2. WHEN el Sistema da de baja un Usuario_Acceso, THE Sistema SHALL invalidar todas las Sesiones activas de ese Usuario_Acceso.
3. THE Sistema SHALL NOT eliminar físicamente el Usuario_Acceso de la base de datos (la baja es lógica).
4. WHILE un Usuario_Acceso tenga Estado_Usuario Inactivo, THE Sistema SHALL rechazar sus intentos de iniciar sesión.

### Requerimiento 22: Cambio de contraseña de un usuario

**Historia de Usuario:** Como Administrador, quiero cambiar la contraseña de un usuario, para restablecer su acceso de forma segura.

#### Criterios de Aceptación

1. WHEN el Administrador envía una nueva contraseña que coincide con su confirmación para un Usuario_Acceso, THE Sistema SHALL actualizar el hash de contraseña usando el mecanismo de hash existente del proyecto.
2. THE Sistema SHALL almacenar únicamente el hash de la nueva contraseña y SHALL NOT almacenar la contraseña en texto plano.
3. IF la nueva contraseña y su confirmación no coinciden, THEN THE Sistema SHALL rechazar el cambio y mostrar un mensaje que indique que las contraseñas no coinciden.
4. WHEN el Sistema cambia la contraseña de un Usuario_Acceso, THE Sistema SHALL invalidar todas las Sesiones activas de ese Usuario_Acceso para obligarlo a iniciar sesión nuevamente.
5. WHEN el Usuario_Acceso inicia sesión después de un cambio de contraseña, THE Sistema SHALL aceptar únicamente la nueva contraseña y SHALL rechazar la contraseña anterior.

### Requerimiento 23: Protección y seguridad de la administración de usuarios

**Historia de Usuario:** Como responsable del sistema, quiero que la administración de usuarios sea segura, para proteger las cuentas de acceso.

#### Criterios de Aceptación

1. THE Sistema SHALL exponer las operaciones de administración de Usuarios_Acceso mediante una API bajo el prefijo `/api` y SHALL requerir una Sesión válida (usuario autenticado) para todas ellas.
2. IF una solicitud a la administración de Usuarios_Acceso no incluye una Sesión válida, THEN THE Sistema SHALL responder con el código HTTP 401.
3. THE Sistema SHALL reutilizar el modelo de Usuario existente (tabla `users`) y NO SHALL crear una segunda tabla de usuarios.
4. THE Sistema SHALL reutilizar el mecanismo de sesión existente (tabla de sesiones y cookie HttpOnly) y NO SHALL introducir un segundo mecanismo de autenticación.
5. IF ocurre un error de validación (Nombre_Usuario duplicado, contraseñas que no coinciden o campos obligatorios vacíos), THEN THE Sistema SHALL responder con un mensaje descriptivo sin revelar información sensible.
