// Esqueletos de carga: mantienen la forma de la pantalla mientras llegan los
// datos, en vez del salto de "Cargando..." a contenido que habia antes.
export function Esqueleto({ className = 'h-4 w-24' }) {
  return (
    <span
      aria-hidden="true"
      className={`relative block overflow-hidden rounded bg-slate-700/50 ${className}`}
    >
      <span className="absolute inset-0 -translate-x-full animate-brillo bg-gradient-to-r from-transparent via-slate-600/40 to-transparent" />
    </span>
  )
}

export function EsqueletoTarjeta({ lineas = 3 }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-800/40 p-4 sm:p-5">
      <Esqueleto className="mb-4 h-4 w-40" />
      <div className="space-y-2.5">
        {Array.from({ length: lineas }, (_, i) => (
          <Esqueleto key={i} className={`h-3 ${i === lineas - 1 ? 'w-2/3' : 'w-full'}`} />
        ))}
      </div>
    </div>
  )
}

export function EsqueletoTabla({ filas = 5, columnas = 5 }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-800/40">
      <div className="space-y-3 p-4">
        {Array.from({ length: filas }, (_, f) => (
          <div key={f} className="flex gap-4">
            {Array.from({ length: columnas }, (_, c) => (
              <Esqueleto key={c} className="h-3 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
