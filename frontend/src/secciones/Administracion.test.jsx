// Pruebas de la seccion ADMINISTRACION: accesos filtrados por permiso y
// sub-navegacion interna (Roles / Gestion de Usuarios).
//
// Requerimiento cubierto: "el panel de Administracion muestra los accesos
// (Gestion de Usuarios, Roles) segun los permisos del usuario (USUARIOS/ROLES)"
// y "al entrar a Roles se ve la sub-vista con boton Volver".
//
// Estrategia de aislamiento:
//  - Administracion usa useAuth() -> MOCKEAMOS '../auth/AuthContext.jsx' con un
//    hasPermission controlado por un array de permisos por prueba.
//  - Administracion importa GestionUsuarios y Roles (rutas relativas './...').
//    Esos componentes hacen fetch via api.js, asi que los sustituimos por STUBS
//    simples para no arrastrar dependencias de red.
//
// Framework: Vitest + @testing-library/react.

import '@testing-library/jest-dom'
import { render, screen, fireEvent } from '@testing-library/react'

// --- Mock de useAuth (permisos configurables por prueba) ------------------
let permisosDePrueba = []
vi.mock('../auth/AuthContext.jsx', () => ({
  useAuth: () => ({
    usuario: { id: 1, username: 'admin', permissions: permisosDePrueba },
    cargando: false,
    permisos: permisosDePrueba,
    hasPermission: (codigo) => permisosDePrueba.includes(codigo),
    login: async () => {},
    logout: async () => {},
  }),
}))

// --- Stubs de las sub-vistas (rutas relativas desde Administracion) -------
// Se mockean con la MISMA ruta con la que Administracion las importa
// ('./GestionUsuarios.jsx' y './Roles.jsx').
vi.mock('./GestionUsuarios.jsx', () => ({
  default: () => <div>STUB_USUARIOS</div>,
}))
vi.mock('./Roles.jsx', () => ({
  default: () => <div>STUB_ROLES</div>,
}))

// Import del componente DESPUES de declarar los mocks.
import Administracion from './Administracion.jsx'

function renderAdmin(permisos) {
  permisosDePrueba = permisos
  return render(<Administracion />)
}

describe('Administracion: accesos filtrados por permiso', () => {
  it('a) con USUARIOS y ROLES muestra ambos accesos', () => {
    renderAdmin(['USUARIOS', 'ROLES'])
    expect(screen.getByText('Gestión de Usuarios')).toBeInTheDocument()
    expect(screen.getByText('Roles')).toBeInTheDocument()
  })

  it('b) con solo ROLES muestra Roles y NO Gestion de Usuarios', () => {
    renderAdmin(['ROLES'])
    expect(screen.getByText('Roles')).toBeInTheDocument()
    expect(screen.queryByText('Gestión de Usuarios')).not.toBeInTheDocument()
  })

  it('c) con solo USUARIOS muestra Gestion de Usuarios y NO Roles', () => {
    renderAdmin(['USUARIOS'])
    expect(screen.getByText('Gestión de Usuarios')).toBeInTheDocument()
    // "Roles" es el titulo del acceso; sin permiso ROLES no debe aparecer.
    expect(screen.queryByText('Roles')).not.toBeInTheDocument()
  })

  it('d) al hacer clic en el acceso "Roles" se muestra la sub-vista (STUB_ROLES) y el boton Volver', () => {
    renderAdmin(['USUARIOS', 'ROLES'])

    // El acceso "Roles" es un boton con ese titulo dentro.
    fireEvent.click(screen.getByText('Roles'))

    // Se renderiza el stub de Roles y aparece el boton para volver al panel.
    expect(screen.getByText('STUB_ROLES')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Volver a Administración/i }),
    ).toBeInTheDocument()
  })
})
