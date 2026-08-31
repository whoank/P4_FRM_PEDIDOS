// Pruebas del layout, el menu lateral y el enrutado por estado (Tarea 14.2).
//
// Se prueba a traves de <App /> para cubrir el comportamiento integrado:
//  - Render de las 5 opciones del menu (Req. 1.1).
//  - Cambio de seccion al hacer clic: el breadcrumb/contenido lo refleja (Req. 1.2).
//  - Resaltado del activo con aria-current="page" (Req. 1.3) e Inicio por
//    defecto al iniciar (Req. 13.1).
//
// Framework: Vitest + @testing-library/react (jsdom, globals habilitados en
// vite.config.js). Los matchers extendidos vienen de @testing-library/jest-dom.
//
// Requerimientos: 1.1, 1.2, 1.3, 13.1

import '@testing-library/jest-dom'
import { render, screen, fireEvent, within } from '@testing-library/react'
import App from './App.jsx'

describe('MenuLateral y layout (App)', () => {
  it('muestra las 5 opciones de navegacion (Req. 1.1)', () => {
    render(<App />)

    // Cada opcion es un boton accesible por su nombre (etiqueta visible).
    expect(screen.getByRole('button', { name: /inicio/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /clientes/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /productos/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /pedidos/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /reporte diario/i })).toBeInTheDocument()
  })

  it('muestra Inicio como seccion activa por defecto (Req. 13.1)', () => {
    render(<App />)

    // El item Inicio esta marcado como pagina actual.
    const inicio = screen.getByRole('button', { name: /inicio/i })
    expect(inicio).toHaveAttribute('aria-current', 'page')

    // El breadcrumb y el contenido reflejan Inicio.
    const topbar = screen.getByRole('banner') // <header class="topbar">
    expect(within(topbar).getByText('Inicio')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Inicio' })).toBeInTheDocument()
  })

  it('cambia de seccion al hacer clic en una opcion (Req. 1.2)', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /clientes/i }))

    // El breadcrumb (topbar) y el contenido reflejan la seccion Clientes.
    const topbar = screen.getByRole('banner')
    expect(within(topbar).getByText('Clientes')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Clientes' })).toBeInTheDocument()
  })

  it('resalta la opcion seleccionada con aria-current="page" y desmarca la anterior (Req. 1.3)', () => {
    render(<App />)

    const inicio = screen.getByRole('button', { name: /inicio/i })
    const productos = screen.getByRole('button', { name: /productos/i })

    // Estado inicial: Inicio activo, Productos no.
    expect(inicio).toHaveAttribute('aria-current', 'page')
    expect(productos).not.toHaveAttribute('aria-current')

    // Al seleccionar Productos, el activo cambia.
    fireEvent.click(productos)
    expect(productos).toHaveAttribute('aria-current', 'page')
    expect(inicio).not.toHaveAttribute('aria-current')
  })
})
