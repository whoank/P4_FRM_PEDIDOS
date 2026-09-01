// Pantalla de inicio de sesion.
//
// Reutiliza el sistema visual de la app (tarjeta blanca, inputs con foco de
// acento, boton primario, mensaje de error) sobre un fondo oscuro del sidebar
// a modo de portada. Incluye:
//  - Logo de la app (mismo emoji y texto que el MenuLateral).
//  - Mensaje de bienvenida.
//  - Campo Usuario y campo Contrasena con toggle mostrar/ocultar accesible.
//  - Boton "Iniciar sesion" que se deshabilita mientras procesa.
//  - Mensaje de error GENERICO ("Usuario o contraseña incorrectos.") sin
//    distinguir usuario vs contrasena; tambien muestra errores de conexion.
//
// Al enviar llama al login del AuthContext. Si el login es correcto, el
// AuthProvider guarda el usuario y el gate muestra la app (no navegamos aqui).

import { useState } from 'react'
import { useAuth } from './AuthContext.jsx'
import estilos from './Login.module.css'

function Login() {
  const { login } = useAuth()

  // Campos controlados del formulario.
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  // Toggle mostrar/ocultar contrasena.
  const [mostrarPassword, setMostrarPassword] = useState(false)
  // true mientras se procesa el login (deshabilita el boton).
  const [enviando, setEnviando] = useState(false)
  // Mensaje de error a mostrar (credenciales o conexion).
  const [error, setError] = useState('')

  // Envia el formulario: llama al login del contexto. Si lanza, muestra el
  // mensaje del error. Si es correcto, el gate se encarga de mostrar la app.
  async function manejarEnvio(evento) {
    evento.preventDefault()
    setError('')
    setEnviando(true)
    try {
      await login(username, password)
      // Exito: no hacemos nada mas; el AuthProvider ya seteo el usuario.
    } catch (err) {
      setError(err.message)
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className={estilos.pantalla}>
      <div className={estilos.tarjeta}>
        {/* Logo: mismo emoji y texto que el MenuLateral. */}
        <div className={estilos.marca}>
          <span className={estilos.marcaIcono} aria-hidden="true">
            {'\u{1F4CB}'}
          </span>
          <span>Control de Pedidos</span>
        </div>

        {/* Mensaje de bienvenida. */}
        <p className={estilos.bienvenida}>
          Bienvenido. Inicia sesión para continuar.
        </p>

        <form className={estilos.formulario} onSubmit={manejarEnvio}>
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
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          {/* Campo Contrasena con toggle mostrar/ocultar. */}
          <div className={estilos.campo}>
            <label className={estilos.etiqueta} htmlFor="password">
              Contraseña
            </label>
            <div className={estilos.campoPassword}>
              <input
                className={estilos.input}
                id="password"
                name="password"
                type={mostrarPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              {/* Toggle accesible: button type="button" con aria-label. */}
              <button
                type="button"
                className={estilos.botonToggle}
                onClick={() => setMostrarPassword((v) => !v)}
                aria-label={
                  mostrarPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'
                }
                aria-pressed={mostrarPassword}
              >
                {mostrarPassword ? '\u{1F648}' : '\u{1F441}'}
              </button>
            </div>
          </div>

          {/* Mensaje de error generico (credenciales) o de conexion. */}
          {error && (
            <p className={estilos.error} role="alert">
              {error}
            </p>
          )}

          <button
            className={estilos.botonPrimario}
            type="submit"
            disabled={enviando}
          >
            {enviando ? 'Iniciando sesión...' : 'Iniciar sesión'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default Login
