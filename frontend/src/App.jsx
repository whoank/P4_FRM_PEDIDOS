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
import MenuLateral, {
  OPCIONES_MENU,
  tienePermisoDeSeccion,
} from './componentes/MenuLateral.jsx'
import Inicio from './secciones/Inicio.jsx'
import Clientes from './secciones/Clientes.jsx'
import Productos from './secciones/Productos.jsx'
import Pedidos from './secciones/Pedidos.jsx'
import ReporteDiario from './secciones/ReporteDiario.jsx'
import Administracion from './secciones/Administracion.jsx'
import BarraUsuario from './componentes/BarraUsuario.jsx'
import { AuthProvider, useAuth } from './auth/AuthContext.jsx'
import Login from './auth/Login.jsx'
import './layout.css'

// Etiqueta legible de cada seccion, para el breadcrumb de la topbar.
const ETIQUETAS_SECCION = OPCIONES_MENU.reduce((acc, opcion) => {
  acc[opcion.id] = opcion.etiqueta
  return acc
}, {})

// Aplicacion autenticada: es EXACTAMENTE la app de antes (layout con
// MenuLateral + topbar + secciones). Solo se le anade el paso de la prop
// `onCerrarSesion` al MenuLateral, conectada al logout del contexto de auth.
function AppAutenticada() {
  // Ademas de logout, tomamos hasPermission para proteger secciones sin permiso.
  const { logout, hasPermission } = useAuth()

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
    administracion: () => <Administracion />,
  }

  // Resuelve el componente de la seccion activa; si no existe, cae en Inicio.
  const renderSeccion = SECCIONES[seccionActiva] || SECCIONES.inicio
  const etiquetaActual = ETIQUETAS_SECCION[seccionActiva] || 'Inicio'

  // Proteccion centralizada: aunque el menu ya oculta las opciones sin permiso,
  // validamos tambien al renderizar para que forzar `seccionActiva` no muestre
  // una seccion restringida. Reutiliza la MISMA regla que el menu
  // (tienePermisoDeSeccion vive en MenuLateral.jsx: unica fuente de verdad).
  // 'inicio' siempre es accesible, por lo que el arranque no se rompe.
  const puedeAcceder = tienePermisoDeSeccion(seccionActiva, hasPermission)

  return (
    <div className="layout">
      {/* Menu lateral: recibe la seccion activa y notifica el cambio (Req. 1).
          Ademas recibe onCerrarSesion, conectada al logout del contexto. */}
      <MenuLateral
        seccionActiva={seccionActiva}
        onSeleccionar={setSeccionActiva}
        onCerrarSesion={logout}
      />

      <div className="contenido">
        {/* Topbar con breadcrumb de la seccion actual en negrita. */}
        <header className="topbar">
          <p className="topbar__breadcrumb">
            <span className="topbar__breadcrumb-prefijo">Gestion de Pedidos &gt; </span>
            {etiquetaActual}
          </p>
        </header>

        {/* Contenedor de la seccion activa. Si el usuario no tiene permiso
            para la seccion, NO se renderiza el componente: se muestra un aviso
            dentro de una tarjeta simple (defensa en profundidad de UX). */}
        <main className="seccion">
          {puedeAcceder ? (
            renderSeccion()
          ) : (
            <section
              style={{
                backgroundColor: 'var(--color-surface)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-card)',
                padding: 'var(--space-5)',
                color: 'var(--color-text-secondary)',
              }}
            >
              No tienes permiso para ver esta sección.
            </section>
          )}
        </main>

        {/* Barra inferior fija al pie del area de contenido: muestra el usuario
            autenticado y su rol. Vive una sola vez en el layout (no en cada
            seccion) y toma el usuario del AuthContext (sin llamar a /auth/me).
            El CSS de .contenido (flex-column) la mantiene abajo sin tapar el
            contenido. */}
        <BarraUsuario />
      </div>
    </div>
  )
}

// Gate de autenticacion: decide que renderizar segun el estado del contexto.
//  - cargando: loader a pantalla completa (evita parpadeo Login/app).
//  - sin usuario: pantalla de Login.
//  - con usuario: la aplicacion actual intacta (AppAutenticada).
function AuthGate() {
  const { usuario, cargando } = useAuth()

  if (cargando) {
    // Loader a pantalla completa, coherente con el estilo de la app.
    return (
      <div className="auth-loader">
        <div className="auth-loader__marca">
          <span aria-hidden="true">{'\u{1F4CB}'}</span>
          <span>Control de Pedidos</span>
        </div>
        <p className="auth-loader__texto">Cargando...</p>
      </div>
    )
  }

  // Sin sesion: mostrar Login. Con sesion: mostrar la app actual.
  return usuario ? <AppAutenticada /> : <Login />
}

// Componente raiz: envuelve todo con el AuthProvider y delega en el gate.
export default function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  )
}
