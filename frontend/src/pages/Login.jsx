import { AlertCircle, ArrowRight, Eye, EyeOff, Factory, Lock, User } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import Boton from '../components/ui/Boton.jsx'
import { CampoTexto } from '../components/ui/Campo.jsx'
import { useSesion } from '../hooks/useSesion.jsx'

// Cada rol arranca en la pantalla que le sirve; el menu muestra el resto.
const INICIO_POR_ROL = {
  ADMINISTRADOR: '/usuarios',
  SUPERVISOR: '/analiticos',
  OPERADOR: '/monitoreo',
}

export function inicioDe(rol) {
  return INICIO_POR_ROL[rol] ?? '/monitoreo'
}

export default function Login() {
  const { sesion, cargando, entrar, rol } = useSesion()
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [verPassword, setVerPassword] = useState(false)
  const [mayusculas, setMayusculas] = useState(false)
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)
  const navegar = useNavigate()
  const ubicacion = useLocation()

  if (!cargando && sesion) {
    return <Navigate to={ubicacion.state?.desde || inicioDe(rol)} replace />
  }

  const enviar = async (ev) => {
    ev.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await entrar(usuario.trim(), password)
      navegar(ubicacion.state?.desde || '/', { replace: true })
    } catch (e) {
      setError(e.message || 'No se pudo iniciar sesion.')
      setPassword('')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900 px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <Factory className="mx-auto mb-3 h-12 w-12 text-cyan-400" />
          <h1 className="text-2xl font-bold tracking-tight text-white">SORT-MATIC</h1>
          <p className="text-sm text-slate-400">EMBOL S.A. · Linea de envasado</p>
        </div>

        <form
          onSubmit={enviar}
          className="space-y-4 rounded-xl border border-slate-800 bg-slate-800/40 p-6"
        >
          <CampoTexto
            etiqueta="Usuario"
            icono={User}
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            autoComplete="username"
            autoFocus
            requerido
          />

          <CampoTexto
            etiqueta="Contraseña"
            icono={Lock}
            type={verPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            // Avisa de Bloq Mayus: es la causa mas comun de "no me entra".
            onKeyUp={(e) => setMayusculas(e.getModifierState?.('CapsLock') ?? false)}
            autoComplete="current-password"
            requerido
            accion={
              <button
                type="button"
                onClick={() => setVerPassword((v) => !v)}
                aria-label={verPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                className="rounded p-1 text-slate-500 transition-colors hover:text-slate-300"
              >
                {verPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            }
          />

          {mayusculas && (
            <p className="flex items-center gap-1.5 text-xs text-amber-400">
              <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" /> Bloq Mayus esta activado.
            </p>
          )}

          {error && (
            <p
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
            >
              <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              {error}
            </p>
          )}

          <Boton
            type="submit"
            cargando={enviando}
            className="w-full"
            icono={enviando ? undefined : ArrowRight}
          >
            {enviando ? 'Entrando...' : 'Entrar'}
          </Boton>
        </form>

        <p className="mt-4 text-center text-xs text-slate-600">
          ¿Sin cuenta? Pidale una al administrador de sistemas.
        </p>
      </div>
    </div>
  )
}
