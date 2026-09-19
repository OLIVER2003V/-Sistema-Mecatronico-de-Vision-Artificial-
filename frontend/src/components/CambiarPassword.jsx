// Cambio de contraseña propia. Cualquier rol puede hacerlo: las cuentas se
// crean con una clave que le pasa el administrador, y lo sano es que el
// usuario la cambie al entrar la primera vez.
import { useState } from 'react'

import { api } from '../api/cliente.js'
import { useAvisos } from '../hooks/useAvisos.jsx'
import Boton from './ui/Boton.jsx'
import { CampoTexto } from './ui/Campo.jsx'
import Modal from './ui/Modal.jsx'

const MINIMO = 8

export default function CambiarPassword({ onCerrar }) {
  const avisar = useAvisos()
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [repetida, setRepetida] = useState('')
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState(null)

  // Se avisa antes de mandar: el backend tambien lo valida, pero hacer un
  // viaje al servidor para decir "no coinciden" es innecesario.
  const noCoinciden = repetida.length > 0 && nueva !== repetida
  const muyCorta = nueva.length > 0 && nueva.length < MINIMO
  const puedeGuardar = actual && nueva.length >= MINIMO && nueva === repetida && !guardando

  const enviar = async (ev) => {
    ev.preventDefault()
    setGuardando(true)
    setError(null)
    try {
      await api('/api/auth/password/', {
        metodo: 'POST',
        cuerpo: { password_actual: actual, password_nueva: nueva },
      })
      avisar.exito('Contraseña actualizada.')
      onCerrar()
    } catch (e) {
      setError(e.message)
    } finally {
      setGuardando(false)
    }
  }

  return (
    <Modal titulo="Cambiar contraseña" ancho="sm" onCerrar={onCerrar}>
      <form onSubmit={enviar} className="space-y-4 p-4">
        <CampoTexto
          etiqueta="Contraseña actual"
          type="password"
          value={actual}
          onChange={(e) => setActual(e.target.value)}
          autoComplete="current-password"
          autoFocus
          requerido
          error={error}
        />
        <CampoTexto
          etiqueta="Contraseña nueva"
          type="password"
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
          autoComplete="new-password"
          requerido
          ayuda={`Minimo ${MINIMO} caracteres, que no sea solo numeros ni una contraseña comun.`}
          error={muyCorta ? `Le faltan ${MINIMO - nueva.length} caracteres.` : null}
        />
        <CampoTexto
          etiqueta="Repetir la nueva"
          type="password"
          value={repetida}
          onChange={(e) => setRepetida(e.target.value)}
          autoComplete="new-password"
          requerido
          error={noCoinciden ? 'Las dos contraseñas no coinciden.' : null}
        />

        <div className="flex justify-end gap-3 pt-1">
          <Boton type="button" variante="contorno" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" disabled={!puedeGuardar} cargando={guardando}>
            Guardar
          </Boton>
        </div>
      </form>
    </Modal>
  )
}
