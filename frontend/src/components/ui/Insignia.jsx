// Etiqueta de estado. Los tonos son los mismos en toda la HMI: verde = pasa,
// rojo = defecto fisico, ambar = nivel de llenado, gris = neutro.
const TONOS = {
  exito: 'bg-emerald-500/15 text-emerald-300',
  peligro: 'bg-red-500/15 text-red-300',
  alerta: 'bg-amber-500/15 text-amber-300',
  info: 'bg-cyan-500/15 text-cyan-300',
  neutro: 'bg-slate-600/30 text-slate-300',
  violeta: 'bg-violet-500/15 text-violet-300',
}

export default function Insignia({ tono = 'neutro', icono: Icono, children, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${TONOS[tono]} ${className}`}
    >
      {Icono && <Icono className="h-3 w-3" />}
      {children}
    </span>
  )
}
