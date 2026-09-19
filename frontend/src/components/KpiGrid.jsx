// Indicadores del lote para el Supervisor de calidad.
//
// El rendimiento y la merma llevan color segun que tan lejos estan de lo
// aceptable: un 92% de rendimiento no se lee igual que un 62%, y en una
// tarjeta gris los dos parecen lo mismo.
import { AlertTriangle, CheckCircle2, Droplets, Gauge, XCircle } from 'lucide-react'

import { Esqueleto } from './ui/Esqueleto.jsx'

const ETIQUETAS_DEFECTO = { SIN_ETIQUETA: 'Sin etiqueta', SIN_TAPA: 'Sin tapa', OTRO: 'Otro' }

function color(valor, { bueno, regular }, invertido = false) {
  if (valor == null) return 'text-slate-300'
  const ok = invertido ? valor <= bueno : valor >= bueno
  const medio = invertido ? valor <= regular : valor >= regular
  if (ok) return 'text-emerald-300'
  if (medio) return 'text-amber-300'
  return 'text-red-300'
}

function Tarjeta({ icono: Icono, iconoColor, etiqueta, children, cargando }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-800/40 p-4">
      <div className="mb-2 flex items-center gap-2">
        <Icono className={`h-4 w-4 flex-shrink-0 ${iconoColor}`} />
        <span className="truncate text-xs uppercase tracking-wide text-slate-400">{etiqueta}</span>
      </div>
      {cargando ? <Esqueleto className="h-8 w-20" /> : children}
    </div>
  )
}

export default function KpiGrid({ kpis, cargando = false }) {
  const defecto = kpis?.defecto_predominante
  const real = kpis?.cadencia_bpm
  const teorica = kpis?.cadencia_teorica_bpm
  const aprovechamiento = real != null && teorica ? Math.min(100, Math.round((real / teorica) * 100)) : null

  return (
    <section className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      <Tarjeta icono={CheckCircle2} iconoColor="text-emerald-400" etiqueta="Rendimiento" cargando={cargando}>
        <p className={`cifra text-3xl font-bold ${color(kpis?.yield_rate, { bueno: 90, regular: 75 })}`}>
          {kpis?.yield_rate != null ? `${kpis.yield_rate}%` : '—'}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">botellas aprobadas</p>
      </Tarjeta>

      <Tarjeta icono={XCircle} iconoColor="text-red-400" etiqueta="Merma global" cargando={cargando}>
        <p className={`cifra text-3xl font-bold ${color(kpis?.reject_rate, { bueno: 10, regular: 25 }, true)}`}>
          {kpis?.reject_rate != null ? `${kpis.reject_rate}%` : '—'}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">
          {kpis?.conteos?.rechazadas_total ?? 0} botellas descartadas
        </p>
      </Tarjeta>

      <Tarjeta icono={Gauge} iconoColor="text-cyan-400" etiqueta="Cadencia real" cargando={cargando}>
        <p className="cifra text-3xl font-bold text-white">
          {real != null ? real : '—'}
          <span className="ml-1 text-base font-normal text-slate-400">BPM</span>
        </p>
        {aprovechamiento != null && (
          <>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-cyan-500 transition-all duration-500"
                style={{ width: `${aprovechamiento}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {aprovechamiento}% de las {teorica} BPM teoricas
            </p>
          </>
        )}
      </Tarjeta>

      <Tarjeta icono={Droplets} iconoColor="text-amber-400" etiqueta="Llenado bajo" cargando={cargando}>
        <p className={`cifra text-3xl font-bold ${color(kpis?.tasa_llenado_bajo, { bueno: 5, regular: 15 }, true)}`}>
          {kpis?.tasa_llenado_bajo != null ? `${kpis.tasa_llenado_bajo}%` : '—'}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">{kpis?.conteos?.llenado_bajo ?? 0} botellas</p>
      </Tarjeta>

      <Tarjeta
        icono={AlertTriangle}
        iconoColor="text-amber-400"
        etiqueta="Defecto predominante"
        cargando={cargando}
      >
        <p className="truncate text-xl font-bold text-white">
          {defecto ? (ETIQUETAS_DEFECTO[defecto.tipo_defecto] ?? defecto.tipo_defecto) : '—'}
        </p>
        <p className="mt-0.5 text-xs text-slate-500">
          {defecto ? `${defecto.porcentaje}% de las defectuosas` : 'sin defectos en este lote'}
        </p>
      </Tarjeta>
    </section>
  )
}
