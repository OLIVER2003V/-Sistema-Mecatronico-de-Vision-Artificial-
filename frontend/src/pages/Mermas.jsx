// Galeria y registro de mermas: el historial visual de todo lo que la linea
// descarto, con la captura que tomo el modulo de vision en el momento.
//
// El detalle se abre en un modal que ademas se recorre con las flechas del
// teclado: revisar veinte capturas seguidas a golpe de clic es tedioso.
import {
  ChevronLeft,
  ChevronRight,
  Droplets,
  Filter,
  ImageOff,
  Images,
  Loader2,
  XCircle,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { api, filas } from '../api/cliente.js'
import Boton from '../components/ui/Boton.jsx'
import { CampoSelect, CampoTexto } from '../components/ui/Campo.jsx'
import EstadoVacio from '../components/ui/EstadoVacio.jsx'
import Insignia from '../components/ui/Insignia.jsx'
import Modal from '../components/ui/Modal.jsx'
import Tarjeta from '../components/ui/Tarjeta.jsx'
import { useAvisos } from '../hooks/useAvisos.jsx'

const FILTROS_VACIOS = {
  desde: '',
  hasta: '',
  hora_desde: '',
  hora_hasta: '',
  tipo_defecto: '',
  resultado: '',
}

const HORAS = Array.from({ length: 24 }, (_, h) => ({
  valor: String(h),
  texto: `${String(h).padStart(2, '0')}:00`,
}))

function InsigniaMerma({ fila }) {
  const esLlenado = fila.resultado === 'LLENADO_BAJO'
  return (
    <Insignia
      tono={esLlenado ? 'alerta' : 'peligro'}
      icono={esLlenado ? Droplets : XCircle}
    >
      {esLlenado ? 'Nivel bajo' : (fila.tipo_defecto_nombre || fila.resultado_nombre)}
    </Insignia>
  )
}

function Ficha({ fila, onAbrir }) {
  return (
    <button
      onClick={onAbrir}
      className="group overflow-hidden rounded-xl border border-slate-800 bg-slate-800/40 text-left transition-colors hover:border-cyan-500/60"
    >
      <div className="aspect-video overflow-hidden bg-slate-950">
        {fila.imagen_url ? (
          <img
            src={fila.imagen_url}
            alt={`Botella descartada el ${new Date(fila.fecha_hora).toLocaleString()}`}
            loading="lazy"
            className="h-full w-full object-contain transition-transform duration-200 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-slate-700">
            <ImageOff className="h-8 w-8" />
          </div>
        )}
      </div>
      <div className="space-y-1.5 p-3">
        <InsigniaMerma fila={fila} />
        <p className="text-xs text-slate-400">{new Date(fila.fecha_hora).toLocaleString()}</p>
        <p className="font-mono text-xs text-slate-600">{fila.lote_correlativo}</p>
      </div>
    </button>
  )
}

function Detalle({ fila, onCerrar, onAnterior, onSiguiente, hayAnterior, haySiguiente }) {
  // Flechas para recorrer la galeria sin volver a la grilla.
  useEffect(() => {
    const alTeclear = (ev) => {
      if (ev.key === 'ArrowLeft' && hayAnterior) onAnterior()
      if (ev.key === 'ArrowRight' && haySiguiente) onSiguiente()
    }
    document.addEventListener('keydown', alTeclear)
    return () => document.removeEventListener('keydown', alTeclear)
  }, [onAnterior, onSiguiente, hayAnterior, haySiguiente])

  const dato = (etiqueta, valor) =>
    valor == null || valor === '' ? null : (
      <div>
        <dt className="text-xs uppercase tracking-wide text-slate-500">{etiqueta}</dt>
        <dd className="text-sm text-slate-200">{valor}</dd>
      </div>
    )

  return (
    <Modal
      ancho="lg"
      titulo="Detalle de la merma"
      encabezado={<InsigniaMerma fila={fila} />}
      onCerrar={onCerrar}
    >
      <div className="relative bg-black">
        {fila.imagen_url ? (
          <img src={fila.imagen_url} alt="" className="max-h-[55vh] w-full object-contain" />
        ) : (
          <div className="flex h-48 items-center justify-center text-slate-700">
            <ImageOff className="h-10 w-10" />
          </div>
        )}
        <button
          onClick={onAnterior}
          disabled={!hayAnterior}
          aria-label="Merma anterior"
          className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-slate-900/80 p-2 text-slate-200 transition-opacity hover:bg-slate-800 disabled:opacity-0"
        >
          <ChevronLeft className="h-5 w-5" />
        </button>
        <button
          onClick={onSiguiente}
          disabled={!haySiguiente}
          aria-label="Merma siguiente"
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-slate-900/80 p-2 text-slate-200 transition-opacity hover:bg-slate-800 disabled:opacity-0"
        >
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>

      <dl className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3">
        {dato('Fecha y hora', new Date(fila.fecha_hora).toLocaleString())}
        {dato('Lote', fila.lote_correlativo)}
        {dato('Motivo', fila.tipo_defecto_nombre || fila.resultado_nombre)}
        {dato('Estacion de descarte', fila.estacion_nombre)}
        {dato(
          'Llenado medido',
          fila.nivel_llenado_detectado != null ? `${Math.round(fila.nivel_llenado_detectado)}%` : null,
        )}
        {dato('Certeza del modelo', fila.confianza_ia != null ? `${Math.round(fila.confianza_ia)}%` : null)}
      </dl>
      <p className="px-4 pb-4 text-xs text-slate-600">
        Use las flechas ← → para recorrer las capturas, Escape para cerrar.
      </p>
    </Modal>
  )
}

export default function Mermas() {
  const avisar = useAvisos()
  const [filtros, setFiltros] = useState(FILTROS_VACIOS)
  const [pagina, setPagina] = useState(1)
  const [datos, setDatos] = useState({ results: [], count: 0, next: null, previous: null })
  const [cargando, setCargando] = useState(true)
  const [indice, setIndice] = useState(null) // posicion abierta en el modal

  const cargar = useCallback(async () => {
    setCargando(true)
    const parametros = new URLSearchParams()
    Object.entries(filtros).forEach(([k, v]) => v !== '' && parametros.set(k, v))
    parametros.set('page', String(pagina))
    try {
      setDatos(await api(`/api/mermas/?${parametros.toString()}`))
    } catch (e) {
      avisar.error(e.message)
      setDatos({ results: [], count: 0, next: null, previous: null })
    } finally {
      setCargando(false)
    }
  }, [filtros, pagina, avisar])

  useEffect(() => {
    cargar()
  }, [cargar])

  const cambiar = (campo) => (ev) => {
    setFiltros((prev) => ({ ...prev, [campo]: ev.target.value }))
    setPagina(1) // un filtro nuevo invalida la pagina en la que estabamos
  }

  const resultados = filas(datos)
  const activos = Object.values(filtros).filter((v) => v !== '').length

  return (
    <div className="space-y-4">
      <Tarjeta
        titulo="Filtros"
        icono={Filter}
        acciones={
          activos > 0 && (
            <Boton
              variante="fantasma"
              tamano="sm"
              onClick={() => {
                setFiltros(FILTROS_VACIOS)
                setPagina(1)
              }}
            >
              Limpiar {activos} filtro(s)
            </Boton>
          )
        }
      >
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <CampoTexto etiqueta="Desde" type="date" value={filtros.desde} onChange={cambiar('desde')} />
          <CampoTexto etiqueta="Hasta" type="date" value={filtros.hasta} onChange={cambiar('hasta')} />
          <CampoSelect
            etiqueta="Motivo del descarte"
            value={filtros.resultado}
            onChange={cambiar('resultado')}
            opciones={[
              { valor: '', texto: 'Todos' },
              { valor: 'DEFECTUOSA', texto: 'Defecto fisico' },
              { valor: 'LLENADO_BAJO', texto: 'Nivel de llenado bajo' },
            ]}
          />
          <CampoSelect
            etiqueta="Tipo de defecto"
            value={filtros.tipo_defecto}
            onChange={cambiar('tipo_defecto')}
            opciones={[
              { valor: '', texto: 'Todos' },
              { valor: 'SIN_ETIQUETA', texto: 'Sin etiqueta' },
              { valor: 'SIN_TAPA', texto: 'Sin tapa' },
              { valor: 'OTRO', texto: 'Otro' },
            ]}
          />
          <CampoSelect
            etiqueta="Desde la hora"
            value={filtros.hora_desde}
            onChange={cambiar('hora_desde')}
            opciones={[{ valor: '', texto: 'Cualquiera' }, ...HORAS]}
          />
          <CampoSelect
            etiqueta="Hasta la hora"
            value={filtros.hora_hasta}
            onChange={cambiar('hora_hasta')}
            opciones={[
              { valor: '', texto: 'Cualquiera' },
              ...HORAS.map((h) => ({ ...h, texto: h.texto.replace(':00', ':59') })),
            ]}
          />
        </div>
      </Tarjeta>

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-400">
        <span className="flex items-center gap-2">
          {cargando && <Loader2 className="h-4 w-4 animate-spin" />}
          <span className="cifra">{datos.count ?? resultados.length}</span> descarte(s)
        </span>
        <div className="flex items-center gap-2">
          <Boton
            variante="contorno"
            tamano="sm"
            icono={ChevronLeft}
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
            disabled={!datos.previous || cargando}
          >
            Anterior
          </Boton>
          <span className="cifra px-1">Pagina {pagina}</span>
          <Boton
            variante="contorno"
            tamano="sm"
            onClick={() => setPagina((p) => p + 1)}
            disabled={!datos.next || cargando}
          >
            Siguiente <ChevronRight className="h-4 w-4" />
          </Boton>
        </div>
      </div>

      {!cargando && resultados.length === 0 ? (
        <EstadoVacio
          icono={Images}
          titulo={activos > 0 ? 'Ningun descarte coincide con estos filtros' : 'Todavia no hay botellas descartadas'}
          mensaje={
            activos > 0
              ? 'Pruebe ampliando el rango de fechas o quitando el tipo de defecto.'
              : 'Cada vez que la linea rechace una botella, la captura aparece aca.'
          }
          accion={
            activos > 0 && (
              <Boton
                variante="contorno"
                onClick={() => {
                  setFiltros(FILTROS_VACIOS)
                  setPagina(1)
                }}
              >
                Limpiar filtros
              </Boton>
            )
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {resultados.map((fila, i) => (
            <Ficha key={fila.id} fila={fila} onAbrir={() => setIndice(i)} />
          ))}
        </div>
      )}

      {indice !== null && resultados[indice] && (
        <Detalle
          fila={resultados[indice]}
          onCerrar={() => setIndice(null)}
          onAnterior={() => setIndice((i) => Math.max(0, i - 1))}
          onSiguiente={() => setIndice((i) => Math.min(resultados.length - 1, i + 1))}
          hayAnterior={indice > 0}
          haySiguiente={indice < resultados.length - 1}
        />
      )}
    </div>
  )
}
