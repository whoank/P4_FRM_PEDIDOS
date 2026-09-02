// Pruebas de la seccion ROLES: carga del catalogo de permisos, creacion de rol
// con permisos seleccionados y edicion que precarga los permisos existentes.
//
// Requerimientos cubiertos:
//  - El formulario de rol muestra un checkbox por cada permiso del catalogo
//    (listarPermisos) -> "asignacion de permisos por opcion".
//  - Crear rol envia crearRol({ nombre, permisos:[codigos] }) con los permisos
//    marcados.
//  - Editar un rol marca (checked) los permisos que ya tiene.
//
// Estrategia de aislamiento:
//  - Roles llama a api.js en useEffect y al guardar. MOCKEAMOS '../api.js' con
//    vi.fn() para controlar los datos y espiar las llamadas. Se mockean las 5
//    funciones que Roles importa (listarRoles, listarPermisos, crearRol,
//    actualizarRol, cambiarEstadoRol).
//  - Roles NO usa useAuth, asi que no hace falta mockear AuthContext.
//
// Framework: Vitest + @testing-library/react. Las cargas async del useEffect se
// esperan con waitFor / findBy*.

import '@testing-library/jest-dom'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

// --- Mock de api.js -------------------------------------------------------
// Datos de prueba controlados. Cada permiso tiene {codigo, nombre}; el label
// del checkbox usa `nombre`.
const CATALOGO = [
  { codigo: 'CLIENTES', nombre: 'Clientes' },
  { codigo: 'PRODUCTOS', nombre: 'Productos' },
  { codigo: 'PEDIDOS', nombre: 'Pedidos' },
]

// Contenedor mutable para poder cambiar el rol devuelto por listarRoles segun
// la prueba (la prueba de edicion necesita un rol con permisos concretos).
let rolesDePrueba = [
  {
    id: 1,
    nombre: 'Administrador',
    descripcion: 'Acceso completo',
    activo: true,
    permisos: [{ codigo: 'CLIENTES', nombre: 'Clientes' }],
    cantidad_permisos: 1,
  },
]

vi.mock('../api.js', () => ({
  listarRoles: vi.fn(() => Promise.resolve(rolesDePrueba)),
  listarPermisos: vi.fn(() => Promise.resolve(CATALOGO)),
  crearRol: vi.fn(() => Promise.resolve({})),
  actualizarRol: vi.fn(() => Promise.resolve({})),
  cambiarEstadoRol: vi.fn(() => Promise.resolve({})),
}))

// Imports DESPUES del mock: el componente y las funciones mockeadas (para
// espiar sus llamadas con expect).
import Roles from './Roles.jsx'
import { listarPermisos, crearRol } from '../api.js'

// Restablece el rol de prueba por defecto antes de cada test.
beforeEach(() => {
  rolesDePrueba = [
    {
      id: 1,
      nombre: 'Administrador',
      descripcion: 'Acceso completo',
      activo: true,
      permisos: [{ codigo: 'CLIENTES', nombre: 'Clientes' }],
      cantidad_permisos: 1,
    },
  ]
  vi.clearAllMocks()
})

describe('Roles: catalogo de permisos en el formulario', () => {
  it('a) al abrir "Crear rol" muestra un checkbox por cada permiso del catalogo', async () => {
    render(<Roles />)

    // El catalogo se pide al montar (useEffect -> listarPermisos).
    await waitFor(() => expect(listarPermisos).toHaveBeenCalled())

    // Abrir el formulario de creacion.
    fireEvent.click(screen.getByRole('button', { name: /Crear rol/i }))

    // Un checkbox por permiso, accesible por su label (nombre del permiso).
    const chkClientes = await screen.findByRole('checkbox', { name: /Clientes/i })
    const chkProductos = screen.getByRole('checkbox', { name: /Productos/i })
    const chkPedidos = screen.getByRole('checkbox', { name: /Pedidos/i })

    expect(chkClientes).toBeInTheDocument()
    expect(chkProductos).toBeInTheDocument()
    expect(chkPedidos).toBeInTheDocument()

    // Al crear, todos inician sin marcar.
    expect(chkClientes).not.toBeChecked()
    expect(chkProductos).not.toBeChecked()
    expect(chkPedidos).not.toBeChecked()
  })
})

describe('Roles: creacion envia los permisos marcados', () => {
  it('b) crea el rol "Operador" con permisos [CLIENTES, PRODUCTOS, PEDIDOS]', async () => {
    render(<Roles />)
    await waitFor(() => expect(listarPermisos).toHaveBeenCalled())

    // Abrir formulario de creacion.
    fireEvent.click(screen.getByRole('button', { name: /Crear rol/i }))

    // Escribir el nombre (input con label "Nombre", htmlFor=nombre).
    const inputNombre = await screen.findByLabelText('Nombre')
    fireEvent.change(inputNombre, { target: { value: 'Operador' } })

    // Marcar los tres permisos.
    fireEvent.click(screen.getByRole('checkbox', { name: /Clientes/i }))
    fireEvent.click(screen.getByRole('checkbox', { name: /Productos/i }))
    fireEvent.click(screen.getByRole('checkbox', { name: /Pedidos/i }))

    // Enviar el formulario (boton "Guardar").
    fireEvent.click(screen.getByRole('button', { name: /Guardar/i }))

    // Se llama crearRol con el nombre y los permisos exactos (orden de marcado).
    await waitFor(() => expect(crearRol).toHaveBeenCalledTimes(1))
    expect(crearRol).toHaveBeenCalledWith(
      expect.objectContaining({
        nombre: 'Operador',
        permisos: expect.arrayContaining(['CLIENTES', 'PRODUCTOS', 'PEDIDOS']),
      }),
    )
    // Verifica ademas que no incluye permisos extra (exactamente 3).
    const argumentos = crearRol.mock.calls[0][0]
    expect(argumentos.permisos).toHaveLength(3)
  })
})

describe('Roles: edicion precarga los permisos existentes', () => {
  it('c) al editar un rol con [PEDIDOS], el checkbox Pedidos queda marcado y los demas no', async () => {
    // Rol de prueba con un unico permiso: PEDIDOS.
    rolesDePrueba = [
      {
        id: 7,
        nombre: 'Despacho',
        descripcion: 'Solo pedidos',
        activo: true,
        permisos: [{ codigo: 'PEDIDOS', nombre: 'Pedidos' }],
        cantidad_permisos: 1,
      },
    ]

    render(<Roles />)

    // Esperar a que la fila del rol aparezca en la tabla (listarRoles resuelto).
    const botonEditar = await screen.findByRole('button', { name: /Editar/i })
    fireEvent.click(botonEditar)

    // El formulario de edicion marca los permisos del rol: Pedidos = checked.
    const chkPedidos = await screen.findByRole('checkbox', { name: /Pedidos/i })
    const chkClientes = screen.getByRole('checkbox', { name: /Clientes/i })
    const chkProductos = screen.getByRole('checkbox', { name: /Productos/i })

    expect(chkPedidos).toBeChecked()
    expect(chkClientes).not.toBeChecked()
    expect(chkProductos).not.toBeChecked()
  })
})
