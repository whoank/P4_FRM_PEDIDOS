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

// Opciones principales del menu. El orden refleja el exigido por el Req. 1.1.
// Los iconos son emojis/unicode simples para no agregar dependencias nuevas.
export const OPCIONES_MENU = [
  { id: 'inicio', etiqueta: 'Inicio', icono: '\u{1F3E0}' },        // casa
  { id: 'clientes', etiqueta: 'Clientes', icono: '\u{1F465}' },    // dos personas
  { id: 'productos', etiqueta: 'Productos', icono: '\u{1F4E6}' },  // caja
  { id: 'pedidos', etiqueta: 'Pedidos', icono: '\u{1F9FE}' },      // recibo
  { id: 'reporte', etiqueta: 'Reporte diario', icono: '\u{1F4CA}' }, // grafico
  { id: 'administracion', etiqueta: 'Administración', icono: '\u{1F6E1}\u{FE0F}' }, // escudo
]

export default function MenuLateral({ seccionActiva, onSeleccionar, onCerrarSesion }) {
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

        {OPCIONES_MENU.map((opcion) => {
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
