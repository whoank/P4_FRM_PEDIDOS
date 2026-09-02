// Pruebas del MENU LATERAL filtrado por permisos (Roles y Permisos por opcion).
//
// Requerimiento cubierto: "el menu solo muestra las opciones para las que el
// usuario tiene permiso" y la regla especial de Administracion
// (visible si ADMINISTRACION || USUARIOS || ROLES).
//
// Estrategia de aislamiento:
//  - MenuLateral usa useAuth() internamente (de '../auth/AuthContext.jsx') para
//    obtener hasPermission. Envolver con el AuthProvider real haria un fetch a
//    /auth/me, por eso MOCKEAMOS useAuth y le inyectamos un hasPermission
//    controlado por un array de permisos de prueba.
//  - Las funciones puras exportadas por el propio MenuLateral
//    (puedeVerOpcion, tienePermisoDeSeccion, OPCIONES_MENU) NO dependen de
//    useAuth, asi que se prueban importandolas directamente.
//
// Framework: Vitest + @testing-library/react (jsdom + globals via vite.config.js).

import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'

// --- Mock de useAuth ------------------------------------------------------
// vi.mock se "iza" (hoisting) al inicio del modulo. Exponemos un contenedor
// mutable (permisosDePrueba) para configurar los permisos por prueba sin tener
// que re-mockear. hasPermission = (codigo) => permisosDePrueba.includes(codigo),
// igual que el AuthContext real.
let permisosDePrueba = []
vi.mock('../auth/AuthContext.jsx', () => ({
  // Solo necesitamos useAuth para el render del componente.
  useAuth: () => ({
    usuario: { id: 1, username: 'test', permissions: permisosDePrueba },
    cargando: false,
    permisos: permisosDePrueba,
    hasPermission: (codigo) => permisosDePrueba.includes(codigo),
    login: async () => {},
    logout: async () => {},
  }),
}))

// Import del componente y de las funciones puras DESPUES del mock. El default
// (MenuLateral) usa useAuth (ya mockeado); las funciones puras no.
import MenuLateral, {
  puedeVerOpcion,
  tienePermisoDeSeccion,
  OPCIONES_MENU,
} from './MenuLateral.jsx'

// Helper: renderiza el menu con permisos concretos.
function renderMenu(permisos) {
  permisosDePrueba = permisos
  return render(
    <MenuLateral
      seccionActiva="inicio"
      onSeleccionar={() => {}}
      onCerrarSesion={() => {}}
    />,
  )
}

describe('MenuLateral: filtrado de opciones por permiso', () => {
  it('a) con CLIENTES/PRODUCTOS/PEDIDOS muestra esas opciones + Inicio y oculta Reporte diario y Administracion', () => {
    renderMenu(['CLIENTES', 'PRODUCTOS', 'PEDIDOS'])

    // Inicio siempre visible (permission null).
    expect(screen.getByRole('button', { name: /inicio/i })).toBeInTheDocument()
    // Opciones habilitadas por su permiso.
    expect(screen.getByRole('button', { name: /clientes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /productos/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pedidos/i })).toBeInTheDocument()

    // Sin REPORTE_DIARIO no aparece "Reporte diario".
    expect(screen.queryByText('Reporte diario')).not.toBeInTheDocument()
    // Sin ADMINISTRACION/USUARIOS/ROLES no aparece "Administracion".
    expect(screen.queryByText('Administración')).not.toBeInTheDocument()
  })

  it('b) con solo ROLES muestra Administracion (regla especial) y oculta Clientes/Productos/Pedidos/Reporte diario', () => {
    renderMenu(['ROLES'])

    // Inicio sigue visible.
    expect(screen.getByRole('button', { name: /inicio/i })).toBeInTheDocument()
    // Administracion visible por la regla ADMINISTRACION || USUARIOS || ROLES.
    expect(screen.getByText('Administración')).toBeInTheDocument()

    // El resto de opciones funcionales NO deben aparecer.
    expect(screen.queryByText('Clientes')).not.toBeInTheDocument()
    expect(screen.queryByText('Productos')).not.toBeInTheDocument()
    expect(screen.queryByText('Pedidos')).not.toBeInTheDocument()
    expect(screen.queryByText('Reporte diario')).not.toBeInTheDocument()
  })

  it('c) con ADMINISTRACION (y todos) muestra Administracion y las demas opciones', () => {
    renderMenu([
      'CLIENTES',
      'PRODUCTOS',
      'PEDIDOS',
      'REPORTE_DIARIO',
      'ADMINISTRACION',
      'USUARIOS',
      'ROLES',
    ])

    expect(screen.getByRole('button', { name: /inicio/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /clientes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /productos/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pedidos/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reporte diario/i })).toBeInTheDocument()
    expect(screen.getByText('Administración')).toBeInTheDocument()
  })
})

// Pruebas de las FUNCIONES PURAS (misma fuente de verdad de permisos). No
// requieren render ni useAuth: se les pasa un hasPermission simulado.
describe('MenuLateral: funciones puras de permisos', () => {
  it('puedeVerOpcion: Administracion visible con solo ROLES', () => {
    const opcion = { id: 'administracion', permission: 'ADMINISTRACION' }
    expect(puedeVerOpcion(opcion, (c) => ['ROLES'].includes(c))).toBe(true)
  })

  it('puedeVerOpcion: Clientes NO visible si el usuario solo tiene PEDIDOS', () => {
    const opcion = { id: 'clientes', permission: 'CLIENTES' }
    expect(puedeVerOpcion(opcion, (c) => ['PEDIDOS'].includes(c))).toBe(false)
  })

  it('tienePermisoDeSeccion: "reporte" NO accesible sin permisos', () => {
    expect(tienePermisoDeSeccion('reporte', () => false)).toBe(false)
  })

  it('tienePermisoDeSeccion: "inicio" SIEMPRE accesible aunque no haya permisos', () => {
    expect(tienePermisoDeSeccion('inicio', () => false)).toBe(true)
  })

  it('tienePermisoDeSeccion: "clientes" NO accesible si hasPermission no incluye CLIENTES', () => {
    // Esto documenta que App.jsx bloquea la seccion restringida reutilizando
    // esta misma funcion (defensa en profundidad de la navegacion).
    expect(tienePermisoDeSeccion('clientes', (c) => ['ROLES'].includes(c))).toBe(false)
  })

  it('OPCIONES_MENU contiene las 6 opciones esperadas en orden', () => {
    expect(OPCIONES_MENU.map((o) => o.id)).toEqual([
      'inicio',
      'clientes',
      'productos',
      'pedidos',
      'reporte',
      'administracion',
    ])
  })
})
