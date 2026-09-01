// Seccion Administracion.
//
// Como el enrutado global de la app es plano (App.jsx mapea un id de seccion a
// un componente), Administracion gestiona su PROPIA sub-navegacion interna:
//  - vista 'panel' (por defecto): tarjeta de bienvenida + grid de accesos,
//    imitando el patron de Inicio. Incluye el acceso "Gestion de Usuarios".
//  - vista 'usuarios': enlace "Volver a Administracion" + <GestionUsuarios/>.
//
// Reutiliza el patron visual de tarjetas/accesos (variables CSS de index.css).
import { useState } from 'react'
import GestionUsuarios from './GestionUsuarios.jsx'
import estilos from './Administracion.module.css'

// Accesos del panel de Administracion. `id` identifica la sub-vista destino.
const ACCESOS = [
  {
    id: 'usuarios',
    icono: '\u{1F6E1}\u{FE0F}', // escudo
    titulo: 'Gestión de Usuarios',
    texto: 'Crea usuarios, controla su estado y cambia contraseñas.',
  },
]

export default function Administracion() {
  // Sub-vista interna: 'panel' (por defecto) o 'usuarios'.
  const [vista, setVista] = useState('panel')

  // Vista de usuarios: enlace para volver + gestion de usuarios.
  if (vista === 'usuarios') {
    return (
      <div className={estilos.administracion}>
        <button
          className={estilos.volver}
          type="button"
          onClick={() => setVista('panel')}
        >
          {'\u2190'} Volver a Administración
        </button>

        <GestionUsuarios />
      </div>
    )
  }

  // Vista panel (por defecto): bienvenida + grid de accesos.
  return (
    <div className={estilos.administracion}>
      {/* Tarjeta de bienvenida. */}
      <section className={estilos.tarjeta}>
        <h2 className={estilos.titulo}>Administración</h2>
        <p className={estilos.subtitulo}>
          Gestiona la configuración y los usuarios del sistema desde un solo
          lugar.
        </p>
      </section>

      {/* Tarjeta con los accesos del modulo de administracion. */}
      <section className={estilos.tarjeta}>
        <h3 className={estilos.tituloAccesos}>Accesos</h3>

        <div className={estilos.accesos}>
          {ACCESOS.map((acceso) => (
            <button
              key={acceso.id}
              type="button"
              className={estilos.acceso}
              onClick={() => setVista(acceso.id)}
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
