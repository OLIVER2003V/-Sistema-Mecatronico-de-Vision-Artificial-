// Filtro de navegacion del lado del cliente. NO es la seguridad del sistema:
// esa la aplica el backend en cada endpoint (cuentas/permisos.py). Esto solo
// evita que alguien caiga en una pantalla vacia llena de errores 403.
import { Factory, ShieldAlert } from 'lucide-react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { useSesion } from '../hooks/useSesion.jsx'
import Boton from './ui/Boton.jsx'

export default function RutaProtegida({ permiso, children }) {
  const { sesion, cargando, puede } = useSesion()
  const ubicacion = useLocation()
  const navegar = useNavigate()

  if (cargando) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3">
        <Factory className="h-10 w-10 animate-pulse text-cyan-500/60" />
        <p className="text-sm text-slate-500">Abriendo sesion...</p>
      </div>
    )
  }

  if (!sesion) {
    // Se recuerda a donde queria ir para volver ahi despues de entrar.
    return <Navigate to="/entrar" state={{ desde: ubicacion.pathname }} replace />
  }

  if (permiso && !puede(permiso)) {
    return (
      <div className="mx-auto mt-16 max-w-md rounded-xl border border-amber-500/30 bg-amber-500/5 p-6 text-center">
        <ShieldAlert className="mx-auto mb-3 h-10 w-10 text-amber-400" />
        <h2 className="mb-1 text-lg font-semibold text-slate-100">Sin permiso</h2>
        <p className="mb-4 text-sm text-slate-400">
          Su rol no tiene acceso a esta pantalla. Si cree que es un error, hable con el
          administrador de sistemas.
        </p>
        <Boton variante="contorno" onClick={() => navegar('/', { replace: true })}>
          Ir a mi pantalla de inicio
        </Boton>
      </div>
    )
  }

  return children
}
