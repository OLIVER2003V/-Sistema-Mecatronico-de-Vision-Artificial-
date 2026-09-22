// Historial de lotes cerrados con inspección interactiva de métricas al hacer clic.
import { BarChart2, Calendar, CheckCircle, Droplets, ExternalLink, Loader2, Package, ShieldAlert, XCircle } from 'lucide-react'
import { useState } from 'react'

import { api } from '../api/cliente.js'
import Boton from './ui/Boton.jsx'
import EstadoVacio from './ui/EstadoVacio.jsx'
import Insignia from './ui/Insignia.jsx'
import Modal from './ui/Modal.jsx'
import Tarjeta from './ui/Tarjeta.jsx'

function fecha(valor) {
  return valor ? new Date(valor).toLocaleString() : '—'
}

export default function LotesTable({ lotes }) {
  const [loteSeleccionado, setLoteSeleccionado] = useState(null)
  const [metricas, setMetricas] = useState(null)
  const [cargandoMetricas, setCargandoMetricas] = useState(false)

  const finalizados = (lotes ?? []).filter((l) => l.estado === 'FINALIZADO')

  const abrirDetalleLote = async (lote) => {
    setLoteSeleccionado(lote)
    setCargandoMetricas(true)
    setMetricas(null)
    try {
      const data = await api(`/api/kpis/?lote=${lote.id}`)
      setMetricas(data)
    } catch (e) {
      console.error('Error cargando métricas del lote:', e)
    } finally {
      setCargandoMetricas(false)
    }
  }

  return (
    <>
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
                  <th scope="col" className="px-2 py-2">Lote</th>
                  <th scope="col" className="px-2 py-2">Botellas</th>
                  <th scope="col" className="hidden px-2 py-2 sm:table-cell">Inicio</th>
                  <th scope="col" className="hidden px-2 py-2 md:table-cell">Fin</th>
                  <th scope="col" className="px-2 py-2">Estado</th>
                  <th scope="col" className="px-2 py-2 text-right">Acción</th>
                </tr>
              </thead>
              <tbody>
                {finalizados.map((l) => (
                  <tr
                    key={l.id}
                    onClick={() => abrirDetalleLote(l)}
                    className="group cursor-pointer border-b border-slate-800 text-slate-200 transition-colors last:border-0 hover:bg-slate-800/60"
                  >
                    <td className="px-2 py-2.5 font-mono font-medium text-cyan-400 group-hover:underline">
                      {l.correlativo}
                    </td>
                    <td className="cifra px-2 py-2.5">
                      {l.total_inspecciones}/{l.capacidad_lote}
                    </td>
                    <td className="hidden px-2 py-2.5 text-slate-400 sm:table-cell">
                      {fecha(l.fecha_inicio)}
                    </td>
                    <td className="hidden px-2 py-2.5 text-slate-400 md:table-cell">
                      {fecha(l.fecha_fin)}
                    </td>
                    <td className="px-2 py-2.5">
                      <Insignia tono="neutro">Finalizado</Insignia>
                    </td>
                    <td className="px-2 py-2.5 text-right">
                      <span className="inline-flex items-center text-xs font-medium text-cyan-400 opacity-80 group-hover:opacity-100">
                        Ver Métricas <BarChart2 className="ml-1 h-3.5 w-3.5" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Tarjeta>

      {loteSeleccionado && (
        <Modal
          titulo={`Análisis del Lote: ${loteSeleccionado.correlativo}`}
          ancho="lg"
          onCerrar={() => setLoteSeleccionado(null)}
        >
          <div className="space-y-5 p-4">
            {/* Header del Lote */}
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-slate-950 p-4 border border-slate-800">
              <div>
                <span className="text-xs uppercase tracking-wide text-slate-500">Código de Lote</span>
                <h3 className="font-mono text-xl font-bold text-cyan-400">{loteSeleccionado.correlativo}</h3>
                <p className="text-xs text-slate-400 flex items-center gap-1 mt-1">
                  <Calendar className="h-3.5 w-3.5 text-slate-500" />
                  {fecha(loteSeleccionado.fecha_inicio)} — {fecha(loteSeleccionado.fecha_fin)}
                </p>
              </div>
              <div className="text-right">
                <Insignia tono="neutro">LOTE FINALIZADO</Insignia>
                <p className="mt-1 text-sm font-mono text-slate-300">
                  {loteSeleccionado.total_inspecciones} / {loteSeleccionado.capacidad_lote} Botellas
                </p>
              </div>
            </div>

            {cargandoMetricas ? (
              <div className="flex h-40 items-center justify-center space-x-2 text-cyan-400">
                <Loader2 className="h-6 w-6 animate-spin" />
                <span className="text-sm">Cargando métricas analíticas del lote...</span>
              </div>
            ) : metricas ? (
              <>
                {/* KPIs principales */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3">
                    <span className="text-xs text-emerald-400 font-medium">Aprobación (Yield)</span>
                    <p className="text-2xl font-bold text-emerald-400 mt-1">{metricas.yield_rate}%</p>
                    <span className="text-[10px] text-emerald-500/80">Botellas aptas</span>
                  </div>
                  <div className="rounded-xl border border-rose-500/20 bg-rose-950/20 p-3">
                    <span className="text-xs text-rose-400 font-medium">Rechazos (Mermas)</span>
                    <p className="text-2xl font-bold text-rose-400 mt-1">{metricas.reject_rate}%</p>
                    <span className="text-[10px] text-rose-500/80">Botellas descartadas</span>
                  </div>
                  <div className="col-span-2 rounded-xl border border-slate-800 bg-slate-950 p-3 sm:col-span-1">
                    <span className="text-xs text-slate-400 font-medium">Cadencia Real</span>
                    <p className="text-2xl font-bold text-cyan-400 mt-1">{metricas.cadencia_bpm} <span className="text-xs font-normal text-slate-400">BPM</span></p>
                    <span className="text-[10px] text-slate-500">Teórica: {metricas.cadencia_teorica_bpm} BPM</span>
                  </div>
                </div>

                {/* Desglose de Conteos por Defecto */}
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3">
                  <h4 className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Desglose Físico del Lote</h4>
                  <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-emerald-400" />
                      <div>
                        <p className="text-xs text-slate-400">Aceptadas</p>
                        <p className="font-semibold text-slate-100">{metricas.conteos?.aceptadas ?? 0}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Droplets className="h-4 w-4 text-amber-400" />
                      <div>
                        <p className="text-xs text-slate-400">Nivel Bajo</p>
                        <p className="font-semibold text-slate-100">{metricas.conteos?.llenado_bajo ?? 0}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-rose-400" />
                      <div>
                        <p className="text-xs text-slate-400">Sin Tapa</p>
                        <p className="font-semibold text-slate-100">{metricas.conteos?.sin_tapa ?? 0}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="h-4 w-4 text-rose-400" />
                      <div>
                        <p className="text-xs text-slate-400">Sin Etiqueta</p>
                        <p className="font-semibold text-slate-100">{metricas.conteos?.sin_etiqueta ?? 0}</p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Botón a la Galería de Mermas filtrada */}
                <div className="flex justify-end pt-2">
                  <a
                    href={`/mermas`}
                    className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-4 py-2 text-xs font-semibold text-white transition-colors hover:bg-cyan-500"
                  >
                    Ver Fotografías de Mermas de este Lote <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
              </>
            ) : (
              <p className="text-center text-xs text-slate-500 py-4">No se pudieron cargar las métricas de este lote.</p>
            )}
          </div>
        </Modal>
      )}
    </>
  )
}

