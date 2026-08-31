// Pruebas de la seccion Clientes (Tarea 16.2).
//
// Se mockea el modulo '../api.js' con vi.mock para no hacer peticiones de red.
// El foco principal es el comportamiento exigido por los Requerimientos 2.5 y
// 16.1: cuando crearCliente rechaza con un Error, la seccion debe mostrar ese
// mensaje y CONSERVAR los datos ingresados en el formulario.
//
// Requerimientos: 2.5, 16.1

import '@testing-library/jest-dom'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Clientes from './Clientes.jsx'
import * as api from '../api.js'

// Mock del modulo api.js: se declaran exactamente las funciones que usa
// Clientes.jsx (listarClientes, crearCliente, actualizarCliente). Las demas
// exportaciones no se necesitan en estas pruebas.
vi.mock('../api.js', () => ({
  listarClientes: vi.fn(),
  crearCliente: vi.fn(),
  actualizarCliente: vi.fn(),
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('Clientes: carga inicial y listado (Req. 3.1, 3.2)', () => {
  it('al montar llama a listarClientes y renderiza las filas', async () => {
    api.listarClientes.mockResolvedValueOnce([
      { id: 1, nombre: 'Ana Perez', telefono: '555-1234', direccion: 'Calle 1' },
      { id: 2, nombre: 'Luis Gomez', telefono: '555-9876', direccion: 'Calle 2' },
    ])

    render(<Clientes />)

    // Se debe haber pedido la lista al montar.
    expect(api.listarClientes).toHaveBeenCalledTimes(1)

    // Las filas de los clientes aparecen en la tabla.
    expect(await screen.findByText('Ana Perez')).toBeInTheDocument()
    expect(screen.getByText('Luis Gomez')).toBeInTheDocument()
  })

  it('muestra el mensaje de lista vacia cuando no hay clientes', async () => {
    api.listarClientes.mockResolvedValueOnce([])

    render(<Clientes />)

    expect(await screen.findByText('No hay clientes registrados.')).toBeInTheDocument()
  })
})

describe('Clientes: error de validacion al crear (Req. 2.5, 16.1)', () => {
  it('muestra el mensaje de error y conserva los datos ingresados', async () => {
    // Lista inicial vacia; la creacion fallara con un Error de validacion.
    api.listarClientes.mockResolvedValue([])
    api.crearCliente.mockRejectedValueOnce(new Error('El Nombre es obligatorio.'))

    render(<Clientes />)

    // Esperar a que termine la carga inicial (mensaje de lista vacia).
    await screen.findByText('No hay clientes registrados.')

    const inputNombre = screen.getByLabelText('Nombre')
    const inputTelefono = screen.getByLabelText('Teléfono')
    const inputDireccion = screen.getByLabelText('Dirección')

    // El usuario escribe datos en el formulario.
    fireEvent.change(inputNombre, { target: { value: 'Cliente de prueba' } })
    fireEvent.change(inputTelefono, { target: { value: '555-0000' } })
    fireEvent.change(inputDireccion, { target: { value: 'Av. Siempre Viva' } })

    // Envia el formulario (boton "Crear").
    fireEvent.click(screen.getByRole('button', { name: 'Crear' }))

    // Debe intentar crear el cliente y luego mostrar el mensaje de error.
    await waitFor(() => expect(api.crearCliente).toHaveBeenCalledTimes(1))
    expect(await screen.findByText('El Nombre es obligatorio.')).toBeInTheDocument()

    // CLAVE (Req. 2.5, 16.1): los datos ingresados se conservan en los inputs.
    expect(screen.getByLabelText('Nombre')).toHaveValue('Cliente de prueba')
    expect(screen.getByLabelText('Teléfono')).toHaveValue('555-0000')
    expect(screen.getByLabelText('Dirección')).toHaveValue('Av. Siempre Viva')
  })
})
