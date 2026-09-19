// Telemetria en vivo de la linea: WebSocket para los eventos + REST para los
// agregados (KPIs, tendencia, historial).
//
// Es un CONTEXTO, no un hook suelto: antes cada pantalla que lo usaba abria
// su propio socket, asi que al abrir dos se duplicaban las conexiones y los
// pedidos. Ahora el proveedor vive en el Layout (o sea, solo con sesion
// iniciada) y todas las pantallas comparten el mismo flujo, incluida la
// cabecera, que muestra el estado de conexion en toda la HMI.
//
// En Docker, nginx.conf proxea /api y /ws hacia el backend, asi que un path
// relativo alcanza. En dev (vite), lo redirige el proxy de vite.config.js.
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

import { api, filas, leerAcceso } from '../api/cliente.js'

const WS_BASE =
  import.meta.env.VITE_WS_BASE ||
  (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host

const RECONEXION_MS = 3000
const MAX_EVENTOS = 8

// Cada botella dispara un evento. A cadencia alta, recargar los agregados en
// cada uno serian varias consultas por segundo contra la misma respuesta:
// se juntan las que caen dentro de esta ventana.
const AGRUPAR_MS = 500

// Lo cierra el consumer cuando el token no sirve (ver linea/consumers.py).
const CIERRE_NO_AUTORIZADO = 4401

const ContextoTelemetria = createContext(null)

export function ProveedorTelemetria({ children }) {
  const [lote, setLote] = useState(null)
  const [kpis, setKpis] = useState(null)
  const [tendencia, setTendencia] = useState([])
  const [lotes, setLotes] = useState([])
  const [conectado, setConectado] = useState(false)
  const [camaraFrame, setCamaraFrame] = useState(null)
  const [estadoFaja, setEstadoFaja] = useState(null)
  const [eventos, setEventos] = useState([])
  const [ultimaSenal, setUltimaSenal] = useState(null)
  const [cargando, setCargando] = useState(true)

  const temporizadorRefresco = useRef(null)
  const lotePendiente = useRef(undefined)

  const refrescarAhora = useCallback(async (loteId) => {
    const qs = loteId ? `?lote=${loteId}` : ''
    // Las tres consultas son independientes: van juntas y un fallo de una no
    // deja las otras sin actualizar.
    const [k, t, l] = await Promise.allSettled([
      api(`/api/kpis/${qs}`),
      api(`/api/tendencia/${qs}`),
      api('/api/lotes/'),
    ])
    if (k.status === 'fulfilled') setKpis(k.value)
    if (t.status === 'fulfilled') setTendencia(t.value)
    if (l.status === 'fulfilled') setLotes(filas(l.value))
    setCargando(false)
  }, [])

  const refrescar = useCallback(
    (loteId) => {
      lotePendiente.current = loteId
      if (temporizadorRefresco.current) return
      temporizadorRefresco.current = setTimeout(() => {
        temporizadorRefresco.current = null
        refrescarAhora(lotePendiente.current)
      }, AGRUPAR_MS)
    },
    [refrescarAhora],
  )

  useEffect(() => {
    refrescarAhora()
    api('/api/estado-faja/')
      .then(setEstadoFaja)
      .catch(() => {})
    return () => clearTimeout(temporizadorRefresco.current)
  }, [refrescarAhora])

  useEffect(() => {
    let ws
    let cerrado = false
    let temporizador

    const conectar = () => {
      const token = leerAcceso()
      if (!token) return
      ws = new WebSocket(`${WS_BASE}/ws/telemetria/?token=${encodeURIComponent(token)}`)

      ws.onopen = () => setConectado(true)
      ws.onclose = (ev) => {
        setConectado(false)
        if (cerrado) return
        // Si el token vencio, un pedido REST cualquiera lo renueva; despues
        // se reintenta la conexion con el token nuevo.
        if (ev.code === CIERRE_NO_AUTORIZADO) {
          api('/api/auth/yo/').catch(() => {})
        }
        temporizador = setTimeout(conectar, RECONEXION_MS)
      }
      ws.onerror = () => ws.close()

      ws.onmessage = (ev) => {
        let msg
        try {
          msg = JSON.parse(ev.data)
        } catch {
          return
        }
        setUltimaSenal(Date.now())
        if (msg.evento === 'progreso_lote') {
          setLote(msg.datos.lote)
          refrescar(msg.datos.lote.id)
        } else if (msg.evento === 'lote_rotado') {
          setLote(msg.datos.lote_nuevo)
          refrescar(msg.datos.lote_nuevo.id)
        } else if (msg.evento === 'inspeccion') {
          refrescar(msg.datos.lote)
          setEventos((prev) => [msg.datos, ...prev].slice(0, MAX_EVENTOS))
        } else if (msg.evento === 'camara') {
          setCamaraFrame(`data:image/jpeg;base64,${msg.datos.jpeg_base64}`)
        } else if (msg.evento === 'estado_faja') {
          setEstadoFaja(msg.datos)
        }
      }
    }

    conectar()
    return () => {
      cerrado = true
      clearTimeout(temporizador)
      ws?.close()
    }
  }, [refrescar])

  const valor = {
    lote,
    kpis,
    tendencia,
    lotes,
    conectado,
    camaraFrame,
    estadoFaja,
    eventos,
    ultimaSenal,
    cargando,
    refrescar: refrescarAhora,
  }

  return <ContextoTelemetria.Provider value={valor}>{children}</ContextoTelemetria.Provider>
}

export function useTelemetria() {
  const valor = useContext(ContextoTelemetria)
  if (valor === null) {
    throw new Error('useTelemetria debe usarse dentro de <ProveedorTelemetria>')
  }
  return valor
}
