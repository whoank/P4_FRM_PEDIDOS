// Seccion Pedidos (Tarea 18.1).
//
// Responsabilidades (Req. 8, 9, 10, 11, 16.1):
//  - Formulario de creacion de pedido: selector de Cliente, selector de
//    Producto (SOLO disponibles), campo Cantidad (entero) y previsualizacion
//    del Total que se recalcula al cambiar la cantidad o el producto.
//  - Lista de pedidos (tabla) con Cliente, Producto, Cantidad, Precio unitario,
//    Total, Fecha y Estado; mensaje cuando no hay pedidos (Req. 11.1, 11.2).
//  - Control para cambiar el estado de cada pedido (Req. 10.1, 10.2).
//  - Ante error del backend, muestra el mensaje en rojo y conserva los datos
//    ingresados (Req. 16.1).
//
// Este componente NO usa fetch directo: reutiliza las funciones de api.js.
// El backend es la autoridad: valida y recalcula el total. La previsualizacion
// del Total aqui es solo para mejorar la experiencia (Req. 9.2, 9.3).
//
// Requerimientos: 8.1, 8.5, 8.6, 8.7, 8.8, 9.2, 9.3, 10.1, 10.2, 11.1, 11.2, 16.1
import { useEffect, useMemo, useState } from 'react'
import {
  listarPedidos,
  crearPedido,
  cambiarEstadoPedido,
  listarClientes,
  listarProductos,
} from '../api.js'
import estilos from './Pedidos.module.css'

// Los 4 estados validos del ciclo de vida de un pedido (Req. 10.1).
const ESTADOS = ['Pendiente', 'Preparando', 'Entregado', 'Cancelado']

// Formatea un numero como monto con 2 decimales para la previsualizacion.
// Se usa Number(...) porque el precio del producto puede llegar como string
// o number desde la API; el backend recalcula el valor autoritativo.
function formatearMonto(valor) {
  return Number(valor).toFixed(2)
}

export default function Pedidos() {
  // Datos cargados desde la API.
  const [clientes, setClientes] = useState([])
  const [productos, setProductos] = useState([]) // Solo disponibles (Req. 7.3, 8.8).
  const [pedidos, setPedidos] = useState([])

  // Estado del formulario de creacion. Se conserva ante errores (Req. 16.1).
  const [clienteId, setClienteId] = useState('')
  const [productoId, setProductoId] = useState('')
  const [cantidad, setCantidad] = useState('1')

  // Mensajes de error (creacion y cambio de estado) mostrados en rojo.
  const [error, setError] = useState('')

  // Carga inicial: clientes, productos disponibles y pedidos.
  useEffect(() => {
    cargarClientes()
    cargarProductos()
    cargarPedidos()
  }, [])

  async function cargarClientes() {
    try {
      setClientes(await listarClientes())
    } catch (e) {
      setError(e.message)
    }
  }

  async function cargarProductos() {
    try {
      // true => ?solo_disponibles=true: el selector solo lista disponibles
      // (Req. 7.3, 8.8).
      setProductos(await listarProductos(true))
    } catch (e) {
      setError(e.message)
    }
  }

  async function cargarPedidos() {
    try {
      setPedidos(await listarPedidos())
    } catch (e) {
      setError(e.message)
    }
  }

  // Producto actualmente seleccionado (para tomar su precio unitario).
  const productoSeleccionado = useMemo(
    () => productos.find((p) => String(p.id) === String(productoId)),
    [productos, productoId]
  )

  // Previsualizacion del Total = cantidad * precio_unitario (Req. 9.2, 9.3).
  // Se recalcula automaticamente cuando cambia la cantidad o el producto,
  // porque depende de `cantidad` y `productoSeleccionado`.
  const totalPrevisualizado = useMemo(() => {
    const cantidadNum = parseInt(cantidad, 10)
    if (!productoSeleccionado || Number.isNaN(cantidadNum) || cantidadNum <= 0) {
      return null
    }
    return cantidadNum * Number(productoSeleccionado.precio)
  }, [cantidad, productoSeleccionado])

  // Envia el formulario para crear el pedido (Req. 8.1).
  async function manejarCrear(evento) {
    evento.preventDefault()
    setError('')
    try {
      // El frontend NO envia precio ni total: los calcula el backend.
      await crearPedido({
        cliente_id: clienteId ? Number(clienteId) : null,
        producto_id: productoId ? Number(productoId) : null,
        cantidad: cantidad === '' ? null : Number(cantidad),
      })
      // Exito: limpia el formulario y refresca la lista.
      setClienteId('')
      setProductoId('')
      setCantidad('1')
      await cargarPedidos()
    } catch (e) {
      // Error de validacion/negocio: muestra el mensaje y conserva los datos
      // ingresados (Req. 16.1).
      setError(e.message)
    }
  }

  // Cambia el estado de un pedido (Req. 10.1, 10.2).
  async function manejarCambioEstado(id, nuevoEstado) {
    setError('')
    try {
      await cambiarEstadoPedido(id, nuevoEstado)
      await cargarPedidos()
    } catch (e) {
      // Ante error se muestra el mensaje; el backend conserva el estado anterior.
      setError(e.message)
    }
  }

  return (
    <div className={estilos.pedidos}>
      {/* Tarjeta con el formulario de creacion de pedido. */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.tituloTarjeta}>Nuevo pedido</h2>

        <form className={estilos.formulario} onSubmit={manejarCrear}>
          {/* Selector de Cliente (Req. 8.6). */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="pedido-cliente">
              Cliente
            </label>
            <select
              id="pedido-cliente"
              className={estilos.select}
              value={clienteId}
              onChange={(e) => setClienteId(e.target.value)}
            >
              <option value="">Selecciona un cliente</option>
              {clientes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </div>

          {/* Selector de Producto: SOLO disponibles (Req. 7.3, 8.8). */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="pedido-producto">
              Producto
            </label>
            <select
              id="pedido-producto"
              className={estilos.select}
              value={productoId}
              onChange={(e) => setProductoId(e.target.value)}
            >
              <option value="">Selecciona un producto</option>
              {productos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nombre} (${formatearMonto(p.precio)})
                </option>
              ))}
            </select>
          </div>

          {/* Campo Cantidad (entero) (Req. 8.5). */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="pedido-cantidad">
              Cantidad
            </label>
            <input
              id="pedido-cantidad"
              className={estilos.input}
              type="number"
              min="1"
              max="9999"
              step="1"
              value={cantidad}
              onChange={(e) => setCantidad(e.target.value)}
            />
          </div>

          {/* Previsualizacion del Total (Req. 9.2, 9.3). El backend recalcula
              el valor autoritativo; esto es solo previsualizacion. */}
          <div className={estilos.campo}>
            <span className={estilos.etiqueta}>Total (previsualizacion)</span>
            <span className={estilos.total} data-testid="total-previsualizado">
              {totalPrevisualizado === null
                ? '—'
                : `$${formatearMonto(totalPrevisualizado)}`}
            </span>
          </div>

          {/* Mensaje de error (conserva los datos ingresados, Req. 16.1). */}
          {error && <p className={estilos.error}>{error}</p>}

          <div className={estilos.acciones}>
            <button type="submit" className={estilos.botonPrimario}>
              Crear pedido
            </button>
          </div>
        </form>
      </section>

      {/* Tarjeta con la lista de pedidos (Req. 11.1, 11.2). */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.tituloTarjeta}>Pedidos registrados</h2>

        {pedidos.length === 0 ? (
          // Mensaje cuando no hay pedidos (Req. 11.2).
          <p className={estilos.vacio}>No hay pedidos registrados.</p>
        ) : (
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Cliente</th>
                <th>Producto</th>
                <th>Cantidad</th>
                <th>Precio unitario</th>
                <th>Total</th>
                <th>Fecha</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {pedidos.map((pedido) => (
                <tr key={pedido.id}>
                  <td>{pedido.cliente_nombre}</td>
                  <td>{pedido.producto_nombre}</td>
                  <td>{pedido.cantidad}</td>
                  <td>${formatearMonto(pedido.precio_unitario)}</td>
                  <td>${formatearMonto(pedido.total)}</td>
                  <td>{pedido.fecha}</td>
                  <td>
                    {/* Control para cambiar el estado (Req. 10.1, 10.2). */}
                    <select
                      className={estilos.selectEstado}
                      aria-label={`Estado del pedido ${pedido.id}`}
                      value={pedido.estado}
                      onChange={(e) =>
                        manejarCambioEstado(pedido.id, e.target.value)
                      }
                    >
                      {ESTADOS.map((estado) => (
                        <option key={estado} value={estado}>
                          {estado}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
