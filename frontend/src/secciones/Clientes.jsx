// Seccion Clientes (Tarea 16.1).
//
// Muestra la lista de clientes en una tabla (dentro de una tarjeta blanca) y
// un formulario para dar de alta o editar clientes. Toda la comunicacion con
// el backend pasa por las funciones de src/api.js (no se usa fetch directo).
//
// Requerimientos cubiertos:
//  - 3.1 Listar clientes con Nombre, Telefono y Direccion.
//  - 3.2 Mensaje cuando no hay clientes registrados.
//  - 2.1 / 2.6 Crear un cliente y reflejarlo en la lista.
//  - 4.1 / 4.3 Editar un cliente existente y reflejar los cambios.
//  - 2.5 / 16.1 Ante error, mostrar el mensaje y CONSERVAR lo ingresado.
//
// El componente se autogestiona: no recibe props. Solo necesita que las
// funciones de api.js apunten al backend (VITE_API_URL).
import { useEffect, useState } from 'react'
import {
  listarClientes,
  crearCliente,
  actualizarCliente,
} from '../api.js'
import estilos from './Clientes.module.css'

// Estado inicial vacio del formulario (campos controlados).
const FORM_VACIO = { nombre: '', telefono: '', direccion: '' }

function Clientes() {
  // Lista de clientes cargada desde el backend.
  const [clientes, setClientes] = useState([])
  // Valores actuales del formulario (alta o edicion).
  const [form, setForm] = useState(FORM_VACIO)
  // id del cliente en edicion; null significa "modo alta".
  const [editandoId, setEditandoId] = useState(null)
  // Mensaje de error de validacion/conexion a mostrar junto al formulario.
  const [error, setError] = useState('')

  // Carga la lista de clientes desde el backend y la guarda en estado.
  // Si falla (por ejemplo, error de conexion), muestra el mensaje.
  async function cargarClientes() {
    try {
      const datos = await listarClientes()
      setClientes(datos || [])
    } catch (err) {
      setError(err.message)
    }
  }

  // Al montar el componente, carga la lista una sola vez (Req. 3.1).
  useEffect(() => {
    cargarClientes()
  }, [])

  // Actualiza un campo del formulario a medida que el usuario escribe.
  function manejarCambio(evento) {
    const { name, value } = evento.target
    setForm((anterior) => ({ ...anterior, [name]: value }))
  }

  // Prepara el formulario para editar un cliente existente (Req. 4.1):
  // copia sus datos al formulario y recuerda su id.
  function comenzarEdicion(cliente) {
    setEditandoId(cliente.id)
    setForm({
      nombre: cliente.nombre || '',
      telefono: cliente.telefono || '',
      direccion: cliente.direccion || '',
    })
    setError('')
  }

  // Cancela la edicion y vuelve al modo alta con el formulario limpio.
  function cancelarEdicion() {
    setEditandoId(null)
    setForm(FORM_VACIO)
    setError('')
  }

  // Envia el formulario: crea (Req. 2.1) o actualiza (Req. 4.3) segun el modo.
  // Ante error, muestra el mensaje del backend y CONSERVA lo ingresado
  // (no se limpia el formulario) (Req. 2.5, 16.1). Ante exito, limpia el
  // formulario y refresca la lista (Req. 2.6, 4.3).
  async function manejarEnvio(evento) {
    evento.preventDefault()
    setError('')

    try {
      if (editandoId === null) {
        await crearCliente(form)
      } else {
        await actualizarCliente(editandoId, form)
      }
      // Exito: limpiar formulario, salir de edicion y refrescar la lista.
      setForm(FORM_VACIO)
      setEditandoId(null)
      await cargarClientes()
    } catch (err) {
      // Error: conservar los datos ingresados y mostrar el mensaje en rojo.
      setError(err.message)
    }
  }

  // Texto del boton segun el modo (alta o edicion).
  const textoBoton = editandoId === null ? 'Crear' : 'Guardar'

  return (
    <div className={estilos.clientes}>
      {/* Tarjeta del formulario de alta / edicion. */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.tituloTarjeta}>
          {editandoId === null ? 'Nuevo cliente' : 'Editar cliente'}
        </h2>

        <form className={estilos.formulario} onSubmit={manejarEnvio}>
          {/* Campo Nombre: etiqueta encima del input. */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="nombre">
              Nombre
            </label>
            <input
              className={estilos.input}
              id="nombre"
              name="nombre"
              type="text"
              value={form.nombre}
              onChange={manejarCambio}
            />
          </div>

          {/* Campo Telefono. */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="telefono">
              Teléfono
            </label>
            <input
              className={estilos.input}
              id="telefono"
              name="telefono"
              type="text"
              value={form.telefono}
              onChange={manejarCambio}
            />
          </div>

          {/* Campo Direccion (opcional). */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="direccion">
              Dirección
            </label>
            <input
              className={estilos.input}
              id="direccion"
              name="direccion"
              type="text"
              value={form.direccion}
              onChange={manejarCambio}
            />
          </div>

          {/* Mensaje de error de validacion / conexion (Req. 2.5, 16.1). */}
          {error && (
            <p className={estilos.error} role="alert">
              {error}
            </p>
          )}

          <div className={estilos.acciones}>
            <button className={estilos.botonPrimario} type="submit">
              {textoBoton}
            </button>
            {/* En modo edicion, permitir cancelar y volver al alta. */}
            {editandoId !== null && (
              <button
                className={estilos.botonSecundario}
                type="button"
                onClick={cancelarEdicion}
              >
                Cancelar
              </button>
            )}
          </div>
        </form>
      </section>

      {/* Tarjeta con la lista de clientes registrados. */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.tituloTarjeta}>Clientes registrados</h2>

        {clientes.length === 0 ? (
          // Mensaje cuando no hay clientes (Req. 3.2).
          <p className={estilos.vacio}>No hay clientes registrados.</p>
        ) : (
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Teléfono</th>
                <th>Dirección</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {clientes.map((cliente) => (
                <tr key={cliente.id}>
                  <td>{cliente.nombre}</td>
                  <td>{cliente.telefono}</td>
                  <td>{cliente.direccion}</td>
                  <td>
                    <button
                      className={estilos.botonAccion}
                      type="button"
                      onClick={() => comenzarEdicion(cliente)}
                    >
                      Editar
                    </button>
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

export default Clientes
