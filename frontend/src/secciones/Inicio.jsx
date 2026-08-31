// Seccion Inicio (Tarea 15).
//
// Responsabilidades (Req. 13.1, 13.2):
//  - Mostrar una vista general de bienvenida dentro de tarjetas blancas.
//  - Ofrecer accesos directos a las secciones Clientes, Productos, Pedidos y
//    Reporte diario (Req. 13.2).
//
// Desacople de App.jsx (concurrencia): este componente NO conoce el enrutado.
// Recibe por prop un callback `onNavegar(idSeccion)` que invoca al hacer clic en
// cada acceso directo. El orquestador conectara ese callback desde App.jsx.
// Si la prop no se provee, los accesos no rompen: se usa la guarda onNavegar?.(...).
//
// Los ids usados coinciden con los del enrutado por estado de App.jsx:
//   'clientes', 'productos', 'pedidos', 'reporte'.
//
// Requerimientos: 13.1, 13.2
import estilos from './Inicio.module.css'

// Definicion declarativa de los accesos directos.
// `id` debe coincidir con el id de seccion que espera App.jsx.
const ACCESOS = [
  {
    id: 'clientes',
    icono: '👥',
    titulo: 'Clientes',
    texto: 'Registra y consulta los datos de tus clientes.',
  },
  {
    id: 'productos',
    icono: '🍔',
    titulo: 'Productos',
    texto: 'Administra el catalogo, precios y disponibilidad.',
  },
  {
    id: 'pedidos',
    icono: '🧾',
    titulo: 'Pedidos',
    texto: 'Crea pedidos y actualiza su estado.',
  },
  {
    id: 'reporte',
    icono: '📊',
    titulo: 'Reporte diario',
    texto: 'Consulta las ventas y los pedidos del dia.',
  },
]

// `onNavegar` es opcional: se invoca con el id de la seccion destino al hacer
// clic en un acceso directo. La guarda `?.` evita errores si no se provee.
export default function Inicio({ onNavegar }) {
  return (
    <div className={estilos.inicio}>
      {/* Tarjeta de bienvenida: vista general al abrir la app. */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.titulo}>Bienvenido a Control de Pedidos</h2>
        <p className={estilos.subtitulo}>
          Administra tus clientes, productos y pedidos desde un solo lugar, y
          consulta el resumen de ventas del dia.
        </p>
      </section>

      {/* Tarjeta con los accesos directos a las demas secciones (Req. 13.2). */}
      <section className={estilos.tarjeta}>
        <h3 className={estilos.tituloAccesos}>Accesos directos</h3>

        <div className={estilos.accesos}>
          {ACCESOS.map((acceso) => (
            <button
              key={acceso.id}
              type="button"
              className={estilos.acceso}
              // Guarda onNavegar?.(...): si la prop no llega, no rompe.
              onClick={() => onNavegar?.(acceso.id)}
            >
              <span className={estilos.accesoIcono} aria-hidden="true">
                {acceso.icono}
              </span>
              <span className={estilos.accesoTitulo}>{acceso.titulo}</span>
              <p className={estilos.accesoTexto}>{acceso.texto}</p>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
