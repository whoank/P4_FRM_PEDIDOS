// Seccion Productos (Tarea 17).
//
// Permite listar los productos, darlos de alta y editarlos, cumpliendo:
// - Req. 6.1: lista de Productos con Nombre, Descripcion, Precio y Disponible.
// - Req. 6.2: mensaje cuando no hay productos registrados.
// - Req. 5.1, 5.6: alta de producto y refresco de la lista.
// - Req. 5.5: Disponible verdadero por defecto en el formulario de alta.
// - Req. 7.1: edicion de un producto existente (incluye marcar/desmarcar Disponible).
// - Req. 16.1 / 5.2: ante error, se muestra el mensaje en rojo y se CONSERVAN
//   los datos ingresados en el formulario.
//
// Toda la comunicacion con el backend usa las funciones de src/api.js
// (no se usa fetch directo). La validacion autoritativa vive en el backend;
// aqui solo se muestran sus mensajes de error.

import { useEffect, useState } from 'react'
import {
  listarProductos,
  crearProducto,
  actualizarProducto,
} from '../api.js'
import estilos from './Productos.module.css'

// Estado inicial del formulario. Disponible arranca en true (Req. 5.5).
const FORM_INICIAL = {
  nombre: '',
  descripcion: '',
  precio: '',
  disponible: true,
}

function Productos() {
  // Lista de productos mostrada en la tabla.
  const [productos, setProductos] = useState([])
  // Datos actuales del formulario (alta o edicion).
  const [form, setForm] = useState(FORM_INICIAL)
  // id del producto en edicion; null cuando es un alta.
  const [editandoId, setEditandoId] = useState(null)
  // Mensaje de error a mostrar en rojo (vacio si no hay error).
  const [error, setError] = useState('')

  // Carga inicial de la lista al montar el componente (Req. 6.1).
  useEffect(() => {
    refrescarLista()
  }, [])

  // Refresca la lista de productos desde el backend.
  async function refrescarLista() {
    try {
      const datos = await listarProductos()
      setProductos(datos || [])
    } catch (err) {
      // Error de conexion o de servidor al listar: se muestra el mensaje.
      setError(err.message)
    }
  }

  // Actualiza un campo del formulario segun el input que cambia.
  function manejarCambio(evento) {
    const { name, value, type, checked } = evento.target
    setForm((anterior) => ({
      ...anterior,
      [name]: type === 'checkbox' ? checked : value,
    }))
  }

  // Carga los datos de un producto en el formulario para editarlo (Req. 7.1).
  function comenzarEdicion(producto) {
    setEditandoId(producto.id)
    setForm({
      nombre: producto.nombre ?? '',
      descripcion: producto.descripcion ?? '',
      // El precio llega como numero/decimal; se muestra como texto en el input.
      precio: producto.precio != null ? String(producto.precio) : '',
      disponible: Boolean(producto.disponible),
    })
    setError('')
  }

  // Cancela la edicion y vuelve al formulario de alta vacio.
  function cancelarEdicion() {
    setEditandoId(null)
    setForm(FORM_INICIAL)
    setError('')
  }

  // Envia el formulario: crea (Req. 5.1) o actualiza (Req. 7.1) segun el modo.
  async function manejarEnvio(evento) {
    evento.preventDefault()
    setError('')

    // El precio se envia como cadena tal cual se ingreso; la validacion
    // numerica y de rango es autoritativa en el backend (Req. 5.3, 5.4).
    const datos = {
      nombre: form.nombre,
      descripcion: form.descripcion,
      precio: form.precio,
      disponible: form.disponible,
    }

    try {
      if (editandoId != null) {
        await actualizarProducto(editandoId, datos)
      } else {
        await crearProducto(datos)
      }
      // Exito: se limpia el formulario y se refresca la lista (Req. 5.6, 7.1).
      cancelarEdicion()
      await refrescarLista()
    } catch (err) {
      // Error de validacion/negocio/conexion: se muestra el mensaje en rojo y
      // se CONSERVAN los datos ingresados en el formulario (Req. 16.1, 5.2).
      setError(err.message)
    }
  }

  const enEdicion = editandoId != null

  return (
    <div className={estilos.productos}>
      {/* Tarjeta del formulario de alta / edicion. */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.tituloTarjeta}>
          {enEdicion ? 'Editar producto' : 'Nuevo producto'}
        </h2>

        <form className={estilos.formulario} onSubmit={manejarEnvio}>
          {/* Nombre */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="nombre">
              Nombre
            </label>
            <input
              id="nombre"
              name="nombre"
              type="text"
              className={estilos.input}
              value={form.nombre}
              onChange={manejarCambio}
            />
          </div>

          {/* Descripcion */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="descripcion">
              Descripción
            </label>
            <textarea
              id="descripcion"
              name="descripcion"
              className={estilos.textarea}
              value={form.descripcion}
              onChange={manejarCambio}
            />
          </div>

          {/* Precio (numerico) */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="precio">
              Precio
            </label>
            <input
              id="precio"
              name="precio"
              type="number"
              step="0.01"
              min="0"
              className={estilos.input}
              value={form.precio}
              onChange={manejarCambio}
            />
          </div>

          {/* Disponible (checkbox) */}
          <div className={estilos.campoCheckbox}>
            <input
              id="disponible"
              name="disponible"
              type="checkbox"
              className={estilos.checkbox}
              checked={form.disponible}
              onChange={manejarCambio}
            />
            <label className={estilos.etiqueta} htmlFor="disponible">
              Disponible
            </label>
          </div>

          {/* Mensaje de error en rojo (Req. 16.1). */}
          {error && <p className={estilos.error}>{error}</p>}

          {/* Botones: primario y, en edicion, cancelar. */}
          <div className={estilos.acciones}>
            <button type="submit" className={estilos.botonPrimario}>
              {enEdicion ? 'Guardar' : 'Crear'}
            </button>
            {enEdicion && (
              <button
                type="button"
                className={estilos.botonSecundario}
                onClick={cancelarEdicion}
              >
                Cancelar
              </button>
            )}
          </div>
        </form>
      </section>

      {/* Tarjeta con la lista de productos. */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.tituloTarjeta}>Productos registrados</h2>

        {productos.length === 0 ? (
          // Mensaje cuando no hay productos (Req. 6.2).
          <p className={estilos.vacio}>No hay productos registrados.</p>
        ) : (
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Descripción</th>
                <th>Precio</th>
                <th>Disponible</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {productos.map((producto) => (
                <tr key={producto.id}>
                  <td>{producto.nombre}</td>
                  <td>{producto.descripcion}</td>
                  <td>{producto.precio}</td>
                  <td>{producto.disponible ? 'Sí' : 'No'}</td>
                  <td>
                    <button
                      type="button"
                      className={estilos.accionTabla}
                      onClick={() => comenzarEdicion(producto)}
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

export default Productos
