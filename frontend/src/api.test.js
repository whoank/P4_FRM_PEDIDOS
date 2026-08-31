// Pruebas del cliente HTTP centralizado (Tarea 13.2).
//
// Se mockea global.fetch para no hacer peticiones de red reales. El foco es
// verificar el manejo de errores descrito en el diseño:
//  - Respuesta ok -> se devuelve el JSON.
//  - Respuesta con status>=400 y {detail} -> se lanza Error con ese detail (Req. 16.1).
//  - fetch rechaza (fallo de red) -> Error "No fue posible conectar con el servidor." (Req. 16.2).
//  - POST/PATCH usan el método y la ruta correctos.
//
// Requerimientos: 16.1, 16.2

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  API_URL,
  listarClientes,
  crearCliente,
  crearPedido,
  cambiarEstadoPedido,
  obtenerReporteDiario,
} from './api.js'

// Construye una respuesta simulada compatible con lo que espera `request`:
// expone `ok`, `status` y `text()` (el helper lee el cuerpo con .text()).
function respuestaSimulada({ ok, status, cuerpo }) {
  return {
    ok,
    status,
    text: async () => (cuerpo === undefined ? '' : JSON.stringify(cuerpo)),
  }
}

beforeEach(() => {
  // Reemplaza fetch por un mock antes de cada prueba.
  vi.stubGlobal('fetch', vi.fn())
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('request: respuestas exitosas', () => {
  it('listarClientes devuelve el JSON cuando la respuesta es ok', async () => {
    const datos = [{ id: 1, nombre: 'Ana Perez', telefono: '555-1234', direccion: 'Calle 1' }]
    fetch.mockResolvedValueOnce(respuestaSimulada({ ok: true, status: 200, cuerpo: datos }))

    const resultado = await listarClientes()

    expect(resultado).toEqual(datos)
    expect(fetch).toHaveBeenCalledWith(`${API_URL}/clientes`, expect.any(Object))
  })
})

describe('request: error de validación del backend (Req. 16.1)', () => {
  it('lanza un Error con el message igual al detail cuando status >= 400', async () => {
    fetch.mockResolvedValueOnce(
      respuestaSimulada({ ok: false, status: 400, cuerpo: { detail: 'El Nombre es obligatorio.' } })
    )

    await expect(crearCliente({ nombre: '', telefono: '555' })).rejects.toThrow(
      'El Nombre es obligatorio.'
    )
  })

  it('usa un mensaje genérico cuando el error no trae detail', async () => {
    fetch.mockResolvedValueOnce(respuestaSimulada({ ok: false, status: 500, cuerpo: {} }))

    await expect(listarClientes()).rejects.toThrow('Ocurrió un error al procesar la solicitud.')
  })
})

describe('request: error de conexión (Req. 16.2)', () => {
  it('lanza el mensaje fijo cuando fetch rechaza por fallo de red', async () => {
    fetch.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(listarClientes()).rejects.toThrow('No fue posible conectar con el servidor.')
  })
})

describe('métodos y rutas de POST/PATCH', () => {
  it('crearPedido hace POST a /pedidos con el body correcto', async () => {
    const pedido = { cliente_id: 1, producto_id: 1, cantidad: 3 }
    fetch.mockResolvedValueOnce(
      respuestaSimulada({ ok: true, status: 201, cuerpo: { id: 1, ...pedido } })
    )

    await crearPedido(pedido)

    expect(fetch).toHaveBeenCalledWith(
      `${API_URL}/pedidos`,
      expect.objectContaining({ method: 'POST', body: JSON.stringify(pedido) })
    )
  })

  it('cambiarEstadoPedido hace PATCH a /pedidos/{id}/estado con {estado}', async () => {
    fetch.mockResolvedValueOnce(
      respuestaSimulada({ ok: true, status: 200, cuerpo: { id: 5, estado: 'Preparando' } })
    )

    await cambiarEstadoPedido(5, 'Preparando')

    expect(fetch).toHaveBeenCalledWith(
      `${API_URL}/pedidos/5/estado`,
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ estado: 'Preparando' }) })
    )
  })

  it('obtenerReporteDiario agrega ?fecha cuando se pasa una fecha', async () => {
    fetch.mockResolvedValueOnce(
      respuestaSimulada({ ok: true, status: 200, cuerpo: { fecha: '2025-05-20', pedidos: [] } })
    )

    await obtenerReporteDiario('2025-05-20')

    expect(fetch).toHaveBeenCalledWith(
      `${API_URL}/reporte-diario?fecha=2025-05-20`,
      expect.any(Object)
    )
  })
})
