// Contexto de autenticacion de la app.
//
// Centraliza el estado de sesion (usuario autenticado) y las acciones de
// login/logout. La sesion vive en una cookie HttpOnly del backend; aqui solo
// guardamos en memoria el objeto usuario que devuelve el servidor (nunca la
// contrasena ni tokens).
//
// Estado expuesto:
//  - usuario:  objeto {id, username, active} si hay sesion; null si no.
//  - cargando: true mientras se verifica la sesion inicial (evita parpadeos).
//  - login(username, password): inicia sesion y guarda el usuario.
//  - logout(): cierra la sesion y limpia el usuario.

import { createContext, useContext, useEffect, useState } from 'react'
import * as authService from './authService.js'

// Contexto con valores por defecto (se sobreescriben por el Provider).
const AuthContext = createContext({
  usuario: null,
  cargando: true,
  login: async () => {},
  logout: async () => {},
})

export function AuthProvider({ children }) {
  // Usuario autenticado (o null). Inicia en null hasta verificar la sesion.
  const [usuario, setUsuario] = useState(null)
  // `cargando` arranca en true: aun no sabemos si hay sesion. El gate muestra
  // un loader mientras tanto para no parpadear entre Login y app.
  const [cargando, setCargando] = useState(true)

  // Al montar, verificamos la sesion existente (GET /auth/me via cookie).
  useEffect(() => {
    let activo = true // evita setState si el componente se desmonta antes
    async function verificarSesion() {
      try {
        const sesion = await authService.obtenerSesion()
        if (activo && sesion) {
          setUsuario(sesion)
        }
      } finally {
        // Pase lo que pase, terminamos la carga inicial.
        if (activo) {
          setCargando(false)
        }
      }
    }
    verificarSesion()
    return () => {
      activo = false
    }
  }, [])

  // Inicia sesion. DECISION documentada: RELANZAMOS el error para que el
  // formulario Login pueda mostrar el mensaje (credenciales/conexion). Si el
  // login es correcto, guardamos el usuario y el gate mostrara la app.
  async function login(username, password) {
    const usuarioAutenticado = await authService.login(username, password)
    setUsuario(usuarioAutenticado)
    return usuarioAutenticado
  }

  // Cierra la sesion en el backend y limpia el usuario local. El gate volvera
  // al Login automaticamente al quedar usuario en null.
  async function logout() {
    await authService.logout()
    setUsuario(null)
  }

  const valor = { usuario, cargando, login, logout }

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

// Hook de comodidad para consumir el contexto de autenticacion.
export function useAuth() {
  return useContext(AuthContext)
}

export default AuthContext
