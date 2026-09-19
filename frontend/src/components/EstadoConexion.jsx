// Salud del enlace con la linea, en la cabecera de todas las pantallas.
//
// Distingue tres cosas que no son lo mismo: no hay conexion con el servidor,
// hay conexion pero no llegan botellas, o la linea esta produciendo. En
// pantalla chica queda solo el punto de color (con title para el detalle).
import { useEffect, useState } from 'react'

const SIN_DATOS_S = 15

function useHaceSegundos(marca) {
  const [ahora, setAhora] = useState(Date.now())
  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  if (!marca) return null
  return Math.max(0, Math.floor((ahora - marca) / 1000))
}

export default function EstadoConexion({ conectado, ultimaSenal }) {
  const segundos = useHaceSegundos(ultimaSenal)

  let corto = 'Sin conexion'
  let largo = 'No se puede hablar con el servidor'
  let punto = 'bg-red-500'
  let texto = 'text-red-400'
  let latido = false

  if (conectado && segundos == null) {
    corto = 'Conectado'
    largo = 'Conectado, todavia no llego ninguna botella'
    punto = 'bg-cyan-400'
    texto = 'text-cyan-300'
  } else if (conectado && segundos <= SIN_DATOS_S) {
    corto = segundos < 2 ? 'Linea activa' : `Linea activa · hace ${segundos}s`
    largo = `Ultima botella hace ${segundos}s`
    punto = 'bg-emerald-400'
    texto = 'text-emerald-300'
    latido = true
  } else if (conectado) {
    corto = `Sin datos hace ${segundos}s`
    largo = `Conectado, pero no llegan botellas hace ${segundos}s`
    punto = 'bg-amber-400'
    texto = 'text-amber-300'
  }

  return (
    <div
      title={largo}
      role="status"
      aria-label={largo}
      className="flex items-center gap-2 rounded-full border border-slate-700 px-2.5 py-1.5"
    >
      <span className="relative flex h-2.5 w-2.5 flex-shrink-0">
        {latido && (
          <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${punto}`} />
        )}
        <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${punto}`} />
      </span>
      <span className={`hidden text-xs font-medium md:inline ${texto}`}>{corto}</span>
    </div>
  )
}
