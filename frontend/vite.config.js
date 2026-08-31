// Configuracion de Vite para el frontend de React.
// - Se activa el plugin oficial de React (soporte de JSX y Fast Refresh).
// - El servidor de desarrollo escucha en el puerto 3000.
// - host: true expone el servidor en todas las interfaces de red,
//   necesario para que funcione dentro de un contenedor Docker (Tarea 22).
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
  },
  // Configuración de Vitest.
  // - environment 'jsdom' para poder probar también componentes React (Tareas 14+).
  //   Para las pruebas de api.js con fetch mockeado bastaría 'node', pero jsdom
  //   sirve igual y evita reconfigurar más adelante.
  // - globals: true habilita describe/it/expect/vi sin importarlos en cada test.
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
