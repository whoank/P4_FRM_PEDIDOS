// Seccion Reporte diario (Tarea 19).
//
// Responsabilidades (Req. 12):
//  - Selector de dia (input type="date") cuyo valor por defecto es HOY (Req. 12.1).
//  - Al montar, carga el reporte de hoy con obtenerReporteDiario() (Req. 12.1).
//  - Al cambiar la fecha, recarga con obtenerReporteDiario(fecha) (Req. 12.2).
//  - Muestra, en tarjetas blancas:
//      * la cantidad total de pedidos del dia (Req. 12.4),
//      * la suma de ventas del dia (excluye cancelados; ya viene calculada del
//        backend en suma_ventas), destacada (Req. 12.5),
//      * una tabla con los pedidos del dia: cliente, producto, cantidad, total,
//        estado (Req. 12.3).
//  - Si no hay pedidos ese dia, muestra "No hay pedidos para ese dia." (Req. 12.6).
//  - Si obtenerReporteDiario lanza (error de conexion o del backend), muestra el
//    mensaje (error.message) en un aviso.
//
// Desacople de App.jsx (concurrencia): este componente es autonomo. No recibe
// props obligatorias ni conoce el enrutado; solo consume la API centralizada.
//
// Requerimientos: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
import { useEffect, useState } from 'react'
import { obtenerReporteDiario } from '../api'
import estilos from './ReporteDiario.module.css'

// Devuelve la fecha de HOY en formato YYYY-MM-DD (el formato que usa el
// input type="date" y que espera el backend). Se usa la fecha LOCAL para
// que coincida con el dia del usuario, no UTC.
function fechaHoy() {
  const ahora = new Date()
  const anio = ahora.getFullYear()
  // getMonth() es 0-indexado; padStart asegura 2 digitos.
  const mes = String(ahora.getMonth() + 1).padStart(2, '0')
  const dia = String(ahora.getDate()).padStart(2, '0')
  return `${anio}-${mes}-${dia}`
}

// Formatea un monto numerico como moneda simple con 2 decimales.
// El backend usa NUMERIC (Decimal); aqui solo se presenta el valor.
function formatearMonto(valor) {
  const numero = Number(valor ?? 0)
  return numero.toLocaleString('es-MX', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export default function ReporteDiario() {
  // Fecha seleccionada en el input (por defecto, HOY -> Req. 12.1).
  const [fecha, setFecha] = useState(fechaHoy())
  // Datos del reporte devueltos por el backend:
  // { fecha, cantidad_pedidos, suma_ventas, pedidos: [...] }.
  const [reporte, setReporte] = useState(null)
  // Indicador de carga para dar retroalimentacion mientras se consulta.
  const [cargando, setCargando] = useState(false)
  // Mensaje de error (validacion/backend o conexion). Vacio = sin error.
  const [error, setError] = useState('')

  // Carga el reporte cada vez que cambia la fecha seleccionada.
  // Al montar, `fecha` ya es HOY, por lo que se carga el reporte de hoy
  // (Req. 12.1); al cambiar la fecha, se recarga (Req. 12.2).
  useEffect(() => {
    // Bandera para evitar actualizar el estado si el componente se desmonta
    // o si la fecha cambia antes de que termine la peticion en curso.
    let vigente = true

    async function cargar() {
      setCargando(true)
      setError('')
      try {
        // Se pasa la fecha explicita; el backend tambien aceptaria omitirla.
        const datos = await obtenerReporteDiario(fecha)
        if (vigente) {
          setReporte(datos)
        }
      } catch (e) {
        // El cliente HTTP (api.js) ya normaliza el mensaje: detail del backend
        // o "No fue posible conectar con el servidor." (Req. 16.2).
        if (vigente) {
          setError(e.message)
          setReporte(null)
        }
      } finally {
        if (vigente) {
          setCargando(false)
        }
      }
    }

    cargar()

    // Cleanup: invalida la peticion anterior si la fecha vuelve a cambiar.
    return () => {
      vigente = false
    }
  }, [fecha])

  // Lista de pedidos del dia (defensivo: array vacio si aun no hay datos).
  const pedidos = reporte?.pedidos ?? []
  // ¿No hay pedidos ese dia? (pedidos vacio o cantidad 0 -> Req. 12.6).
  const sinPedidos =
    !cargando &&
    !error &&
    reporte !== null &&
    (pedidos.length === 0 || reporte.cantidad_pedidos === 0)

  return (
    <div className={estilos.reporte}>
      {/* Tarjeta con el selector de dia (Req. 12.1, 12.2). */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.titulo}>Reporte diario</h2>
        <div className={estilos.selector}>
          <label className={estilos.etiqueta} htmlFor="reporte-fecha">
            Dia
          </label>
          <input
            id="reporte-fecha"
            className={estilos.input}
            type="date"
            value={fecha}
            // Al cambiar la fecha se recarga el reporte via useEffect (Req. 12.2).
            onChange={(evento) => setFecha(evento.target.value)}
          />
        </div>
      </section>

      {/* Aviso de error de conexion o del backend (Req. 16.2). */}
      {error && (
        <div className={estilos.aviso} role="alert">
          {error}
        </div>
      )}

      {/* Tarjetas de resumen: conteo (Req. 12.4) y suma destacada (Req. 12.5). */}
      {!error && reporte && (
        <section className={estilos.resumen}>
          <div className={estilos.tarjetaResumen}>
            <span className={estilos.resumenEtiqueta}>Pedidos del dia</span>
            <span className={estilos.resumenValor}>
              {reporte.cantidad_pedidos}
            </span>
          </div>
          <div className={`${estilos.tarjetaResumen} ${estilos.destacada}`}>
            <span className={estilos.resumenEtiqueta}>Ventas del dia</span>
            <span className={estilos.resumenValorDestacado}>
              ${formatearMonto(reporte.suma_ventas)}
            </span>
          </div>
        </section>
      )}

      {/* Tabla de pedidos del dia (Req. 12.3) o mensaje si no hay (Req. 12.6). */}
      {!error && (
        <section className={estilos.tarjeta}>
          <h3 className={estilos.tituloTabla}>Pedidos</h3>

          {cargando && <p className={estilos.mensaje}>Cargando reporte...</p>}

          {sinPedidos && (
            <p className={estilos.mensaje}>No hay pedidos para ese dia.</p>
          )}

          {!cargando && !sinPedidos && pedidos.length > 0 && (
            <table className={estilos.tabla}>
              <thead>
                <tr>
                  <th className={estilos.th}>Cliente</th>
                  <th className={estilos.th}>Producto</th>
                  <th className={estilos.th}>Cantidad</th>
                  <th className={estilos.th}>Total</th>
                  <th className={estilos.th}>Estado</th>
                </tr>
              </thead>
              <tbody>
                {pedidos.map((pedido) => (
                  <tr key={pedido.id}>
                    <td className={estilos.td}>{pedido.cliente_nombre}</td>
                    <td className={estilos.td}>{pedido.producto_nombre}</td>
                    <td className={estilos.td}>{pedido.cantidad}</td>
                    <td className={estilos.td}>${formatearMonto(pedido.total)}</td>
                    <td className={estilos.td}>{pedido.estado}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  )
}
