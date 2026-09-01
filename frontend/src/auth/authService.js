// Cliente HTTP de los endpoints de autenticacion (/auth).
//
// A diferencia de api.js (que apunta a la base con sufijo /api para los
// endpoints de negocio), los endpoints de auth viven directamente bajo /auth,
// SIN el prefijo /api. Por eso derivamos la base del backend a partir de
// API_URL quitando ese sufijo:
//   API_URL = http://localhost:8000/api  ->  AUTH_BASE = http://localhost:8000
//
// La sesion se maneja por COOKIE HttpOnly, por lo que todas las llamadas usan
// `credentials: 'include'` para que la cookie viaje en la peticion. NO se
// guarda contrasena ni datos sensibles en localStorage/sessionStorage.

import { API_URL } from '../api.js'

// Base del backend sin el sufijo /api (los endpoints de auth no van bajo /api).
const AUTH_BASE = API_URL.replace(/\/api\/?$/, '')

// Mensajes fijos (mismos textos que muestra la app al usuario).
const MENSAJE_CREDENCIALES = 'Usuario o contraseña incorrectos.'
const MENSAJE_ERROR_CONEXION = 'No fue posible conectar con el servidor.'

/**
 * Inicia sesion contra POST /auth/login.
 *
 * @param {string} username
 * @param {string} password
 * @returns {Promise<object>} El usuario autenticado {id, username, active}.
 * @throws {Error} Con el `detail` del backend (o mensaje generico) si las
 *   credenciales fallan; con MENSAJE_ERROR_CONEXION ante fallo de red.
 */
export async function login(username, password) {
  let respuesta
  try {
    respuesta = await fetch(`${AUTH_BASE}/auth/login`, {
      method: 'POST',
      credentials: 'include', // la respuesta setea la cookie de sesion HttpOnly
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
  } catch (error) {
    // Fallo de red: el backend no respondio.
    throw new Error(MENSAJE_ERROR_CONEXION)
  }

  // Intentamos leer el cuerpo JSON (puede traer {detail} en error o el usuario).
  let cuerpo = null
  try {
    const texto = await respuesta.text()
    cuerpo = texto ? JSON.parse(texto) : null
  } catch (error) {
    cuerpo = null
  }

  if (!respuesta.ok) {
    // Mensaje generico: no distinguimos usuario vs contrasena.
    const mensaje = (cuerpo && cuerpo.detail) || MENSAJE_CREDENCIALES
    throw new Error(mensaje)
  }

  return cuerpo
}

/**
 * Consulta la sesion actual contra GET /auth/me.
 *
 * DECISION documentada: ante 401 (sin sesion) devolvemos `null`. Ante
 * cualquier otro error (incluido fallo de red o respuesta inesperada) tambien
 * devolvemos `null` y lo tratamos como "no autenticado". Se prioriza la
 * simplicidad del gate: si no podemos confirmar una sesion valida, mostramos
 * el Login en vez de bloquear la app con un estado de error.
 *
 * @returns {Promise<object|null>} El usuario si hay sesion valida; null si no.
 */
export async function obtenerSesion() {
  let respuesta
  try {
    respuesta = await fetch(`${AUTH_BASE}/auth/me`, {
      method: 'GET',
      credentials: 'include', // envia la cookie de sesion para validarla
    })
  } catch (error) {
    // Fallo de red: tratamos como "sin sesion" (ver decision arriba).
    return null
  }

  // 401 (u otro status !ok) -> no hay sesion valida.
  if (!respuesta.ok) {
    return null
  }

  try {
    const texto = await respuesta.text()
    return texto ? JSON.parse(texto) : null
  } catch (error) {
    return null
  }
}

/**
 * Cierra la sesion contra POST /auth/logout.
 *
 * El backend invalida la sesion y borra la cookie. Los errores no criticos se
 * ignoran: pase lo que pase, el frontend limpiara el usuario en el contexto.
 *
 * @returns {Promise<void>}
 */
export async function logout() {
  try {
    await fetch(`${AUTH_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include', // envia la cookie para poder invalidar la sesion
    })
  } catch (error) {
    // Fallo de red al cerrar sesion: se ignora (no es critico para el cliente).
  }
}
