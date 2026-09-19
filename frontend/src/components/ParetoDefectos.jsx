// Pareto de defectos: que falla mas.
//
// Antes era un donut. Un donut obliga a comparar angulos, que es justo lo que
// peor hace el ojo; y con tres porciones no aporta nada que no diga una lista
// ordenada. La tarea aca es comparar magnitudes, asi que van barras
// horizontales ordenadas de mayor a menor, con el numero al lado.
//
// Barras en una sola rampa de azul: el largo ya codifica la magnitud, el
// color no tiene que repetirla. La identidad la da la etiqueta, no el color.
import { PieChart } from 'lucide-react'

import EstadoVacio from './ui/EstadoVacio.jsx'
import Tarjeta from './ui/Tarjeta.jsx'
import { RAMPA_DEFECTO } from './ui/colores.js'

const ETIQUETAS = { SIN_ETIQUETA: 'Sin etiqueta', SIN_TAPA: 'Sin tapa', OTRO: 'Otro defecto' }

export default function ParetoDefectos({ defectos }) {
  const filas = Object.entries(defectos ?? {})
    .map(([clave, n]) => ({ clave, nombre: ETIQUETAS[clave] ?? clave, n }))
    .sort((a, b) => b.n - a.n)

  const total = filas.reduce((suma, f) => suma + f.n, 0)

  if (total === 0) {
    return (
      <Tarjeta titulo="Defectos por tipo" icono={PieChart}>
        <EstadoVacio
          icono={PieChart}
          titulo="Sin defectos en este lote"
          mensaje="Cuando la linea rechace una botella por defecto fisico, aparece el reparto aca."
        />
      </Tarjeta>
    )
  }

  const mayor = filas[0].n

  return (
    <Tarjeta titulo="Defectos por tipo" descripcion={`${total} botellas con defecto fisico`} icono={PieChart}>
      <ul className="space-y-3">
        {filas.map((fila, i) => {
          const proporcion = Math.round((fila.n / mayor) * 100)
          const porcentaje = Math.round((fila.n / total) * 100)
          return (
            <li key={fila.clave}>
              <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
                <span className="truncate text-slate-300">{fila.nombre}</span>
                <span className="cifra flex-shrink-0 text-slate-400">
                  <span className="font-semibold text-slate-100">{fila.n}</span> · {porcentaje}%
                </span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${proporcion}%`,
                    backgroundColor: RAMPA_DEFECTO[Math.min(i, RAMPA_DEFECTO.length - 1)],
                  }}
                />
              </div>
            </li>
          )
        })}
      </ul>
    </Tarjeta>
  )
}
