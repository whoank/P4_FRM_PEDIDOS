// Seccion Gestion de Usuarios (Administracion > Gestion de Usuarios).
//
// Reutiliza el patron visual de la app (tarjetas, tabla, formularios y
// mensajes) igual que la seccion Clientes. Toda la comunicacion con el backend
// pasa por las funciones de src/api.js (no se usa fetch directo).
//
// Funcionalidad:
//  - Al montar, carga la lista de usuarios con listarUsuarios() (useEffect).
//  - Tabla con ID, Usuario, Estado (Activo/Inactivo), Fecha de creacion,
//    Ultimo acceso y Acciones.
//  - Formulario para crear usuario (username + contrasena + confirmacion) con
//    validacion de coincidencia en cliente y en backend.
//  - Por fila: dar de alta/baja segun estado y cambiar contrasena (form inline).
//  - Mensajes de exito (acento) y error (rojo, role="alert") diferenciados.
//  - Nunca muestra password_hash: el backend no lo envia.
//
// El componente se autogestiona: no recibe props obligatorias.
import { useEffect, useState } from 'react'
import {
  listarUsuarios,
  crearUsuario,
  activarUsuario,
  desactivarUsuario,
  cambiarPasswordUsuario,
  listarRoles,
  asignarRolUsuario,
} from '../api.js'
import estilos from './GestionUsuarios.module.css'

// Estado inicial vacio del formulario de creacion (campos controlados).
// `role_id` como cadena vacia representa "(sin rol)".
const FORM_CREAR_VACIO = {
  username: '',
  password: '',
  password_confirmacion: '',
  role_id: '',
}

// Estado inicial vacio del formulario de cambio de contrasena.
const FORM_PASSWORD_VACIO = { password: '', password_confirmacion: '' }

// Formatea una fecha ISO (o null) a texto legible en es-MX.
// Si el valor es null/undefined o invalido, devuelve un guion.
function formatearFecha(valor) {
  if (!valor) return '\u2014' // em dash "—"
  const fecha = new Date(valor)
  if (Number.isNaN(fecha.getTime())) return '\u2014'
  return fecha.toLocaleString('es-MX')
}

function GestionUsuarios() {
  // Lista de usuarios cargada desde el backend.
  const [usuarios, setUsuarios] = useState([])
  // Roles ACTIVOS disponibles para asignar (poblar los <select> de rol).
  const [rolesActivos, setRolesActivos] = useState([])
  // Controla si el formulario de creacion esta visible.
  const [mostrarCrear, setMostrarCrear] = useState(false)
  // Valores actuales del formulario de creacion.
  const [formCrear, setFormCrear] = useState(FORM_CREAR_VACIO)
  // Mensaje de error del formulario de creacion (rojo).
  const [errorCrear, setErrorCrear] = useState('')

  // Mensajes globales de la seccion (por ejemplo, error al cargar la lista).
  const [errorLista, setErrorLista] = useState('')
  // Mensaje de exito global (verde/acento) tras crear o cambiar contrasena.
  const [exito, setExito] = useState('')

  // id del usuario cuyo formulario de cambio de contrasena esta abierto; null
  // significa que no hay ninguno abierto.
  const [passwordAbiertoId, setPasswordAbiertoId] = useState(null)
  // Valores del formulario de cambio de contrasena.
  const [formPassword, setFormPassword] = useState(FORM_PASSWORD_VACIO)
  // Mensaje de error del formulario de cambio de contrasena (rojo).
  const [errorPassword, setErrorPassword] = useState('')

  // id del usuario cuyo formulario inline de cambio de rol esta abierto; null
  // significa que no hay ninguno abierto.
  const [rolAbiertoId, setRolAbiertoId] = useState(null)
  // Valor (role_id como cadena) del select de cambio de rol.
  const [formRol, setFormRol] = useState('')
  // Mensaje de error del formulario inline de cambio de rol (rojo).
  const [errorRol, setErrorRol] = useState('')

  // Carga la lista de usuarios desde el backend y la guarda en estado.
  async function cargarUsuarios() {
    try {
      const datos = await listarUsuarios()
      setUsuarios(datos || [])
      setErrorLista('')
    } catch (err) {
      setErrorLista(err.message)
    }
  }

  // Carga los roles ACTIVOS desde el backend (para los selects de rol).
  // Si el usuario no tuviera permiso ROLES el backend responderia 403; en ese
  // caso simplemente se deja la lista de roles vacia (el select mostrara solo
  // "(sin rol)") sin romper la gestion de usuarios.
  async function cargarRolesActivos() {
    try {
      const datos = await listarRoles()
      setRolesActivos((datos || []).filter((rol) => rol.activo === true))
    } catch (err) {
      setRolesActivos([])
    }
  }

  // Al montar, carga usuarios y roles activos una sola vez.
  useEffect(() => {
    cargarUsuarios()
    cargarRolesActivos()
  }, [])

  // --- Formulario de creacion -------------------------------------------

  // Actualiza un campo del formulario de creacion mientras el usuario escribe.
  function manejarCambioCrear(evento) {
    const { name, value } = evento.target
    setFormCrear((anterior) => ({ ...anterior, [name]: value }))
  }

  // Abre el formulario de creacion (limpia estado previo).
  function abrirCrear() {
    setFormCrear(FORM_CREAR_VACIO)
    setErrorCrear('')
    setExito('')
    setMostrarCrear(true)
  }

  // Cierra el formulario de creacion y limpia los campos (no persiste nada).
  function cancelarCrear() {
    setMostrarCrear(false)
    setFormCrear(FORM_CREAR_VACIO)
    setErrorCrear('')
  }

  // Envia el formulario de creacion. Valida coincidencia de contrasenas en
  // cliente (sin llamar al backend si no coinciden); ante exito limpia el form,
  // refresca la lista y muestra mensaje; ante error conserva lo ingresado.
  async function manejarEnvioCrear(evento) {
    evento.preventDefault()
    setErrorCrear('')
    setExito('')

    // Validacion minima en cliente: las contrasenas deben coincidir. El
    // backend tambien valida, pero evitamos una llamada innecesaria.
    if (formCrear.password !== formCrear.password_confirmacion) {
      setErrorCrear('Las contraseñas no coinciden.')
      return
    }

    try {
      await crearUsuario({
        username: formCrear.username,
        password: formCrear.password,
        password_confirmacion: formCrear.password_confirmacion,
        // role_id es opcional: si se eligio "(sin rol)" (cadena vacia) se envia
        // null; si se eligio un rol, se convierte a numero.
        role_id: formCrear.role_id ? Number(formCrear.role_id) : null,
      })
      // Exito: limpiar formulario, cerrarlo, refrescar lista y avisar.
      setFormCrear(FORM_CREAR_VACIO)
      setMostrarCrear(false)
      setExito('Usuario creado.')
      await cargarUsuarios()
    } catch (err) {
      // Error: conservar lo ingresado y mostrar el mensaje del backend.
      setErrorCrear(err.message)
    }
  }

  // --- Acciones de alta / baja ------------------------------------------

  // Da de baja (desactiva) un usuario y refresca la lista.
  async function manejarDarDeBaja(id) {
    setExito('')
    setErrorLista('')
    try {
      await desactivarUsuario(id)
      await cargarUsuarios()
    } catch (err) {
      setErrorLista(err.message)
    }
  }

  // Da de alta (activa) un usuario y refresca la lista.
  async function manejarDarDeAlta(id) {
    setExito('')
    setErrorLista('')
    try {
      await activarUsuario(id)
      await cargarUsuarios()
    } catch (err) {
      setErrorLista(err.message)
    }
  }

  // --- Formulario de cambio de contrasena -------------------------------

  // Abre el formulario de cambio de contrasena para un usuario concreto.
  function abrirPassword(id) {
    setPasswordAbiertoId(id)
    setFormPassword(FORM_PASSWORD_VACIO)
    setErrorPassword('')
    setExito('')
  }

  // Cierra el formulario de cambio de contrasena y limpia sus campos.
  function cancelarPassword() {
    setPasswordAbiertoId(null)
    setFormPassword(FORM_PASSWORD_VACIO)
    setErrorPassword('')
  }

  // Actualiza un campo del formulario de contrasena mientras se escribe.
  function manejarCambioPassword(evento) {
    const { name, value } = evento.target
    setFormPassword((anterior) => ({ ...anterior, [name]: value }))
  }

  // Envia el cambio de contrasena. Valida coincidencia en cliente y llama al
  // backend; ante exito cierra el form y avisa; ante error muestra el mensaje.
  async function manejarEnvioPassword(evento, id) {
    evento.preventDefault()
    setErrorPassword('')
    setExito('')

    if (formPassword.password !== formPassword.password_confirmacion) {
      setErrorPassword('Las contraseñas no coinciden.')
      return
    }

    try {
      await cambiarPasswordUsuario(id, {
        password: formPassword.password,
        password_confirmacion: formPassword.password_confirmacion,
      })
      // Exito: cerrar formulario, limpiar campos y avisar.
      setPasswordAbiertoId(null)
      setFormPassword(FORM_PASSWORD_VACIO)
      setExito('Contraseña actualizada.')
    } catch (err) {
      setErrorPassword(err.message)
    }
  }

  // --- Formulario inline de cambio de rol -------------------------------

  // Abre el select inline de cambio de rol para un usuario, precargando su rol
  // actual (o cadena vacia si no tiene).
  function abrirRol(usuario) {
    setRolAbiertoId(usuario.id)
    setFormRol(usuario.role_id != null ? String(usuario.role_id) : '')
    setErrorRol('')
    setExito('')
  }

  // Cierra el select inline de cambio de rol.
  function cancelarRol() {
    setRolAbiertoId(null)
    setFormRol('')
    setErrorRol('')
  }

  // Envia el cambio de rol. Llama a asignarRolUsuario; ante exito refresca la
  // lista y avisa; ante error (p. ej. rol inactivo) muestra el mensaje.
  async function manejarEnvioRol(evento, id) {
    evento.preventDefault()
    setErrorRol('')
    setExito('')

    try {
      await asignarRolUsuario(id, formRol ? Number(formRol) : null)
      setRolAbiertoId(null)
      setFormRol('')
      setExito('Rol actualizado.')
      await cargarUsuarios()
    } catch (err) {
      setErrorRol(err.message)
    }
  }

  return (
    <div className={estilos.usuarios}>
      {/* Tarjeta del formulario de creacion (desplegable). */}
      <section className={estilos.tarjeta}>
        <div className={estilos.cabeceraTarjeta}>
          <h2 className={estilos.tituloTarjeta}>Usuarios</h2>
          {!mostrarCrear && (
            <button
              className={estilos.botonPrimario}
              type="button"
              onClick={abrirCrear}
            >
              Crear usuario
            </button>
          )}
        </div>

        {mostrarCrear && (
          <form className={estilos.formulario} onSubmit={manejarEnvioCrear}>
            {/* Campo Usuario. */}
            <div className={estilos.campo}>
              <label className={estilos.etiqueta} htmlFor="username">
                Usuario
              </label>
              <input
                className={estilos.input}
                id="username"
                name="username"
                type="text"
                value={formCrear.username}
                onChange={manejarCambioCrear}
              />
            </div>

            {/* Campo Contrasena. */}
            <div className={estilos.campo}>
              <label className={estilos.etiqueta} htmlFor="password">
                Contraseña
              </label>
              <input
                className={estilos.input}
                id="password"
                name="password"
                type="password"
                value={formCrear.password}
                onChange={manejarCambioCrear}
              />
            </div>

            {/* Campo Confirmar contrasena. */}
            <div className={estilos.campo}>
              <label
                className={estilos.etiqueta}
                htmlFor="password_confirmacion"
              >
                Confirmar contraseña
              </label>
              <input
                className={estilos.input}
                id="password_confirmacion"
                name="password_confirmacion"
                type="password"
                value={formCrear.password_confirmacion}
                onChange={manejarCambioCrear}
              />
            </div>

            {/* Campo Rol (opcional): select con los roles activos. */}
            <div className={estilos.campo}>
              <label className={estilos.etiqueta} htmlFor="role_id">
                Rol
              </label>
              <select
                className={estilos.input}
                id="role_id"
                name="role_id"
                value={formCrear.role_id}
                onChange={manejarCambioCrear}
              >
                <option value="">(sin rol)</option>
                {rolesActivos.map((rol) => (
                  <option key={rol.id} value={rol.id}>
                    {rol.nombre}
                  </option>
                ))}
              </select>
            </div>

            {/* Mensaje de error de validacion / conexion / duplicado. */}
            {errorCrear && (
              <p className={estilos.error} role="alert">
                {errorCrear}
              </p>
            )}

            <div className={estilos.acciones}>
              <button className={estilos.botonPrimario} type="submit">
                Guardar
              </button>
              <button
                className={estilos.botonSecundario}
                type="button"
                onClick={cancelarCrear}
              >
                Cancelar
              </button>
            </div>
          </form>
        )}

        {/* Mensaje de exito global (verde/acento) tras crear o cambiar pass. */}
        {exito && <p className={estilos.exito}>{exito}</p>}
      </section>

      {/* Tarjeta con la lista de usuarios registrados. */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.tituloTarjeta}>Usuarios registrados</h2>

        {/* Error al cargar / operar sobre la lista. */}
        {errorLista && (
          <p className={estilos.error} role="alert">
            {errorLista}
          </p>
        )}

        {usuarios.length === 0 ? (
          // Mensaje cuando no hay usuarios.
          <p className={estilos.vacio}>No hay usuarios registrados.</p>
        ) : (
          <table className={estilos.tabla}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Usuario</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Fecha de creación</th>
                <th>Último acceso</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {usuarios.map((usuario) => {
                const activo = usuario.active === true
                const passwordAbierto = passwordAbiertoId === usuario.id
                const rolAbierto = rolAbiertoId === usuario.id
                return (
                  <tr key={usuario.id}>
                    <td>{usuario.id}</td>
                    <td>{usuario.username}</td>
                    {/* Rol asignado (o guion si no tiene). */}
                    <td>{usuario.role_nombre || '\u2014'}</td>
                    <td>
                      {/* Badge de estado: color + texto (no solo color). */}
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
                    <td>{formatearFecha(usuario.created_at)}</td>
                    <td>{formatearFecha(usuario.last_login)}</td>
                    <td>
                      <div className={estilos.accionesFila}>
                        {/* Alta / baja segun estado actual. */}
                        {activo ? (
                          <button
                            className={estilos.botonAccion}
                            type="button"
                            onClick={() => manejarDarDeBaja(usuario.id)}
                          >
                            Dar de baja
                          </button>
                        ) : (
                          <button
                            className={estilos.botonAccion}
                            type="button"
                            onClick={() => manejarDarDeAlta(usuario.id)}
                          >
                            Dar de alta
                          </button>
                        )}

                        {/* Abrir formulario de cambio de contrasena. */}
                        <button
                          className={estilos.botonAccion}
                          type="button"
                          onClick={() => abrirPassword(usuario.id)}
                        >
                          Cambiar contraseña
                        </button>

                        {/* Abrir select inline de cambio de rol. */}
                        <button
                          className={estilos.botonAccion}
                          type="button"
                          onClick={() => abrirRol(usuario)}
                        >
                          Cambiar rol
                        </button>
                      </div>

                      {/* Formulario inline de cambio de contrasena. */}
                      {passwordAbierto && (
                        <form
                          className={estilos.formularioInline}
                          onSubmit={(evento) =>
                            manejarEnvioPassword(evento, usuario.id)
                          }
                        >
                          <div className={estilos.campo}>
                            <label
                              className={estilos.etiqueta}
                              htmlFor={`password-nueva-${usuario.id}`}
                            >
                              Nueva contraseña
                            </label>
                            <input
                              className={estilos.input}
                              id={`password-nueva-${usuario.id}`}
                              name="password"
                              type="password"
                              value={formPassword.password}
                              onChange={manejarCambioPassword}
                            />
                          </div>

                          <div className={estilos.campo}>
                            <label
                              className={estilos.etiqueta}
                              htmlFor={`password-confirmar-${usuario.id}`}
                            >
                              Confirmar nueva contraseña
                            </label>
                            <input
                              className={estilos.input}
                              id={`password-confirmar-${usuario.id}`}
                              name="password_confirmacion"
                              type="password"
                              value={formPassword.password_confirmacion}
                              onChange={manejarCambioPassword}
                            />
                          </div>

                          {errorPassword && (
                            <p className={estilos.error} role="alert">
                              {errorPassword}
                            </p>
                          )}

                          <div className={estilos.acciones}>
                            <button
                              className={estilos.botonPrimario}
                              type="submit"
                            >
                              Guardar
                            </button>
                            <button
                              className={estilos.botonSecundario}
                              type="button"
                              onClick={cancelarPassword}
                            >
                              Cancelar
                            </button>
                          </div>
                        </form>
                      )}

                      {/* Formulario inline de cambio de rol. */}
                      {rolAbierto && (
                        <form
                          className={estilos.formularioInline}
                          onSubmit={(evento) =>
                            manejarEnvioRol(evento, usuario.id)
                          }
                        >
                          <div className={estilos.campo}>
                            <label
                              className={estilos.etiqueta}
                              htmlFor={`rol-${usuario.id}`}
                            >
                              Rol
                            </label>
                            <select
                              className={estilos.input}
                              id={`rol-${usuario.id}`}
                              value={formRol}
                              onChange={(evento) =>
                                setFormRol(evento.target.value)
                              }
                            >
                              <option value="">(sin rol)</option>
                              {rolesActivos.map((rol) => (
                                <option key={rol.id} value={rol.id}>
                                  {rol.nombre}
                                </option>
                              ))}
                            </select>
                          </div>

                          {errorRol && (
                            <p className={estilos.error} role="alert">
                              {errorRol}
                            </p>
                          )}

                          <div className={estilos.acciones}>
                            <button
                              className={estilos.botonPrimario}
                              type="submit"
                            >
                              Guardar
                            </button>
                            <button
                              className={estilos.botonSecundario}
                              type="button"
                              onClick={cancelarRol}
                            >
                              Cancelar
                            </button>
                          </div>
                        </form>
                      )}
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

export default GestionUsuarios
