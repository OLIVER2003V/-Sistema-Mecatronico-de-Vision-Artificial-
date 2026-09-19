// Ultimas botellas inspeccionadas, la mas nueva arriba. Sirve para confirmar
// que la linea esta viva y para pescar una racha de rechazos apenas empieza.
import { AlertTriangle, CheckCircle2, Droplets, History } from 'lucide-react'

import EstadoVacio from './ui/EstadoVacio.jsx'
import Tarjeta from './ui/Tarjeta.jsx'

const ASPECTO = {
  ACEPTADA: { Icono: CheckCircle2, color: 'text-emerald-400', texto: 'Aprobada' },
  DEFECTUOSA: { Icono: AlertTriangle, color: 'text-red-400', texto: 'Defectuosa' },
  LLENADO_BAJO: { Icono: Droplets, color: 'text-amber-400', texto: 'Nivel bajo' },
}

const MOTIVO = { SIN_ETIQUETA: 'sin etiqueta', SIN_TAPA: 'sin tapa', OTRO: 'otro defecto' }

export default function EventosFeed({ eventos }) {
  const lista = eventos ?? []

  return (
    <Tarjeta titulo="Ultimas botellas" icono={History}>
      {lista.length === 0 ? (
        <EstadoVacio
          icono={History}
          titulo="Todavia no llego ninguna botella"
          mensaje="Cada inspeccion aparece aca apenas la faja la procesa."
        />
      ) : (
        <ul className="divide-y divide-slate-800">
          {lista.map((ev) => {
            const { Icono, color, texto } = ASPECTO[ev.resultado] ?? ASPECTO.ACEPTADA
            const motivo = ev.tipo_defecto ? (MOTIVO[ev.tipo_defecto] ?? ev.tipo_defecto) : null
            return (
              <li key={ev.id} className="flex items-center gap-2.5 py-2 text-sm">
                <Icono className={`h-4 w-4 flex-shrink-0 ${color}`} />
                <span className="cifra flex-shrink-0 font-mono text-xs text-slate-500">
                  {new Date(ev.fecha_hora).toLocaleTimeString()}
                </span>
                <span className="truncate text-slate-200">
                  {texto}
                  {motivo && <span className="text-slate-400"> · {motivo}</span>}
                </span>
                {ev.confianza_ia != null && (
                  <span className="cifra ml-auto flex-shrink-0 text-xs text-slate-500">
                    {Math.round(ev.confianza_ia)}%
                  </span>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </Tarjeta>
  )
}
