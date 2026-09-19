// Avance del lote en curso. Ademas del porcentaje muestra cuantas botellas
// faltan: es el dato con el que el operador decide si le da tiempo a hacer
// otra cosa antes del cambio de lote.
import { Package } from 'lucide-react'

import { Esqueleto } from './ui/Esqueleto.jsx'

export default function BatchTracker({ lote, cargando = false }) {
  const total = lote?.total_inspecciones ?? 0
  const capacidad = lote?.capacidad_lote ?? 0
  const pct = capacidad ? Math.min(100, Math.round((total / capacidad) * 100)) : 0
  const faltan = Math.max(0, capacidad - total)

  return (
    <section className="rounded-xl border border-slate-800 bg-slate-800/40 p-4 sm:p-5">
      <div className="mb-2.5 flex flex-wrap items-baseline justify-between gap-2">
        <span className="flex items-center gap-2 text-sm text-slate-400">
          <Package className="h-4 w-4" /> Lote en curso
        </span>
        {cargando ? (
          <Esqueleto className="h-6 w-36" />
        ) : (
          <span className="font-mono text-lg font-semibold text-cyan-400">
            {lote?.correlativo ?? 'sin lote abierto'}
          </span>
        )}
      </div>

      <div
        className="h-3 w-full overflow-hidden rounded-full bg-slate-700"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Avance del lote"
      >
        <div
          className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="mt-2 flex flex-wrap justify-between gap-2 text-sm">
        <span className="text-slate-400">
          {capacidad ? (
            <>
              Faltan <span className="cifra font-semibold text-slate-200">{faltan}</span> botellas
              para cerrar
            </>
          ) : (
            'Se abre solo con la primera botella inspeccionada'
          )}
        </span>
        <span className="cifra text-slate-300">
          {total} / {capacidad || '—'} ({pct}%)
        </span>
      </div>
    </section>
  )
}
