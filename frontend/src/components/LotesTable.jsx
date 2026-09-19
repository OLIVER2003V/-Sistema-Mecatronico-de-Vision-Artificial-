// Historial de lotes cerrados.
//
// En pantalla chica las columnas menos importantes se ocultan en vez de
// obligar a arrastrar la tabla de costado (el supervisor consulta esto desde
// el celular en planta).
import { Package } from 'lucide-react'

import EstadoVacio from './ui/EstadoVacio.jsx'
import Insignia from './ui/Insignia.jsx'
import Tarjeta from './ui/Tarjeta.jsx'

function fecha(valor) {
  return valor ? new Date(valor).toLocaleString() : '—'
}

export default function LotesTable({ lotes }) {
  const finalizados = (lotes ?? []).filter((l) => l.estado === 'FINALIZADO')

  return (
    <Tarjeta titulo="Historial de lotes" icono={Package}>
      {finalizados.length === 0 ? (
        <EstadoVacio
          icono={Package}
          titulo="Aun no hay lotes cerrados"
          mensaje="Un lote se cierra solo al llegar a su capacidad, o a mano desde la pantalla de lotes."
        />
      ) : (
        <div className="-mx-1 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-400">
              <tr className="border-b border-slate-700">
                <th scope="col" className="px-1 py-2">Lote</th>
                <th scope="col" className="px-1 py-2">Botellas</th>
                <th scope="col" className="hidden px-1 py-2 sm:table-cell">Inicio</th>
                <th scope="col" className="hidden px-1 py-2 md:table-cell">Fin</th>
                <th scope="col" className="px-1 py-2">Estado</th>
              </tr>
            </thead>
            <tbody>
              {finalizados.map((l) => (
                <tr
                  key={l.id}
                  className="border-b border-slate-800 text-slate-200 transition-colors last:border-0 hover:bg-slate-800/40"
                >
                  <td className="px-1 py-2.5 font-mono">{l.correlativo}</td>
                  <td className="cifra px-1 py-2.5">
                    {l.total_inspecciones}/{l.capacidad_lote}
                  </td>
                  <td className="hidden px-1 py-2.5 text-slate-400 sm:table-cell">
                    {fecha(l.fecha_inicio)}
                  </td>
                  <td className="hidden px-1 py-2.5 text-slate-400 md:table-cell">
                    {fecha(l.fecha_fin)}
                  </td>
                  <td className="px-1 py-2.5">
                    <Insignia tono="neutro">Finalizado</Insignia>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Tarjeta>
  )
}
