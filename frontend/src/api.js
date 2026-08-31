// Cliente HTTP centralizado del frontend (Tarea 13).
//
// Este módulo concentra toda la comunicación con la API REST del backend.
// Las secciones (Clientes, Productos, Pedidos, Reporte) importan estas
// funciones y NO usan `fetch` directamente. Así el manejo de errores queda
// en un solo lugar (Req. 15, 16).
//
// Base URL del backend, leída de la variable de entorno de Vite.
// En desarrollo/producción se define en .env como VITE_API_URL
// (por ejemplo: http://localhost:8000/api).
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

// Mensaje fijo que se muestra cuando no se puede contactar al backend (Req. 16.2).
const MENSAJE_ERROR_CONEXION = 'No fue posible conectar con el servidor.'

/**
 * Helper interno que realiza una petición HTTP y normaliza el manejo de errores.
 *
 * Reglas (design.md → Error Handling frontend):
 * - Si la respuesta NO es ok (status >= 400): se intenta leer el JSON del
 *   cuerpo y extraer el campo `detail` (convención de FastAPI). Se lanza un
 *   Error con ese mensaje para que la sección lo muestre junto al formulario
 *   conservando los datos ingresados (Req. 16.1). Si no hay `detail`, se usa
 *   un mensaje genérico.
 * - Si `fetch` lanza (fallo de red, backend caído): se captura y se propaga un
 *   Error con el mensaje EXACTO "No fue posible conectar con el servidor."
 *   (Req. 16.2).
 * - En una respuesta ok se devuelve el JSON parseado (o `null` si no hay cuerpo).
 *
 * @param {string} path  Ruta relativa a la API, p. ej. "/clientes".
 * @param {object} [options]  Opciones de fetch (method, body, headers...).
 * @returns {Promise<any>}  El JSON de la respuesta, o null si no hay cuerpo.
 */
async function request(path, options = {}) {
  let respuesta
  try {
    respuesta = await fetch(`${API_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch (error) {
    // Fallo de red: el backend no respondió (Req. 16.2).
    // Se distingue del error de validación: aquí NO hay respuesta del servidor.
    throw new Error(MENSAJE_ERROR_CONEXION)
  }

  // La respuesta llegó. Intentamos parsear el cuerpo como JSON (puede no haberlo).
  let cuerpo = null
  try {
    const texto = await respuesta.text()
    cuerpo = texto ? JSON.parse(texto) : null
  } catch (error) {
    // Respuesta sin cuerpo o cuerpo no-JSON: se deja `cuerpo` en null.
    cuerpo = null
  }

  if (!respuesta.ok) {
    // Error de validación / negocio / recurso inexistente (400, 404, 422...).
    // El backend envía el mensaje en la clave `detail` (Req. 16.1).
    const mensaje =
      (cuerpo && cuerpo.detail) || 'Ocurrió un error al procesar la solicitud.'
    throw new Error(mensaje)
  }

  return cuerpo
}

// Serializa el cuerpo a JSON de forma uniforme para POST/PUT/PATCH.
function conCuerpo(metodo, datos) {
  return { method: metodo, body: JSON.stringify(datos) }
}

// ---------------------------------------------------------------------------
// Clientes (Req. 2, 3, 4)
// ---------------------------------------------------------------------------

export function listarClientes() {
  return request('/clientes')
}

export function crearCliente(datos) {
  return request('/clientes', conCuerpo('POST', datos))
}

export function obtenerCliente(id) {
  return request(`/clientes/${id}`)
}

export function actualizarCliente(id, datos) {
  return request(`/clientes/${id}`, conCuerpo('PUT', datos))
}

// ---------------------------------------------------------------------------
// Productos (Req. 5, 6, 7)
// ---------------------------------------------------------------------------

// Si `soloDisponibles` es true, agrega ?solo_disponibles=true para el selector
// de pedidos (design.md → Router productos).
export function listarProductos(soloDisponibles = false) {
  const query = soloDisponibles ? '?solo_disponibles=true' : ''
  return request(`/productos${query}`)
}

export function crearProducto(datos) {
  return request('/productos', conCuerpo('POST', datos))
}

export function obtenerProducto(id) {
  return request(`/productos/${id}`)
}

export function actualizarProducto(id, datos) {
  return request(`/productos/${id}`, conCuerpo('PUT', datos))
}

// ---------------------------------------------------------------------------
// Pedidos (Req. 8, 9, 10, 11)
// ---------------------------------------------------------------------------

export function listarPedidos() {
  return request('/pedidos')
}

// El frontend NO envía precio ni total: los calcula el backend (design.md).
export function crearPedido(datos) {
  return request('/pedidos', conCuerpo('POST', datos))
}

// Cambia el estado del pedido: PATCH /api/pedidos/{id}/estado con body {estado}.
export function cambiarEstadoPedido(id, estado) {
  return request(`/pedidos/${id}/estado`, conCuerpo('PATCH', { estado }))
}

// ---------------------------------------------------------------------------
// Reporte diario (Req. 12)
// ---------------------------------------------------------------------------

// Si se pasa `fecha` (YYYY-MM-DD) agrega ?fecha=...; si se omite, el backend
// usa el día actual.
export function obtenerReporteDiario(fecha) {
  const query = fecha ? `?fecha=${encodeURIComponent(fecha)}` : ''
  return request(`/reporte-diario${query}`)
}
