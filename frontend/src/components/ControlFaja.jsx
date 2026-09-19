// Panel SCADA: marcha/paro de la faja y su estado REAL.
//
// El boton solo deja el comando en cola; vision/ lo consume por polling y se
// lo escribe al Arduino por el puerto serie. El estado que se muestra arriba
// NO es "lo que pedi" sino lo que el firmware informo despues ('#START' /
// '#STOP'): si el Arduino esta desconectado, aca se ve.
//
// Los botones son grandes a proposito: se aprietan desde la linea, a veces
// con guantes. El PARO nunca pide confirmacion — un paro que tarda un dialogo
// no sirve para nada.
import { AlertTriangle, Play, Plug, RotateCcw, Square } from 'lucide-react'
import { useState } from 'react'

import { api } from '../api/cliente.js'
import { useAvisos } from '../hooks/useAvisos.jsx'
import Boton from './ui/Boton.jsx'
import Tarjeta from './ui/Tarjeta.jsx'

function Semaforo({ estado }) {
  if (!estado) {
    return (
      <span className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-500">
        Consultando estado...
      </span>
    )
  }

  if (!estado.arduino_conectado) {
    return (
      <span className="flex items-center gap-2 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-1.5">
        <Plug className="h-4 w-4 text-red-400" />
        <span className="text-sm font-semibold text-red-300">ARDUINO DESCONECTADO</span>
      </span>
    )
  }

  const enMarcha = estado.en_marcha
  return (
    <span
      className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 ${
        enMarcha ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-slate-600 bg-slate-700/30'
      }`}
    >
      <span className="relative flex h-2.5 w-2.5">
        {enMarcha && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />
        )}
        <span
          className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
            enMarcha ? 'bg-emerald-400' : 'bg-slate-500'
          }`}
        />
      </span>
      <span className={`text-sm font-semibold ${enMarcha ? 'text-emerald-300' : 'text-slate-300'}`}>
        {enMarcha ? 'FAJA EN MARCHA' : 'FAJA DETENIDA'}
      </span>
    </span>
  )
}

export default function ControlFaja({ estado }) {
  const avisar = useAvisos()
  const [enviando, setEnviando] = useState(null)

  const mandar = async (accion, mensaje) => {
    setEnviando(accion)
    try {
      await api('/api/comandos/', { metodo: 'POST', cuerpo: { accion } })
      avisar.info(mensaje)
    } catch (e) {
      avisar.error(`No se pudo enviar ${accion}: ${e.message}`)
    } finally {
      setEnviando(null)
    }
  }

  const arrancar = () => {
    if (
      window.confirm(
        '¿Arrancar la faja?\n\nAsegurese de que no haya nadie cerca de los servos ni de la cinta.',
      )
    ) {
      mandar('START', 'Marcha enviada. Llega al Arduino en menos de 1 s.')
    }
  }

  const reiniciar = () => {
    if (window.confirm('¿Poner los contadores del Arduino en cero?')) {
      mandar('RESET', 'Contadores del Arduino reiniciados.')
    }
  }

  const sinArduino = estado && !estado.arduino_conectado

  return (
    <Tarjeta
      titulo="Control de la faja"
      acciones={<Semaforo estado={estado} />}
      className={sinArduino ? 'border-red-500/30' : undefined}
    >
      <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
        <Boton
          icono={Play}
          variante="exito"
          tamano="grande"
          onClick={arrancar}
          cargando={enviando === 'START'}
          disabled={enviando !== null}
        >
          Marcha
        </Boton>
        <Boton
          icono={Square}
          variante="peligro"
          tamano="grande"
          onClick={() => mandar('STOP', 'Paro enviado.')}
          cargando={enviando === 'STOP'}
          disabled={enviando !== null}
        >
          Paro
        </Boton>
        <Boton
          icono={RotateCcw}
          variante="contorno"
          tamano="grande"
          onClick={reiniciar}
          cargando={enviando === 'RESET'}
          disabled={enviando !== null}
          className="col-span-2 sm:col-auto"
        >
          Reiniciar contadores
        </Boton>
      </div>

      {sinArduino && (
        <p className="mt-3 flex items-start gap-2 text-sm text-red-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          El modulo de vision no esta hablando con el Arduino. Los comandos quedan en cola y se
          entregan cuando vuelva la conexion.
        </p>
      )}

      {estado?.detalle && (
        <p className="mt-3 font-mono text-xs text-slate-600">ultimo aviso del firmware: {estado.detalle}</p>
      )}
    </Tarjeta>
  )
}
