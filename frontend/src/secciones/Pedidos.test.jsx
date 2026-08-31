// Pruebas de la seccion Pedidos (Tarea 18.2).
//
// Foco (Req. 9.2, 9.3): la PREVISUALIZACION del Total mostrada en el formulario
// debe ser cantidad * precio_unitario del producto seleccionado, y debe
// ACTUALIZARSE cuando cambia la cantidad (y cuando cambia el producto).
//
// Se mockea '../api.js' con vi.mock para no hacer peticiones reales. El mock
// respeta las exportaciones reales usadas por el componente:
//   listarClientes, listarProductos, listarPedidos, crearPedido, cambiarEstadoPedido.
//
// Requerimientos: 9.2, 9.3
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import Pedidos from './Pedidos.jsx'

// Mock del modulo api.js. Cada funcion se reemplaza por un vi.fn() para poder
// controlar los datos devueltos y verificar las llamadas.
vi.mock('../api.js', () => ({
  listarClientes: vi.fn(),
  listarProductos: vi.fn(),
  listarPedidos: vi.fn(),
  crearPedido: vi.fn(),
  cambiarEstadoPedido: vi.fn(),
}))

// Se importan las funciones ya mockeadas para configurarlas en cada prueba.
import {
  listarClientes,
  listarProductos,
  listarPedidos,
  crearPedido,
  cambiarEstadoPedido,
} from '../api.js'

// Datos de prueba con precios conocidos.
const CLIENTES = [
  { id: 1, nombre: 'Ana Perez', telefono: '555-1234', direccion: 'Calle 1' },
]
const PRODUCTOS = [
  // Precio conocido: 55.00 => permite verificar cantidad * precio.
  { id: 10, nombre: 'Hamburguesa', descripcion: 'Clasica', precio: 55.0, disponible: true },
  { id: 11, nombre: 'Refresco', descripcion: 'Lata', precio: 20.0, disponible: true },
]

beforeEach(() => {
  vi.clearAllMocks()
  listarClientes.mockResolvedValue(CLIENTES)
  listarProductos.mockResolvedValue(PRODUCTOS)
  listarPedidos.mockResolvedValue([])
})

describe('Pedidos: previsualizacion del Total (Req. 9.2, 9.3)', () => {
  it('muestra cantidad * precio del producto y lo recalcula al cambiar la cantidad', async () => {
    render(<Pedidos />)

    // Espera a que carguen los productos (opciones en el selector).
    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Hamburguesa/ })).toBeInTheDocument()
    })

    const selectProducto = screen.getByLabelText('Producto')
    const inputCantidad = screen.getByLabelText('Cantidad')
    const total = screen.getByTestId('total-previsualizado')

    // Selecciona el producto de precio 55.00.
    fireEvent.change(selectProducto, { target: { value: '10' } })

    // Con cantidad inicial 1 => 1 * 55 = 55.00.
    await waitFor(() => {
      expect(total).toHaveTextContent('$55.00')
    })

    // Cambia la cantidad a 3 => 3 * 55 = 165.00 (se recalcula, Req. 9.2, 9.3).
    fireEvent.change(inputCantidad, { target: { value: '3' } })
    await waitFor(() => {
      expect(total).toHaveTextContent('$165.00')
    })

    // Cambia la cantidad a 5 => 5 * 55 = 275.00 (vuelve a recalcularse).
    fireEvent.change(inputCantidad, { target: { value: '5' } })
    await waitFor(() => {
      expect(total).toHaveTextContent('$275.00')
    })
  })

  it('recalcula el Total al cambiar el producto seleccionado', async () => {
    render(<Pedidos />)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Refresco/ })).toBeInTheDocument()
    })

    const selectProducto = screen.getByLabelText('Producto')
    const inputCantidad = screen.getByLabelText('Cantidad')
    const total = screen.getByTestId('total-previsualizado')

    fireEvent.change(inputCantidad, { target: { value: '2' } })

    // Producto de 55 => 2 * 55 = 110.00.
    fireEvent.change(selectProducto, { target: { value: '10' } })
    await waitFor(() => {
      expect(total).toHaveTextContent('$110.00')
    })

    // Cambia al producto de 20 => 2 * 20 = 40.00.
    fireEvent.change(selectProducto, { target: { value: '11' } })
    await waitFor(() => {
      expect(total).toHaveTextContent('$40.00')
    })
  })
})

describe('Pedidos: carga de datos y estados iniciales', () => {
  it('carga productos solo disponibles (listarProductos(true))', async () => {
    render(<Pedidos />)
    await waitFor(() => {
      expect(listarProductos).toHaveBeenCalledWith(true)
    })
  })

  it('muestra el mensaje cuando no hay pedidos (Req. 11.2)', async () => {
    render(<Pedidos />)
    await waitFor(() => {
      expect(screen.getByText('No hay pedidos registrados.')).toBeInTheDocument()
    })
  })
})

describe('Pedidos: creacion y cambio de estado', () => {
  it('crea el pedido con cliente, producto y cantidad, y refresca la lista', async () => {
    crearPedido.mockResolvedValue({ id: 1 })
    render(<Pedidos />)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Hamburguesa/ })).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText('Cliente'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Producto'), { target: { value: '10' } })
    fireEvent.change(screen.getByLabelText('Cantidad'), { target: { value: '3' } })

    fireEvent.click(screen.getByRole('button', { name: 'Crear pedido' }))

    await waitFor(() => {
      expect(crearPedido).toHaveBeenCalledWith({
        cliente_id: 1,
        producto_id: 10,
        cantidad: 3,
      })
    })
    // Se refresca la lista tras crear (llamada inicial + refresco).
    expect(listarPedidos).toHaveBeenCalledTimes(2)
  })

  it('muestra el error del backend y conserva los datos ingresados (Req. 16.1)', async () => {
    crearPedido.mockRejectedValue(new Error('El Producto no esta disponible.'))
    render(<Pedidos />)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: /Hamburguesa/ })).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText('Cliente'), { target: { value: '1' } })
    fireEvent.change(screen.getByLabelText('Producto'), { target: { value: '10' } })
    fireEvent.change(screen.getByLabelText('Cantidad'), { target: { value: '4' } })

    fireEvent.click(screen.getByRole('button', { name: 'Crear pedido' }))

    await waitFor(() => {
      expect(screen.getByText('El Producto no esta disponible.')).toBeInTheDocument()
    })
    // Los datos se conservan (no se limpian ante error).
    expect(screen.getByLabelText('Cantidad')).toHaveValue(4)
    expect(screen.getByLabelText('Producto')).toHaveValue('10')
  })

  it('cambia el estado de un pedido y refresca la lista (Req. 10.1)', async () => {
    listarPedidos.mockResolvedValue([
      {
        id: 7,
        cliente_nombre: 'Ana Perez',
        producto_nombre: 'Hamburguesa',
        cantidad: 2,
        precio_unitario: 55.0,
        total: 110.0,
        fecha: '2025-05-20',
        estado: 'Pendiente',
      },
    ])
    cambiarEstadoPedido.mockResolvedValue({ id: 7, estado: 'Preparando' })
    render(<Pedidos />)

    const selectEstado = await screen.findByLabelText('Estado del pedido 7')
    fireEvent.change(selectEstado, { target: { value: 'Preparando' } })

    await waitFor(() => {
      expect(cambiarEstadoPedido).toHaveBeenCalledWith(7, 'Preparando')
    })
  })
})
