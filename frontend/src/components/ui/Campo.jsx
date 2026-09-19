// Campos de formulario con etiqueta, ayuda y error asociados por id, para
// que el lector de pantalla los lea juntos y el clic en la etiqueta enfoque
// el control.
import { useId } from 'react'

const BASE =
  'w-full rounded-lg border bg-slate-900 px-3 py-2 text-sm text-slate-100 transition-colors placeholder:text-slate-600 disabled:opacity-60'

function Envoltura({ id, etiqueta, ayuda, error, requerido, children }) {
  return (
    <div>
      {etiqueta && (
        <label htmlFor={id} className="mb-1.5 block text-sm text-slate-300">
          {etiqueta}
          {requerido && <span className="ml-0.5 text-red-400">*</span>}
        </label>
      )}
      {children}
      {ayuda && !error && (
        <p id={`${id}-ayuda`} className="mt-1 text-xs text-slate-500">
          {ayuda}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="mt-1 text-xs text-red-400">
          {error}
        </p>
      )}
    </div>
  )
}

/**
 * `accion` es un boton al final del campo (por ejemplo el ojo para ver la
 * contraseña). Va aca y no en cada pantalla para que quede siempre bien
 * alineado con el input, sin posiciones a ojo.
 */
export function CampoTexto({
  etiqueta,
  ayuda,
  error,
  icono: Icono,
  accion,
  requerido,
  className = '',
  ...resto
}) {
  const idAuto = useId()
  const id = resto.id ?? idAuto
  return (
    <Envoltura id={id} etiqueta={etiqueta} ayuda={ayuda} error={error} requerido={requerido}>
      <div className="relative">
        {Icono && (
          <Icono className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        )}
        <input
          id={id}
          required={requerido}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={error ? `${id}-error` : ayuda ? `${id}-ayuda` : undefined}
          className={`${BASE} ${Icono ? 'pl-9' : ''} ${accion ? 'pr-10' : ''} ${
            error ? 'border-red-500/60 focus:border-red-500' : 'border-slate-700 focus:border-cyan-500'
          } ${className}`}
          {...resto}
        />
        {accion && (
          <span className="absolute right-2 top-1/2 -translate-y-1/2">{accion}</span>
        )}
      </div>
    </Envoltura>
  )
}

export function CampoSelect({
  etiqueta,
  ayuda,
  error,
  opciones,
  requerido,
  className = '',
  ...resto
}) {
  const idAuto = useId()
  const id = resto.id ?? idAuto
  return (
    <Envoltura id={id} etiqueta={etiqueta} ayuda={ayuda} error={error} requerido={requerido}>
      <select
        id={id}
        aria-describedby={ayuda ? `${id}-ayuda` : undefined}
        className={`${BASE} border-slate-700 focus:border-cyan-500 ${className}`}
        {...resto}
      >
        {opciones.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.texto}
          </option>
        ))}
      </select>
    </Envoltura>
  )
}

export function CampoCasilla({ etiqueta, ayuda, ...resto }) {
  const idAuto = useId()
  const id = resto.id ?? idAuto
  return (
    <div>
      <label htmlFor={id} className="flex cursor-pointer items-center gap-2 text-sm text-slate-300">
        <input id={id} type="checkbox" className="h-4 w-4 accent-cyan-500" {...resto} />
        {etiqueta}
      </label>
      {ayuda && <p className="ml-6 mt-1 text-xs text-slate-500">{ayuda}</p>}
    </div>
  )
}
