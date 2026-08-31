// Punto de entrada de la aplicacion.
// Monta el componente raiz <App /> en el nodo #root del index.html
// e importa los estilos globales (variables CSS de la guia de estilo).
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
