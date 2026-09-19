// Vista de la camara de la estacion 1. No es video: son fotos seguidas que
// manda vision/ cada ~100 ms. Se aclara para que nadie la lea como un stream
// en tiempo real y saque conclusiones de lo que "no vio".
import { Video, VideoOff } from 'lucide-react'
import { useEffect, useState } from 'react'

import Tarjeta from './ui/Tarjeta.jsx'

// Si no llega un cuadro nuevo en este tiempo, la imagen que se ve es vieja.
const CONGELADA_MS = 4000

export default function CameraView({ frame }) {
  const [congelada, setCongelada] = useState(false)

  useEffect(() => {
    if (!frame) return
    setCongelada(false)
    const id = setTimeout(() => setCongelada(true), CONGELADA_MS)
    return () => clearTimeout(id)
  }, [frame])

  return (
    <Tarjeta
      titulo="Camara de la estacion 1"
      icono={Video}
      acciones={
        congelada && (
          <span className="flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-xs text-amber-300">
            <VideoOff className="h-3 w-3" /> imagen detenida
          </span>
        )
      }
    >
      {frame ? (
        <img
          src={frame}
          alt="Vista en vivo de la camara de inspeccion"
          className={`w-full rounded-lg bg-black transition-opacity ${congelada ? 'opacity-50' : ''}`}
        />
      ) : (
        <div className="flex aspect-video items-center justify-center rounded-lg bg-slate-950 px-4 text-center text-sm text-slate-500">
          Esperando imagen del modulo de vision. Verifique que inspector_botellas.py este corriendo.
        </div>
      )}
      <p className="mt-2 text-xs text-slate-500">
        Vista de referencia a pocos cuadros por segundo, no es video continuo.
      </p>
    </Tarjeta>
  )
}
