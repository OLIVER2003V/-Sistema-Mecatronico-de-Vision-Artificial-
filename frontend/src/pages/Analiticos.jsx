// Pantalla del Supervisor de calidad: indicadores del lote, Pareto de
// defectos, produccion por hora e historial de lotes cerrados.
import ContadoresLinea from '../components/ContadoresLinea.jsx'
import KpiGrid from '../components/KpiGrid.jsx'
import LotesTable from '../components/LotesTable.jsx'
import ParetoDefectos from '../components/ParetoDefectos.jsx'
import TrendChart from '../components/TrendChart.jsx'
import { Esqueleto } from '../components/ui/Esqueleto.jsx'
import { useTelemetria } from '../hooks/useTelemetria.jsx'

export default function Analiticos() {
  const { kpis, tendencia, lotes, cargando } = useTelemetria()

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-400">
        {cargando ? (
          <Esqueleto className="h-4 w-64" />
        ) : (
          <>
            Lote{' '}
            <span className="font-mono font-medium text-cyan-400">
              {kpis?.lote?.correlativo ?? '—'}
            </span>{' '}
            · <span className="cifra">{kpis?.total_inspecciones ?? 0}</span> botellas inspeccionadas
          </>
        )}
      </p>

      <KpiGrid kpis={kpis} cargando={cargando} />
      <ContadoresLinea
        conteos={kpis?.conteos}
        total={kpis?.total_inspecciones ?? 0}
        cargando={cargando}
        compacto
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <ParetoDefectos defectos={kpis?.defectos} />
        </div>
        <div className="lg:col-span-2">
          <TrendChart tendencia={tendencia} />
        </div>
      </div>

      <LotesTable lotes={lotes} />
    </div>
  )
}
