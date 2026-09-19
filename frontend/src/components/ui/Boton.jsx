// Boton unico de la HMI. Antes cada pantalla repetia la misma cadena de
// clases y cada una manejaba el "cargando" a su manera.
import { Loader2 } from 'lucide-react'

const VARIANTES = {
  primario: 'bg-cyan-600 text-white hover:bg-cyan-500',
  peligro: 'bg-red-600 text-white hover:bg-red-500',
  exito: 'bg-emerald-600 text-white hover:bg-emerald-500',
  neutro: 'bg-slate-600 text-white hover:bg-slate-500',
  contorno: 'border border-slate-600 text-slate-200 hover:border-slate-400 hover:bg-slate-800',
  fantasma: 'text-slate-300 hover:bg-slate-800 hover:text-slate-100',
}

// 'grande' es para los botones de planta (marcha/paro): se aprietan con
// guantes y a veces en una pantalla tactil, asi que necesitan area.
const TAMANOS = {
  sm: 'px-2.5 py-1.5 text-xs gap-1',
  md: 'px-4 py-2 text-sm gap-1.5',
  grande: 'px-6 py-3.5 text-base font-semibold gap-2',
}

export default function Boton({
  children,
  icono: Icono,
  variante = 'primario',
  tamano = 'md',
  cargando = false,
  className = '',
  disabled,
  ...resto
}) {
  return (
    <button
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      className={`inline-flex items-center justify-center rounded-lg font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTES[variante]} ${TAMANOS[tamano]} ${className}`}
      {...resto}
    >
      {cargando ? (
        <Loader2 className={tamano === 'grande' ? 'h-5 w-5 animate-spin' : 'h-4 w-4 animate-spin'} />
      ) : (
        Icono && <Icono className={tamano === 'grande' ? 'h-5 w-5' : 'h-4 w-4'} />
      )}
      {children}
    </button>
  )
}
