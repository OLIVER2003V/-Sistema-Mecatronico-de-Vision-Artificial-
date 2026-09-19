// Contenedor estandar de las secciones. Unifica borde, fondo y espaciado,
// que antes variaban de pantalla en pantalla.
export default function Tarjeta({
  titulo,
  descripcion,
  icono: Icono,
  acciones,
  children,
  className = '',
  padding = 'p-4 sm:p-5',
}) {
  return (
    <section className={`rounded-xl border border-slate-800 bg-slate-800/40 ${padding} ${className}`}>
      {(titulo || acciones) && (
        <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
          <div>
            {titulo && (
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
                {Icono && <Icono className="h-4 w-4 text-slate-400" />}
                {titulo}
              </h3>
            )}
            {descripcion && <p className="mt-1 text-xs text-slate-500">{descripcion}</p>}
          </div>
          {acciones}
        </div>
      )}
      {children}
    </section>
  )
}
