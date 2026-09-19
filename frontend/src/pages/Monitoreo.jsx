// Pantalla del Operador de planta.
//
// Orden pensado para alguien parado frente a la faja: primero si esta andando
// y como pararla, despues cuanto lleva producido, despues los contadores, y
// al final el detalle (camara y ultimas botellas).
import BatchTracker from '../components/BatchTracker.jsx'
import CameraView from '../components/CameraView.jsx'
import ContadoresLinea from '../components/ContadoresLinea.jsx'
import ControlFaja from '../components/ControlFaja.jsx'
import EventosFeed from '../components/EventosFeed.jsx'
import { useTelemetria } from '../hooks/useTelemetria.jsx'

export default function Monitoreo() {
  const { lote, kpis, camaraFrame, estadoFaja, eventos, cargando } = useTelemetria()
  const enCurso = lote ?? kpis?.lote

  return (
    <div className="space-y-4">
      <ControlFaja estado={estadoFaja} />
      <BatchTracker lote={enCurso} cargando={cargando} />
      <ContadoresLinea
        conteos={kpis?.conteos}
        total={kpis?.total_inspecciones ?? 0}
        cargando={cargando}
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CameraView frame={camaraFrame} />
        <EventosFeed eventos={eventos} />
      </div>
    </div>
  )
}
