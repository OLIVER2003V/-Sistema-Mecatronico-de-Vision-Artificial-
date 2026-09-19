// Pantalla sin datos. Un "no hay nada" a secas deja al usuario sin saber si
// se rompio algo o si todavia no paso nada, asi que siempre dice el porque
// y, cuando se puede, que hacer.
export default function EstadoVacio({ icono: Icono, titulo, mensaje, accion }) {
  return (
    <div className="flex flex-col items-center rounded-xl border border-dashed border-slate-700 bg-slate-800/20 px-6 py-12 text-center">
      {Icono && <Icono className="mb-3 h-10 w-10 text-slate-600" />}
      <p className="font-medium text-slate-300">{titulo}</p>
      {mensaje && <p className="mt-1 max-w-sm text-sm text-slate-500">{mensaje}</p>}
      {accion && <div className="mt-4">{accion}</div>}
    </div>
  )
}
