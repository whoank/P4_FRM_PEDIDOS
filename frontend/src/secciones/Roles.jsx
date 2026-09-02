// Seccion Roles (Administracion > Roles).
//
// Pantalla de gestion de roles y sus permisos. Reutiliza el patron visual de
// la app (tarjetas, tabla, formulario con checkboxes, badges y mensajes) igual
// que GestionUsuarios. Toda la comunicacion con el backend pasa por api.js.
//
// Funcionalidad:
//  - Al montar, carga los roles (listarRoles) y el catalogo de permisos
//    (listarPermisos) para poblar los checkboxes del formulario.
//  - Tabla con Nombre, Descripcion, Estado (badge), cantidad de Permisos y
//    Acciones (Editar, Activar/Desactivar).
//  - Formulario (crear/editar) con nombre, descripcion, activo y la lista de
//    permisos como checkboxes del catalogo (nunca texto libre).
//  - Mensajes de exito (acento) y error (rojo, role="alert").
//
// El componente se autogestiona: no recibe props obligatorias.
import { useEffect, useState } from 'react'
import {
  listarRoles,
  listarPermisos,
  crearRol,
  actualizarRol,
  cambiarEstadoRol,
} from '../api.js'
import estilos from './Roles.module.css'

// Estado inicial vacio del formulario (campos controlados).
// `permisos` es un array de codigos marcados.
const FORM_VACIO = { nombre: '', descripcion: '', activo: true, permisos: [] }

export default function Roles() {
  // Lista de roles cargada desde el backend.
  const [roles, setRoles] = useState([])
  // Catalogo de permisos disponibles (para los checkboxes).
  const [permisosCatalogo, setPermisosCatalogo] = useState([])

  // Controla si el formulario (crear/editar) esta visible.
  const [mostrarForm, setMostrarForm] = useState(false)
  // id del rol en edicion; null significa que el formulario es de CREACION.
  const [editandoId, setEditandoId] = useState(null)
  // Valores actuales del formulario.
  const [form, setForm] = useState(FORM_VACIO)
  // Mensaje de error del formulario (rojo).
  const [errorForm, setErrorForm] = useState('')

  // Mensajes globales de la seccion.
  const [errorLista, setErrorLista] = useState('')
  const [exito, setExito] = useState('')

  // Carga los roles desde el backend y los guarda en estado.
  async function cargarRoles() {
    try {
      const datos = await listarRoles()
      setRoles(datos || [])
      setErrorLista('')
    } catch (err) {
      setErrorLista(err.message)
    }
  }

  // Carga el catalogo de permisos (una sola vez, para los checkboxes).
  async function cargarPermisos() {
    try {
      const datos = await listarPermisos()
      setPermisosCatalogo(datos || [])
    } catch (err) {
      setErrorLista(err.message)
    }
  }

  // Al montar, carga roles y catalogo de permisos.
  useEffect(() => {
    cargarRoles()
    cargarPermisos()
  }, [])

  // --- Formulario -------------------------------------------------------

  // Actualiza un campo de texto del formulario mientras se escribe.
  function manejarCambio(evento) {
    const { name, value } = evento.target
    setForm((anterior) => ({ ...anterior, [name]: value }))
  }

  // Alterna el checkbox "Activo".
  function manejarCambioActivo(evento) {
    const { checked } = evento.target
    setForm((anterior) => ({ ...anterior, activo: checked }))
  }

  // Alterna un permiso en la lista de codigos marcados.
  function alternarPermiso(codigo) {
    setForm((anterior) => {
      const marcado = anterior.permisos.includes(codigo)
      const permisos = marcado
        ? anterior.permisos.filter((c) => c !== codigo)
        : [...anterior.permisos, codigo]
      return { ...anterior, permisos }
    })
  }

  // Abre el formulario en modo CREACION (limpia estado previo).
  function abrirCrear() {
    setEditandoId(null)
    setForm(FORM_VACIO)
    setErrorForm('')
    setExito('')
    setMostrarForm(true)
  }

  // Abre el formulario en modo EDICION: precarga los datos del rol y marca los
  // checkboxes de los permisos que ya tiene (rol.permisos -> codigos).
  function abrirEditar(rol) {
    setEditandoId(rol.id)
    setForm({
      nombre: rol.nombre || '',
      descripcion: rol.descripcion || '',
      activo: rol.activo === true,
      permisos: (rol.permisos || []).map((p) => p.codigo),
    })
    setErrorForm('')
    setExito('')
    setMostrarForm(true)
  }

  // Cierra el formulario y limpia los campos (no persiste nada).
  function cancelar() {
    setMostrarForm(false)
    setEditandoId(null)
    setForm(FORM_VACIO)
    setErrorForm('')
  }

  // Envia el formulario (crear o actualizar segun editandoId).
  async function manejarEnvio(evento) {
    evento.preventDefault()
    setErrorForm('')
    setExito('')

    // Validacion minima en cliente: el nombre es obligatorio. El backend
    // valida unicidad y la existencia de los permisos.
    if (!form.nombre.trim()) {
      setErrorForm('El nombre del rol es obligatorio.')
      return
    }

    const datos = {
      nombre: form.nombre,
      descripcion: form.descripcion,
      activo: form.activo,
      permisos: form.permisos,
    }

    try {
      if (editandoId === null) {
        // Creacion.
        await crearRol(datos)
        setExito('Rol creado.')
      } else {
        // Edicion (reemplaza los permisos).
        await actualizarRol(editandoId, datos)
        setExito('Rol actualizado.')
      }
      // Exito: cerrar formulario, limpiar y refrescar la lista.
      setMostrarForm(false)
      setEditandoId(null)
      setForm(FORM_VACIO)
      await cargarRoles()
    } catch (err) {
      // Error: conservar lo ingresado y mostrar el mensaje del backend
      // (p. ej. "Ya existe un rol con ese nombre.").
      setErrorForm(err.message)
    }
  }

  // --- Activar / desactivar --------------------------------------------

  // Cambia el estado del rol. Si el backend responde 400 (p. ej. salvaguarda
  // del rol de administrador), se muestra el mensaje de error.
  async function manejarCambiarEstado(rol) {
    setExito('')
    setErrorLista('')
    try {
      await cambiarEstadoRol(rol.id, !rol.activo)
      await cargarRoles()
    } catch (err) {
      setErrorLista(err.message)
    }
  }

  return (
    <div className={estilos.roles}>
      {/* Tarjeta del formulario (crear/editar), desplegable. */}
      <section className={estilos.tarjeta}>
        <div className={estilos.cabeceraTarjeta}>
          <h2 className={estilos.tituloTarjeta}>Roles</h2>
          {!mostrarForm && (
            <button
              className={estilos.botonPrimario}
              type="button"
              onClick={abrirCrear}
            >
              Crear rol
            </button>
          )}
        </div>

        {mostrarForm && (
          <form className={estilos.formulario} onSubmit={manejarEnvio}>
            {/* Campo Nombre. */}
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

            {/* Campo Descripcion (textarea). */}
            <div className={estilos.campo}>
              <label className={estilos.etiqueta} htmlFor="descripcion">
                Descripción
              </label>
              <textarea
                className={estilos.input}
                id="descripcion"
                name="descripcion"
                rows={2}
                value={form.descripcion}
                onChange={manejarCambio}
              />
            </div>

            {/* Campo Activo (checkbox). */}
            <div className={estilos.campoCheckbox}>
              <input
                id="activo"
                name="activo"
                type="checkbox"
                checked={form.activo}
                onChange={manejarCambioActivo}
              />
              <label htmlFor="activo">Activo</label>
            </div>

            {/* Lista de permisos como checkboxes del catalogo. */}
            <div className={estilos.campo}>
              <span className={estilos.etiqueta}>Permisos</span>
              <div className={estilos.grupoCheckboxes}>
                {permisosCatalogo.map((permiso) => (
                  <label key={permiso.codigo} className={estilos.checkbox}>
                    <input
                      type="checkbox"
                      value={permiso.codigo}
                      checked={form.permisos.includes(permiso.codigo)}
                      onChange={() => alternarPermiso(permiso.codigo)}
                    />
                    {permiso.nombre}
                  </label>
                ))}
              </div>
            </div>

            {/* Mensaje de error de validacion / negocio / conexion. */}
            {errorForm && (
              <p className={estilos.error} role="alert">
                {errorForm}
              </p>
            )}

            <div className={estilos.acciones}>
              <button className={estilos.botonPrimario} type="submit">
                Guardar
              </button>
              <button
                className={estilos.botonSecundario}
                type="button"
                onClick={cancelar}
              >
                Cancelar
              </button>
            </div>
          </form>
        )}

        {/* Mensaje de exito global (acento). */}
        {exito && <p className={estilos.exito}>{exito}</p>}
      </section>

      {/* Tarjeta con la lista de roles registrados. */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.tituloTarjeta}>Roles registrados</h2>

        {/* Error al cargar / operar sobre la lista. */}
        {errorLista && (
          <p className={estilos.error} role="alert">
            {errorLista}
          </p>
        )}

        {roles.length === 0 ? (
          <p className={estilos.vacio}>No hay roles registrados.</p>
        ) : (
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Descripción</th>
                <th>Estado</th>
                <th>Permisos</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((rol) => {
                const activo = rol.activo === true
                // Cantidad de permisos: usa cantidad_permisos si viene, o el
                // largo del array de permisos como respaldo.
                const cantidad =
                  rol.cantidad_permisos ??
                  (rol.permisos ? rol.permisos.length : 0)
                return (
                  <tr key={rol.id}>
                    <td>{rol.nombre}</td>
                    <td>{rol.descripcion || '\u2014'}</td>
                    <td>
                      <span
                        className={
                          estilos.badge +
                          ' ' +
                          (activo ? estilos.badgeActivo : estilos.badgeInactivo)
                        }
                      >
                        {activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    <td>{cantidad}</td>
                    <td>
                      <div className={estilos.accionesFila}>
                        {/* Editar: precarga el rol en el formulario. */}
                        <button
                          className={estilos.botonAccion}
                          type="button"
                          onClick={() => abrirEditar(rol)}
                        >
                          Editar
                        </button>

                        {/* Activar / desactivar segun estado actual. */}
                        <button
                          className={estilos.botonAccion}
                          type="button"
                          onClick={() => manejarCambiarEstado(rol)}
                        >
                          {activo ? 'Desactivar' : 'Activar'}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  )
}
