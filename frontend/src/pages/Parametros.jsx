// Parametros de inspeccion que ajusta el Supervisor de calidad.
//
// Son los mismos umbrales que usa vision/clasificador.py, pero con nombres y
// explicaciones de planta en vez de nombres de variable. Cada deslizador dice
// ademas hacia donde afloja y hacia donde aprieta: sin eso, "subir la certeza
// de la etiqueta" no le dice a nadie si van a salir mas o menos rechazos.
//
// Al guardar, el backend sube su 'version' y el modulo de vision la toma en
// caliente: la inspeccion NO se reinicia ni se interrumpe.
import { AlertTriangle, RotateCcw, Save } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { api } from '../api/cliente.js'
import Boton from '../components/ui/Boton.jsx'
import { CampoSelect } from '../components/ui/Campo.jsx'
import { EsqueletoTarjeta } from '../components/ui/Esqueleto.jsx'
import Tarjeta from '../components/ui/Tarjeta.jsx'
import { useAvisos } from '../hooks/useAvisos.jsx'

// campo -> como se llama en la HMI y hacia donde va cada extremo del deslizador.
const CAMPOS = {
  umbral_llenado_minimo: {
    etiqueta: 'Nivel minimo de llenado',
    min: 0,
    max: 100,
    unidad: '%',
    izquierda: 'acepta botellas mas vacias',
    derecha: 'exige botellas mas llenas',
  },
  confianza_etiqueta: {
    etiqueta: 'Certeza minima · Etiqueta',
    min: 0,
    max: 100,
    unidad: '%',
    izquierda: 'pasan mas dudosas',
    derecha: 'mas rechazos por etiqueta',
  },
  confianza_tapa: {
    etiqueta: 'Certeza minima · Tapa',
    min: 0,
    max: 100,
    unidad: '%',
    izquierda: 'pasan mas dudosas',
    derecha: 'mas rechazos por tapa',
  },
  confianza_defecto: {
    etiqueta: 'Certeza minima · Defecto fisico',
    min: 0,
    max: 100,
    unidad: '%',
    izquierda: 'marca defectos con menos evidencia',
    derecha: 'solo defectos evidentes',
  },
  confianza_deteccion: {
    etiqueta: 'Sensibilidad de deteccion',
    min: 0,
    max: 100,
    unidad: '%',
    izquierda: 've mas objetos, con mas ruido',
    derecha: 've solo lo muy claro',
  },
  fraccion_cuello: {
    etiqueta: 'Altura del cuello de la botella',
    min: 0,
    max: 50,
    unidad: '%',
    izquierda: 'cuello corto',
    derecha: 'cuello largo',
  },
  velocidad_teorica: {
    etiqueta: 'Cadencia teorica de la faja',
    min: 1,
    max: 600,
    unidad: 'BPM',
    izquierda: 'linea lenta',
    derecha: 'linea rapida',
  },
  tamano_imagen: {
    etiqueta: 'Resolucion de analisis',
    opciones: [320, 416, 512, 640, 768, 960, 1280].map((v) => ({ valor: v, texto: `${v} px` })),
  },
  dispositivo_inferencia: {
    etiqueta: 'Procesador del modelo',
    opciones: [
      { valor: 'cpu', texto: 'CPU' },
      { valor: '0', texto: 'GPU (CUDA 0)' },
    ],
  },
}

const GRUPOS = [
  {
    titulo: 'Calidad del producto',
    descripcion: 'Que tan llena tiene que estar una botella para pasar.',
    campos: ['umbral_llenado_minimo'],
  },
  {
    titulo: 'Certeza del modelo de inteligencia artificial',
    descripcion:
      'Que tan seguro tiene que estar el sistema antes de aprobar o rechazar. Cada deslizador dice que pasa al moverlo para cada lado.',
    campos: ['confianza_etiqueta', 'confianza_tapa', 'confianza_defecto', 'confianza_deteccion'],
  },
  {
    titulo: 'Calibracion y rendimiento',
    descripcion: 'Se tocan poco: afectan como se mide el llenado y cuanto tarda cada foto.',
    campos: ['fraccion_cuello', 'tamano_imagen', 'dispositivo_inferencia', 'velocidad_teorica'],
  },
]

const TODOS = GRUPOS.flatMap((g) => g.campos)

function Deslizador({ campo, valor, ayuda, cambiado, onCambio }) {
  const def = CAMPOS[campo]
  const pct = ((valor - def.min) / (def.max - def.min)) * 100

  return (
    <div className="border-t border-slate-800 py-4 first:border-t-0 first:pt-0">
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <label htmlFor={campo} className="text-sm font-medium text-slate-200">
          {def.etiqueta}
          {cambiado && (
            <span className="ml-2 rounded-full bg-amber-500/15 px-1.5 py-0.5 text-xs font-normal text-amber-300">
              sin guardar
            </span>
          )}
        </label>
        <span className="cifra flex-shrink-0 text-lg font-semibold text-cyan-400">
          {valor}
          {def.unidad === '%' ? '%' : ` ${def.unidad}`}
        </span>
      </div>
      {ayuda && <p className="mb-2.5 text-xs text-slate-500">{ayuda}</p>}

      <div className="flex items-center gap-3">
        <input
          id={campo}
          type="range"
          min={def.min}
          max={def.max}
          step={1}
          value={valor}
          onChange={(e) => onCambio(campo, Number(e.target.value))}
          className="h-2 flex-1 cursor-pointer appearance-none rounded-full accent-cyan-500"
          style={{
            background: `linear-gradient(to right, #0e7490 ${pct}%, #334155 ${pct}%)`,
          }}
        />
        <input
          type="number"
          aria-label={`${def.etiqueta}, valor exacto`}
          min={def.min}
          max={def.max}
          value={valor}
          onChange={(e) => onCambio(campo, Number(e.target.value))}
          className="w-20 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-right text-sm text-slate-100 outline-none transition-colors focus:border-cyan-500"
        />
      </div>

      {/* Lo mas util para el supervisor: que consecuencia tiene mover esto. */}
      <div className="mt-1.5 flex justify-between gap-4 pr-[5.75rem] text-[11px] text-slate-600">
        <span>← {def.izquierda}</span>
        <span className="text-right">{def.derecha} →</span>
      </div>
    </div>
  )
}

export default function Parametros() {
  const avisar = useAvisos()
  const [guardado, setGuardado] = useState(null) // lo que hay en el servidor
  const [borrador, setBorrador] = useState(null) // lo que edita el supervisor
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)

  const cargar = useCallback(async () => {
    try {
      const datos = await api('/api/configuracion/')
      setGuardado(datos)
      setBorrador(datos)
    } catch (e) {
      avisar.error(e.message)
    } finally {
      setCargando(false)
    }
  }, [avisar])

  useEffect(() => {
    cargar()
  }, [cargar])

  const cambiados = useMemo(
    () => (borrador && guardado ? TODOS.filter((c) => borrador[c] !== guardado[c]) : []),
    [borrador, guardado],
  )

  // Avisa si se intenta cerrar la pestaña con cambios sin aplicar.
  useEffect(() => {
    if (cambiados.length === 0) return
    const alSalir = (ev) => ev.preventDefault()
    window.addEventListener('beforeunload', alSalir)
    return () => window.removeEventListener('beforeunload', alSalir)
  }, [cambiados])

  const cambiar = (campo, valor) => setBorrador((prev) => ({ ...prev, [campo]: valor }))

  const guardar = async () => {
    setGuardando(true)
    try {
      const cuerpo = Object.fromEntries(cambiados.map((c) => [c, borrador[c]]))
      const datos = await api('/api/configuracion/', { metodo: 'PATCH', cuerpo })
      setGuardado(datos)
      setBorrador(datos)
      avisar.exito('Aplicado. La linea ya esta inspeccionando con estos valores.')
    } catch (e) {
      avisar.error(e.message)
    } finally {
      setGuardando(false)
    }
  }

  if (cargando) {
    return (
      <div className="max-w-3xl space-y-4">
        <EsqueletoTarjeta lineas={2} />
        <EsqueletoTarjeta lineas={6} />
      </div>
    )
  }
  if (!borrador) {
    return (
      <p className="flex items-center gap-2 text-red-400">
        <AlertTriangle className="h-4 w-4" /> No se pudo cargar la configuracion.
      </p>
    )
  }

  return (
    <div className="max-w-3xl space-y-4 pb-24">
      <p className="text-sm text-slate-400">
        Los cambios se aplican en la linea en pocos segundos, sin detener la inspeccion.
      </p>

      {GRUPOS.map((grupo) => (
        <Tarjeta key={grupo.titulo} titulo={grupo.titulo} descripcion={grupo.descripcion}>
          {grupo.campos.map((campo) =>
            CAMPOS[campo].opciones ? (
              <div key={campo} className="border-t border-slate-800 py-4 first:border-t-0 first:pt-0">
                <CampoSelect
                  etiqueta={CAMPOS[campo].etiqueta}
                  ayuda={guardado.ayuda?.[campo]}
                  opciones={CAMPOS[campo].opciones}
                  value={borrador[campo]}
                  onChange={(e) => {
                    const crudo = e.target.value
                    cambiar(campo, campo === 'tamano_imagen' ? Number(crudo) : crudo)
                  }}
                />
              </div>
            ) : (
              <Deslizador
                key={campo}
                campo={campo}
                valor={borrador[campo]}
                ayuda={guardado.ayuda?.[campo]}
                cambiado={cambiados.includes(campo)}
                onCambio={cambiar}
              />
            ),
          )}
        </Tarjeta>
      ))}

      {/* Barra fija: el formulario es largo y el boton tiene que estar siempre a mano. */}
      <div className="fixed inset-x-0 bottom-0 z-20 border-t border-slate-800 bg-slate-900/95 p-3 backdrop-blur lg:left-64">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-3">
          <Boton
            icono={Save}
            onClick={guardar}
            cargando={guardando}
            disabled={cambiados.length === 0}
          >
            Aplicar a la linea
          </Boton>
          <Boton
            icono={RotateCcw}
            variante="contorno"
            onClick={() => setBorrador(guardado)}
            disabled={cambiados.length === 0}
          >
            Descartar
          </Boton>
          <span className="text-xs text-slate-500">
            {cambiados.length > 0
              ? `${cambiados.length} parametro(s) sin aplicar`
              : `Version ${guardado.version} · ${
                  guardado.actualizado_en
                    ? new Date(guardado.actualizado_en).toLocaleString()
                    : 'sin cambios aun'
                }`}
          </span>
        </div>
      </div>
    </div>
  )
}
