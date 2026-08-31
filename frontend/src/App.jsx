// Componente raiz de la aplicacion (Tarea 14).
//
// Responsabilidades (Req. 1, 13):
//  - Mantener en estado la seccion activa (useState), con 'inicio' por defecto
//    para mostrar la seccion Inicio al abrir la app (Req. 13.1).
//  - Renderizar el layout general de la guia de estilo: sidebar oscuro fijo a
//    la izquierda (MenuLateral) + area de contenido a la derecha con una topbar
//    (breadcrumb de la seccion actual) y el contenedor de la seccion activa.
//  - Enrutar por estado (sin react-router): un objeto mapea el id de seccion al
//    componente a renderizar.
//
// NOTA: las secciones reales (Inicio, Clientes, Productos, Pedidos,
// ReporteDiario) ya estan implementadas (Tareas 15-19) y quedan conectadas
// aqui. La seccion Inicio recibe `onNavegar` para poder cambiar de seccion
// desde sus accesos directos (Req. 13.2).
//
// Requerimientos: 1.1, 1.2, 1.3, 13.1, 13.2
import { useState } from 'react'
import MenuLateral, { OPCIONES_MENU } from './componentes/MenuLateral.jsx'
import Inicio from './secciones/Inicio.jsx'
import Clientes from './secciones/Clientes.jsx'
import Productos from './secciones/Productos.jsx'
import Pedidos from './secciones/Pedidos.jsx'
import ReporteDiario from './secciones/ReporteDiario.jsx'
import './layout.css'

// Etiqueta legible de cada seccion, para el breadcrumb de la topbar.
const ETIQUETAS_SECCION = OPCIONES_MENU.reduce((acc, opcion) => {
  acc[opcion.id] = opcion.etiqueta
  return acc
}, {})

export default function App() {
  // 'inicio' por defecto: la app muestra la seccion Inicio al abrirse (Req. 13.1).
  const [seccionActiva, setSeccionActiva] = useState('inicio')

  // Enrutado por estado: mapea el id de seccion al componente a renderizar.
  // Se define dentro de App porque Inicio necesita `setSeccionActiva` para
  // navegar desde sus accesos directos (Req. 13.2).
  const SECCIONES = {
    inicio: () => <Inicio onNavegar={setSeccionActiva} />,
    clientes: () => <Clientes />,
    productos: () => <Productos />,
    pedidos: () => <Pedidos />,
    reporte: () => <ReporteDiario />,
  }

  // Resuelve el componente de la seccion activa; si no existe, cae en Inicio.
  const renderSeccion = SECCIONES[seccionActiva] || SECCIONES.inicio
  const etiquetaActual = ETIQUETAS_SECCION[seccionActiva] || 'Inicio'

  return (
    <div className="layout">
      {/* Menu lateral: recibe la seccion activa y notifica el cambio (Req. 1). */}
      <MenuLateral seccionActiva={seccionActiva} onSeleccionar={setSeccionActiva} />

      <div className="contenido">
        {/* Topbar con breadcrumb de la seccion actual en negrita. */}
        <header className="topbar">
          <p className="topbar__breadcrumb">
            <span className="topbar__breadcrumb-prefijo">Gestion de Pedidos &gt; </span>
            {etiquetaActual}
          </p>
        </header>

        {/* Contenedor de la seccion activa. */}
        <main className="seccion">{renderSeccion()}</main>
      </div>
    </div>
  )
}
