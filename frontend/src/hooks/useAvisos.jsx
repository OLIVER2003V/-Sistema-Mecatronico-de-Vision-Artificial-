// Avisos (exito / error / informacion) para toda la HMI.
//
// Antes cada pantalla dibujaba su propio cartel y lo guardaba en su estado:
// el mensaje desaparecia al recargar la tabla y habia diez copias del mismo
// bloque de JSX. Ahora se llama avisar.exito('...') desde cualquier lado.
//
// La region tiene aria-live: el lector de pantalla anuncia el resultado de
// una accion aunque el foco este en otro lado.
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'
import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react'

const ContextoAvisos = createContext(null)

// Un error hay que poder leerlo; un "guardado" se entiende de un vistazo.
const DURACION_MS = { exito: 4000, info: 5000, error: 9000 }

const ASPECTO = {
  exito: {
    Icono: CheckCircle2,
    clases: 'border-emerald-500/40 bg-emerald-950/90 text-emerald-100',
    color: 'text-emerald-400',
  },
  error: {
    Icono: AlertTriangle,
    clases: 'border-red-500/40 bg-red-950/90 text-red-100',
    color: 'text-red-400',
  },
  info: {
    Icono: Info,
    clases: 'border-cyan-500/40 bg-cyan-950/90 text-cyan-100',
    color: 'text-cyan-400',
  },
}

export function ProveedorAvisos({ children }) {
  const [avisos, setAvisos] = useState([])
  const siguienteId = useRef(1)

  const cerrar = useCallback((id) => {
    setAvisos((prev) => prev.filter((a) => a.id !== id))
  }, [])

  const agregar = useCallback(
    (tipo, mensaje) => {
      if (!mensaje) return
      const id = siguienteId.current++
      setAvisos((prev) => [...prev.slice(-3), { id, tipo, mensaje: String(mensaje) }])
      setTimeout(() => cerrar(id), DURACION_MS[tipo])
    },
    [cerrar],
  )

  const avisar = useMemo(
    () => ({
      exito: (mensaje) => agregar('exito', mensaje),
      error: (mensaje) => agregar('error', mensaje),
      info: (mensaje) => agregar('info', mensaje),
    }),
    [agregar],
  )

  return (
    <ContextoAvisos.Provider value={avisar}>
      {children}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed inset-x-0 bottom-0 z-[60] flex flex-col items-center gap-2 p-4 sm:items-end"
      >
        {avisos.map(({ id, tipo, mensaje }) => {
          const { Icono, clases, color } = ASPECTO[tipo]
          return (
            <div
              key={id}
              role={tipo === 'error' ? 'alert' : undefined}
              className={`pointer-events-auto flex w-full max-w-sm animate-entrar items-start gap-2.5 rounded-xl border p-3.5 shadow-xl backdrop-blur ${clases}`}
            >
              <Icono className={`mt-0.5 h-4 w-4 flex-shrink-0 ${color}`} />
              <p className="flex-1 text-sm leading-snug">{mensaje}</p>
              <button
                onClick={() => cerrar(id)}
                aria-label="Descartar aviso"
                className="rounded p-0.5 opacity-60 transition-opacity hover:opacity-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          )
        })}
      </div>
    </ContextoAvisos.Provider>
  )
}

export function useAvisos() {
  const valor = useContext(ContextoAvisos)
  if (valor === null) {
    throw new Error('useAvisos debe usarse dentro de <ProveedorAvisos>')
  }
  return valor
}
