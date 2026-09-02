// Barra inferior que muestra el usuario autenticado y su rol.
//
// Fuente de datos UNICA: el contexto de autenticacion (useAuth). NO hace
// ninguna llamada a /auth/me: reutiliza el `usuario` que AuthContext ya tiene
// en memoria (poblado al montar via /auth/me y en el login). Asi se evita
// duplicar peticiones al backend.
//
// Solo se muestra cuando hay un usuario autenticado; si no hay usuario
// devuelve null (defensa, aunque en la practica solo se renderiza dentro de la
// app autenticada). Al cerrar sesion, el usuario del contexto pasa a null y la
// barra desaparece sin logica de logout propia.
//
// Muestra: "Usuario: <username>  |  Rol: <rol>". Si el usuario no tiene rol,
// muestra "Sin rol asignado".

import { useAuth } from '../auth/AuthContext.jsx'
import estilos from './BarraUsuario.module.css'

export default function BarraUsuario() {
  const { usuario } = useAuth()

  // Sin usuario autenticado no se muestra nada (evita "undefined" y la barra
  // en la pantalla de login).
  if (!usuario) {
    return null
  }

  // Nombre del rol o texto de respaldo si el usuario no tiene rol asignado.
  const nombreRol = usuario.role?.nombre ?? 'Sin rol asignado'

  return (
    <footer className={estilos.barra}>
      {/* Icono de usuario (emoji unicode, sin librerias nuevas). Decorativo:
          la informacion tambien va en texto, no depende solo del icono. */}
      <span className={estilos.dato}>
        <span className={estilos.icono} aria-hidden="true">
          {'\u{1F464}'}
        </span>
        <span>
          <span className={estilos.etiqueta}>Usuario: </span>
          {usuario.username}
        </span>
      </span>

      {/* Separador visual (oculto a lectores de pantalla; el layout ya separa
          los dos datos en pantallas estrechas). */}
      <span className={estilos.separador} aria-hidden="true">
        |
      </span>

      <span className={estilos.dato}>
        <span className={estilos.etiqueta}>Rol: </span>
        {nombreRol}
      </span>
    </footer>
  )
}
