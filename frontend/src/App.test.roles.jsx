// Pruebas del BLOQUEO de secciones restringidas (usuario sin permiso no puede
// entrar a una seccion) para el sistema de Roles y Permisos por opcion de menu.
//
// NOTA IMPORTANTE (limitacion documentada):
// App.jsx protege el render de una seccion con `tienePermisoDeSeccion` y muestra
// "No tienes permiso para ver esta seccion." cuando el usuario no tiene permiso.
// Sin embargo, App arranca SIEMPRE en 'inicio' (accesible para todos) y no
// permite fijar `seccionActiva` desde fuera; ademas AuthGate hace un fetch a
// /auth/me. Por eso una prueba de integracion pura de App es fragil.
//
// Enfoque adoptado (robusto y sin red):
//  1) Prueba UNITARIA de la regla `tienePermisoDeSeccion` (la MISMA funcion que
//     App usa para bloquear), demostrando que una seccion restringida como
//     'clientes' NO es accesible sin el permiso 'CLIENTES'. Esto valida la
//     logica de proteccion que App reutiliza (unica fuente de verdad).
//  2) Prueba de INTEGRACION de una copia minima del gate protegido de App, que
//     reproduce el mismo patron condicional
//     (puedeAcceder ? seccion : aviso) usando `tienePermisoDeSeccion`, para
//     comprobar de forma visual que se muestra el aviso de "No tienes permiso...".
//
// No se toca App.test.jsx existente: este es un archivo nuevo e independiente.
//
// Framework: Vitest + @testing-library/react.

import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { tienePermisoDeSeccion } from './componentes/MenuLateral.jsx'

describe('Bloqueo de seccion restringida (regla que usa App)', () => {
  it('1) tienePermisoDeSeccion bloquea "clientes" si hasPermission no incluye CLIENTES', () => {
    // Usuario con ROLES pero SIN CLIENTES: no debe poder acceder a Clientes.
    const hasPermission = (c) => ['ROLES'].includes(c)
    expect(tienePermisoDeSeccion('clientes', hasPermission)).toBe(false)
  })

  it('1b) tienePermisoDeSeccion permite "clientes" si hasPermission incluye CLIENTES', () => {
    const hasPermission = (c) => ['CLIENTES'].includes(c)
    expect(tienePermisoDeSeccion('clientes', hasPermission)).toBe(true)
  })

  it('2) el patron de proteccion de App muestra el aviso cuando no hay permiso', () => {
    // Reproduccion minima del bloque protegido de AppAutenticada: la misma
    // condicion (puedeAcceder ? seccion : aviso) con la misma funcion.
    const hasPermission = (c) => ['ROLES'].includes(c)
    const seccionActiva = 'clientes' // seccion restringida

    function GateProtegidoDePrueba() {
      const puedeAcceder = tienePermisoDeSeccion(seccionActiva, hasPermission)
      return (
        <main>
          {puedeAcceder ? (
            <div>CONTENIDO_CLIENTES</div>
          ) : (
            <section>No tienes permiso para ver esta sección.</section>
          )}
        </main>
      )
    }

    render(<GateProtegidoDePrueba />)

    // Se muestra el aviso y NO el contenido de la seccion restringida.
    expect(
      screen.getByText('No tienes permiso para ver esta sección.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('CONTENIDO_CLIENTES')).not.toBeInTheDocument()
  })

  it('2b) el mismo patron muestra el contenido cuando SI hay permiso', () => {
    const hasPermission = (c) => ['CLIENTES'].includes(c)
    const seccionActiva = 'clientes'

    function GateProtegidoDePrueba() {
      const puedeAcceder = tienePermisoDeSeccion(seccionActiva, hasPermission)
      return (
        <main>
          {puedeAcceder ? (
            <div>CONTENIDO_CLIENTES</div>
          ) : (
            <section>No tienes permiso para ver esta sección.</section>
          )}
        </main>
      )
    }

    render(<GateProtegidoDePrueba />)

    expect(screen.getByText('CONTENIDO_CLIENTES')).toBeInTheDocument()
    expect(
      screen.queryByText('No tienes permiso para ver esta sección.'),
    ).not.toBeInTheDocument()
  })
})
