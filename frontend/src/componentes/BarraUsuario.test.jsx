// Pruebas de la BarraUsuario: muestra usuario y rol del usuario autenticado,
// texto de respaldo si no tiene rol, se oculta sin sesion, desaparece tras
// logout y NO hace ninguna llamada a /auth/me (usa solo el AuthContext).
//
// Estrategia de aislamiento: BarraUsuario consume useAuth() de
// '../auth/AuthContext.jsx'. Envolver con el AuthProvider real dispararia un
// fetch a /auth/me; por eso MOCKEAMOS useAuth y le inyectamos un `usuario`
// controlado por prueba. Ademas espiamos global.fetch para demostrar que la
// barra NO realiza peticiones de red.
//
// Framework: Vitest + @testing-library/react (jsdom + globals via vite.config).

import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'

// --- Mock de useAuth ------------------------------------------------------
// Contenedor mutable para configurar el `usuario` devuelto por cada prueba.
let usuarioDePrueba = null
vi.mock('../auth/AuthContext.jsx', () => ({
  useAuth: () => ({
    usuario: usuarioDePrueba,
    cargando: false,
    permisos: usuarioDePrueba?.permissions ?? [],
    hasPermission: () => false,
    login: async () => {},
    logout: async () => {},
  }),
}))

// Import del componente DESPUES del mock.
import BarraUsuario from './BarraUsuario.jsx'

describe('BarraUsuario', () => {
  beforeEach(() => {
    usuarioDePrueba = null
    vi.restoreAllMocks()
  })

  it('usuario autenticado: muestra el username y el rol', () => {
    usuarioDePrueba = {
      id: 1,
      username: 'juan.perez',
      active: true,
      role: { id: 2, nombre: 'Operador' },
      permissions: ['CLIENTES'],
    }
    render(<BarraUsuario />)

    // El username y el rol aparecen en la barra.
    expect(screen.getByText('juan.perez')).toBeInTheDocument()
    expect(screen.getByText('Operador')).toBeInTheDocument()
    // Es un <footer> (HTML semantico -> role "contentinfo").
    expect(screen.getByRole('contentinfo')).toBeInTheDocument()
  })

  it('usuario Administrador: muestra el rol Administrador', () => {
    usuarioDePrueba = {
      id: 1,
      username: 'admin',
      active: true,
      role: { id: 1, nombre: 'Administrador' },
      permissions: [],
    }
    render(<BarraUsuario />)

    expect(screen.getByText('admin')).toBeInTheDocument()
    expect(screen.getByText('Administrador')).toBeInTheDocument()
  })

  it('usuario sin rol: muestra "Sin rol asignado"', () => {
    usuarioDePrueba = {
      id: 3,
      username: 'juan.perez',
      active: true,
      role: null,
      permissions: [],
    }
    render(<BarraUsuario />)

    expect(screen.getByText('juan.perez')).toBeInTheDocument()
    expect(screen.getByText('Sin rol asignado')).toBeInTheDocument()
  })

  it('usuario no autenticado: la barra no se muestra', () => {
    usuarioDePrueba = null
    const { container } = render(<BarraUsuario />)

    // No renderiza nada (return null) -> sin footer.
    expect(screen.queryByRole('contentinfo')).not.toBeInTheDocument()
    expect(container).toBeEmptyDOMElement()
  })

  it('logout: al quedar el usuario en null, la informacion desaparece', () => {
    // Primero autenticado.
    usuarioDePrueba = {
      id: 1,
      username: 'admin',
      active: true,
      role: { id: 1, nombre: 'Administrador' },
      permissions: [],
    }
    const { rerender } = render(<BarraUsuario />)
    expect(screen.getByText('admin')).toBeInTheDocument()

    // Simula el logout: el contexto pasa usuario a null y se re-renderiza.
    usuarioDePrueba = null
    rerender(<BarraUsuario />)

    expect(screen.queryByText('admin')).not.toBeInTheDocument()
    expect(screen.queryByRole('contentinfo')).not.toBeInTheDocument()
  })

  it('no realiza ninguna llamada de red (no llama a /auth/me)', () => {
    // Espiamos fetch: la barra usa el AuthContext, no debe hacer peticiones.
    const espiaFetch = vi.fn()
    vi.stubGlobal('fetch', espiaFetch)

    usuarioDePrueba = {
      id: 1,
      username: 'admin',
      active: true,
      role: { id: 1, nombre: 'Administrador' },
      permissions: [],
    }
    render(<BarraUsuario />)

    expect(espiaFetch).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
})
