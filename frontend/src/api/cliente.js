// Cliente HTTP del dashboard SORT-MATIC.
//
// Centraliza tres cosas que si no habria que repetir en cada pantalla:
//   * mandar el token de acceso en cada pedido,
//   * renovarlo solo cuando vence (una sola vez por pedido),
//   * cerrar la sesion si el refresco tampoco sirve.
//
// Los tokens se guardan en localStorage para que al recargar la pagina el
// operador no tenga que volver a entrar. Es la contrapartida conocida de no
// usar cookies httpOnly: un XSS podria leerlos. Por eso el token de acceso
// dura poco (ver SIMPLE_JWT en el backend) y el refresco rota en cada uso.

const API_BASE = import.meta.env.VITE_API_BASE || ''

const CLAVE_ACCESO = 'sortmatic.acceso'
const CLAVE_REFRESCO = 'sortmatic.refresco'

// Varias pantallas piden datos a la vez: si todas ven un 401 no deben
// disparar cinco refrescos. Se comparte la promesa del que llego primero.
let refrescoEnCurso = null

export function leerAcceso() {
  return localStorage.getItem(CLAVE_ACCESO)
}

export function guardarTokens({ access, refresh }) {
  if (access) localStorage.setItem(CLAVE_ACCESO, access)
  if (refresh) localStorage.setItem(CLAVE_REFRESCO, refresh)
}

export function borrarTokens() {
  localStorage.removeItem(CLAVE_ACCESO)
  localStorage.removeItem(CLAVE_REFRESCO)
}

export class ErrorApi extends Error {
  constructor(mensaje, estado, detalles) {
    super(mensaje)
    this.estado = estado
    this.detalles = detalles || {}
  }
}

function mensajeDeError(estado, cuerpo) {
  if (!cuerpo) return `Error ${estado}`
  if (typeof cuerpo === 'string') return cuerpo
  if (cuerpo.detalle) return cuerpo.detalle
  if (cuerpo.detail) return cuerpo.detail
  const primero = Object.values(cuerpo)[0]
  if (Array.isArray(primero)) return primero[0]
  if (typeof primero === 'string') return primero
  return `Error ${estado}`
}

async function cuerpoDe(respuesta) {
  if (respuesta.status === 204) return null
  const texto = await respuesta.text()
  if (!texto) return null
  try {
    return JSON.parse(texto)
  } catch {
    return texto
  }
}

async function refrescarAcceso() {
  const refresh = localStorage.getItem(CLAVE_REFRESCO)
  if (!refresh) return null

  if (!refrescoEnCurso) {
    refrescoEnCurso = fetch(`${API_BASE}/api/auth/refrescar/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh }),
    })
      .then(async (r) => {
        if (!r.ok) return null
        const datos = await r.json()
        guardarTokens(datos)
        return datos.access
      })
      .catch(() => null)
      .finally(() => {
        refrescoEnCurso = null
      })
  }
  return refrescoEnCurso
}

/**
 * Pedido autenticado a la API. Devuelve el cuerpo ya parseado.
 * Lanza ErrorApi si el backend responde un codigo de error.
 */
export async function api(ruta, opciones = {}) {
  const { cuerpo, archivo, metodo = 'GET', ...resto } = opciones

  const armar = () => {
    const cabeceras = { ...(resto.headers || {}) }
    const acceso = leerAcceso()
    if (acceso) cabeceras.Authorization = `Bearer ${acceso}`

    let contenido
    if (archivo) {
      contenido = archivo // FormData: el navegador pone el Content-Type con su boundary
    } else if (cuerpo !== undefined) {
      cabeceras['Content-Type'] = 'application/json'
      contenido = JSON.stringify(cuerpo)
    }
    return fetch(`${API_BASE}${ruta}`, { ...resto, method: metodo, headers: cabeceras, body: contenido })
  }

  let respuesta = await armar()

  if (respuesta.status === 401 && leerAcceso()) {
    const nuevo = await refrescarAcceso()
    if (nuevo) {
      respuesta = await armar()
    }
  }

  const datos = await cuerpoDe(respuesta)
  if (!respuesta.ok) {
    throw new ErrorApi(mensajeDeError(respuesta.status, datos), respuesta.status, datos)
  }
  return datos
}

/** Inicio de sesion. Guarda los tokens y devuelve los datos del usuario. */
export async function iniciarSesion(username, password) {
  const respuesta = await fetch(`${API_BASE}/api/auth/login/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  const datos = await cuerpoDe(respuesta)
  if (!respuesta.ok) {
    const mensaje =
      respuesta.status === 401
        ? 'Usuario o contraseña incorrectos.'
        : respuesta.status === 429
          ? 'Demasiados intentos. Espere un minuto y vuelva a probar.'
          : mensajeDeError(respuesta.status, datos)
    throw new ErrorApi(mensaje, respuesta.status, datos)
  }
  guardarTokens(datos)
  return datos.usuario
}

/** Los listados de DRF vienen paginados; las acciones sueltas no. */
export function filas(respuesta) {
  if (!respuesta) return []
  return Array.isArray(respuesta) ? respuesta : (respuesta.results ?? [])
}
