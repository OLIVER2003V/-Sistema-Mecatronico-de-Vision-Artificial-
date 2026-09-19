// Contadores del lote en curso.
//
// Es lo que el operador mira de lejos, parado frente a la faja, asi que los
// tres numeros que pide la HU (aprobadas / defectuosas / nivel bajo) van en
// cifras grandes y con el color del semaforo. El desglose por tipo de
// defecto queda abajo, en chico: es informacion de consulta, no de vigilancia.
import { Ban, CheckCircle2, Droplets, Tag, XCircle } from 'lucide-react'

import { Esqueleto } from './ui/Esqueleto.jsx'

function Contador({ icono: Icono, etiqueta, valor, total, tono, cargando }) {
  const porcentaje = total ? Math.round((valor / total) * 100) : 0

  return (
    <div className={`rounded-xl border bg-slate-900/60 p-4 sm:p-5 ${tono.borde}`}>
      <div className="mb-1 flex items-center gap-2">
        <Icono className={`h-5 w-5 flex-shrink-0 ${tono.icono}`} />
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400 sm:text-sm">
          {etiqueta}
        </span>
      </div>

      {cargando ? (
        <Esqueleto className="h-12 w-24" />
      ) : (
        <div className="flex items-baseline gap-2">
          <span className={`cifra text-5xl font-bold leading-none sm:text-6xl ${tono.cifra}`}>
            {valor ?? 0}
          </span>
          {total > 0 && <span className="cifra text-lg text-slate-500">{porcentaje}%</span>}
        </div>
      )}

      {/* Barra de proporcion: de un vistazo se ve el reparto sin leer numeros. */}
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-500 ${tono.barra}`}
          style={{ width: `${porcentaje}%` }}
        />
      </div>
    </div>
  )
}

function Desglose({ icono: Icono, etiqueta, valor, color }) {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2.5">
      <Icono className={`h-4 w-4 flex-shrink-0 ${color}`} />
      <span className="cifra text-xl font-bold text-white">{valor ?? 0}</span>
      <span className="truncate text-xs text-slate-400">{etiqueta}</span>
    </div>
  )
}

const TONOS = {
  aprobadas: {
    borde: 'border-emerald-500/30',
    icono: 'text-emerald-400',
    cifra: 'text-emerald-300',
    barra: 'bg-emerald-500',
  },
  defectuosas: {
    borde: 'border-red-500/30',
    icono: 'text-red-400',
    cifra: 'text-red-300',
    barra: 'bg-red-500',
  },
  nivel: {
    borde: 'border-amber-500/30',
    icono: 'text-amber-400',
    cifra: 'text-amber-300',
    barra: 'bg-amber-500',
  },
}

export default function ContadoresLinea({ conteos, total = 0, cargando = false, compacto = false }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Contador
          icono={CheckCircle2}
          etiqueta="Aprobadas"
          valor={conteos?.aceptadas}
          total={total}
          tono={TONOS.aprobadas}
          cargando={cargando}
        />
        <Contador
          icono={XCircle}
          etiqueta="Defectuosas"
          valor={conteos?.defectuosa}
          total={total}
          tono={TONOS.defectuosas}
          cargando={cargando}
        />
        <Contador
          icono={Droplets}
          etiqueta="Nivel bajo"
          valor={conteos?.llenado_bajo}
          total={total}
          tono={TONOS.nivel}
          cargando={cargando}
        />
      </div>

      {!compacto && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <Desglose icono={Ban} etiqueta="Sin tapa" valor={conteos?.sin_tapa} color="text-orange-400" />
          <Desglose icono={Tag} etiqueta="Sin etiqueta" valor={conteos?.sin_etiqueta} color="text-amber-400" />
          <Desglose icono={XCircle} etiqueta="Otro defecto" valor={conteos?.otro_defecto} color="text-slate-400" />
        </div>
      )}
    </div>
  )
}
