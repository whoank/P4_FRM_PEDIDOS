// Contexto de autenticacion de la app.
//
// Centraliza el estado de sesion (usuario autenticado) y las acciones de
// login/logout. La sesion vive en una cookie HttpOnly del backend; aqui solo
// guardamos en memoria el objeto usuario que devuelve el servidor (nunca la
// contrasena ni tokens).
//
// Estado expuesto:
//  - usuario:  objeto de sesion si hay sesion; null si no. AHORA incluye
//    ademas de {id, username, active} los campos `role` ({id, nombre} | null)
//    y `permissions` (array de codigos de permiso, p. ej. ["CLIENTES","ROLES"]).
//  - cargando: true mientras se verifica la sesion inicial (evita parpadeos).
//  - permisos:  array de codigos de permiso derivado de usuario.permissions
//    (vacio si no hay sesion). Se usa SOLO para UX/navegacion; la seguridad
//    real la aplica el backend con require_permission.
//  - hasPermission(codigo): funcion que indica si el usuario tiene ese permiso.
//  - login(username, password): inicia sesion y guarda el usuario.
//  - logout(): cierra la sesion y limpia el usuario.

import { createContext, useContext, useEffect, useState } from 'react'
import * as authService from './authService.js'

// Contexto con valores por defecto (se sobreescriben por el Provider).
const AuthContext = createContext({
  usuario: null,
  cargando: true,
  permisos: [],
  hasPermission: () => false,
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

  // Lista de permisos del usuario, derivada del objeto de sesion. Si no hay
  // sesion (o el backend no envio permisos), queda como array vacio.
  const permisos = usuario?.permissions ?? []

  // Indica si el usuario tiene un permiso concreto por su codigo.
  // Se usa para mostrar/ocultar y bloquear secciones (defensa en profundidad
  // de UX); la autorizacion real vive en el backend.
  const hasPermission = (codigo) => permisos.includes(codigo)

  const valor = { usuario, cargando, permisos, hasPermission, login, logout }

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>
}

// Hook de comodidad para consumir el contexto de autenticacion.
export function useAuth() {
  return useContext(AuthContext)
}

export default AuthContext
