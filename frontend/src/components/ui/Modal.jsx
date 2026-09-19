// Ventana modal accesible: se cierra con Escape y con clic afuera, bloquea
// el scroll del fondo y devuelve el foco a donde estaba al cerrarse. Antes
// cada modal resolvia esto por su cuenta (y ninguno escuchaba Escape).
import { X } from 'lucide-react'
import { useEffect, useRef } from 'react'

const ANCHOS = { sm: 'max-w-md', md: 'max-w-lg', lg: 'max-w-3xl' }

export default function Modal({ titulo, encabezado, ancho = 'md', onCerrar, children }) {
  const caja = useRef(null)
  const focoPrevio = useRef(null)

  useEffect(() => {
    focoPrevio.current = document.activeElement
    const scrollOriginal = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const alTeclear = (ev) => {
      if (ev.key === 'Escape') {
        ev.stopPropagation()
        onCerrar()
        return
      }
      // Atrapa el tabulador dentro del modal: sin esto el foco se va a los
      // botones de atras, que el usuario no ve.
      if (ev.key !== 'Tab' || !caja.current) return
      const enfocables = caja.current.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )
      if (enfocables.length === 0) return
      const primero = enfocables[0]
      const ultimo = enfocables[enfocables.length - 1]
      if (ev.shiftKey && document.activeElement === primero) {
        ev.preventDefault()
        ultimo.focus()
      } else if (!ev.shiftKey && document.activeElement === ultimo) {
        ev.preventDefault()
        primero.focus()
      }
    }

    document.addEventListener('keydown', alTeclear)
    return () => {
      document.removeEventListener('keydown', alTeclear)
      document.body.style.overflow = scrollOriginal
      focoPrevio.current?.focus?.()
    }
  }, [onCerrar])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4"
      onMouseDown={(ev) => ev.target === ev.currentTarget && onCerrar()}
    >
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        className={`max-h-full w-full ${ANCHOS[ancho]} animate-entrar overflow-auto rounded-xl border border-slate-700 bg-slate-900 shadow-2xl`}
      >
        <div className="flex items-center justify-between gap-3 border-b border-slate-800 p-4">
          {encabezado ?? <h3 className="text-lg font-semibold text-white">{titulo}</h3>}
          <button
            type="button"
            onClick={onCerrar}
            aria-label="Cerrar"
            className="rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
