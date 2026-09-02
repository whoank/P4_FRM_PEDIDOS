// Componente de navegacion lateral (Req. 1).
//
// Muestra la marca de la app, una etiqueta tenue "Menu" y las opciones de
// navegacion (Inicio, Clientes, Productos, Pedidos, Reporte diario). Cada
// opcion es un <button> (focusable por teclado) con un icono a la izquierda y
// su etiqueta. La seccion activa se resalta con fondo primario, texto blanco y
// una barra de acento a la izquierda (el estado NO depende solo del color), y
// se marca con aria-current="page" para accesibilidad.
//
// Recibe por props:
//  - seccionActiva: id de la seccion actualmente seleccionada.
//  - onSeleccionar: callback(id) que se invoca al hacer clic en una opcion.
//  - onCerrarSesion: callback opcional que se invoca al pulsar "Cerrar sesion".
//
// El estilo visual proviene de la seccion "Visual Style" del design.md y usa
// las variables CSS definidas en index.css. Las clases estan en layout.css.
//
// Requerimientos: 1.1, 1.2, 1.3, 13.1

import { useAuth } from '../auth/AuthContext.jsx'

// Opciones principales del menu. El orden refleja el exigido por el Req. 1.1.
// Los iconos son emojis/unicode simples para no agregar dependencias nuevas.
//
// Cada opcion incluye el campo `permission` con el codigo de permiso que la
// habilita. 'inicio' es null (siempre visible: es la landing). El caso de
// 'administracion' es especial (ver puedeVerOpcion mas abajo).
export const OPCIONES_MENU = [
  { id: 'inicio', etiqueta: 'Inicio', icono: '\u{1F3E0}', permission: null },        // casa
  { id: 'clientes', etiqueta: 'Clientes', icono: '\u{1F465}', permission: 'CLIENTES' },    // dos personas
  { id: 'productos', etiqueta: 'Productos', icono: '\u{1F4E6}', permission: 'PRODUCTOS' },  // caja
  { id: 'pedidos', etiqueta: 'Pedidos', icono: '\u{1F9FE}', permission: 'PEDIDOS' },      // recibo
  { id: 'reporte', etiqueta: 'Reporte diario', icono: '\u{1F4CA}', permission: 'REPORTE_DIARIO' }, // grafico
  { id: 'administracion', etiqueta: 'Administración', icono: '\u{1F6E1}\u{FE0F}', permission: 'ADMINISTRACION' }, // escudo
]

// -------------------------------------------------------------------------
// Reglas centralizadas de permisos de navegacion.
//
// ESTE ES EL UNICO LUGAR donde viven las reglas de visibilidad/acceso por
// seccion. Tanto el menu lateral (que oculta opciones) como App.jsx (que
// bloquea el render de una seccion sin permiso) las reutilizan. Asi no se
// duplican condicionales por toda la app.
// -------------------------------------------------------------------------

// Decide si una OPCION del menu debe verse, segun los permisos del usuario.
//  - Opciones con permission === null: siempre visibles (p. ej. Inicio).
//  - Administracion: caso especial. Se muestra si el usuario tiene
//    ADMINISTRACION o alguna subseccion administrativa (USUARIOS o ROLES), para
//    que un usuario con solo ROLES pueda entrar y ver la gestion de Roles.
//  - El resto: visible si tiene el permiso correspondiente.
export function puedeVerOpcion(opcion, hasPermission) {
  if (opcion.id === 'administracion') {
    return (
      hasPermission('ADMINISTRACION') ||
      hasPermission('USUARIOS') ||
      hasPermission('ROLES')
    )
  }
  return opcion.permission === null || hasPermission(opcion.permission)
}

// Version por id de seccion, para que App.jsx valide el acceso sin depender
// del objeto opcion. Coherente con puedeVerOpcion (misma fuente de verdad).
export function tienePermisoDeSeccion(id, hasPermission) {
  const opcion = OPCIONES_MENU.find((o) => o.id === id)
  // Una seccion desconocida no se bloquea aqui (App.jsx cae en Inicio).
  if (!opcion) return true
  return puedeVerOpcion(opcion, hasPermission)
}

export default function MenuLateral({ seccionActiva, onSeleccionar, onCerrarSesion }) {
  // Permisos del usuario autenticado, desde el contexto de auth.
  const { hasPermission } = useAuth()

  // Solo se muestran las opciones permitidas (regla centralizada).
  const opcionesVisibles = OPCIONES_MENU.filter((opcion) =>
    puedeVerOpcion(opcion, hasPermission),
  )

  return (
    <aside className="sidebar" aria-label="Menu lateral">
      {/* Marca: icono + nombre de la app, en la parte superior */}
      <div className="sidebar__marca">
        <span className="sidebar__marca-icono" aria-hidden="true">
          {'\u{1F4CB}'}
        </span>
        <span className="sidebar__marca-texto">Control de Pedidos</span>
      </div>

      {/* Navegacion principal */}
      <nav className="sidebar__nav" aria-label="Secciones">
        {/* Etiqueta tenue de grupo */}
        <p className="sidebar__grupo-label">Menu</p>

        {opcionesVisibles.map((opcion) => {
          const activa = opcion.id === seccionActiva
          return (
            <button
              key={opcion.id}
              type="button"
              className={
                'sidebar__item' + (activa ? ' sidebar__item--activo' : '')
              }
              // Indicador accesible de la seccion activa (no solo por color).
              aria-current={activa ? 'page' : undefined}
              onClick={() => onSeleccionar(opcion.id)}
            >
              <span className="sidebar__item-icono" aria-hidden="true">
                {opcion.icono}
              </span>
              <span className="sidebar__item-texto">{opcion.etiqueta}</span>
            </button>
          )
        })}
      </nav>

      {/* "Soporte": opcion cosmetica anclada al pie, separada del grupo
          principal. No navega a una seccion funcional; solo mantiene la
          coherencia visual con la referencia de diseno. */}
      <div className="sidebar__pie">
        <button
          type="button"
          className="sidebar__item"
          onClick={() => onSeleccionar('inicio')}
        >
          <span className="sidebar__item-icono" aria-hidden="true">
            {'\u{1F6DF}'}
          </span>
          <span className="sidebar__item-texto">Soporte</span>
        </button>

        {/* "Cerrar sesion": invoca el callback del contexto de auth (si se
            provee). El AuthProvider pondra usuario=null y el gate volvera al
            Login automaticamente. */}
        <button
          type="button"
          className="sidebar__item"
          onClick={() => onCerrarSesion?.()}
        >
          <span className="sidebar__item-icono" aria-hidden="true">
            {'\u{1F6AA}'}
          </span>
          <span className="sidebar__item-texto">Cerrar sesión</span>
        </button>
      </div>
    </aside>
  )
}
