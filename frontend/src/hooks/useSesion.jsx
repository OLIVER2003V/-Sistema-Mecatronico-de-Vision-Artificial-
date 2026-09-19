// Sesion del usuario: quien entro, con que rol y que pantallas puede ver.
//
// El rol y los permisos los decide el BACKEND (/api/auth/yo/): aca solo se
// usan para armar el menu y evitar mostrar botones que darian 403. La
// autorizacion de verdad la hace el servidor en cada endpoint.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

import { api, borrarTokens, iniciarSesion, leerAcceso } from '../api/cliente.js'

const ContextoSesion = createContext(null)

export function ProveedorSesion({ children }) {
  const [sesion, setSesion] = useState(null)
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(async () => {
    if (!leerAcceso()) {
      setSesion(null)
      setCargando(false)
      return
    }
    try {
      setSesion(await api('/api/auth/yo/'))
    } catch {
      // Token vencido o revocado: se vuelve al login sin ruido.
      borrarTokens()
      setSesion(null)
    } finally {
      setCargando(false)
    }
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar])

  const entrar = useCallback(
    async (usuario, password) => {
      await iniciarSesion(usuario, password)
      setSesion(await api('/api/auth/yo/'))
    },
    [],
  )

  const salir = useCallback(() => {
    borrarTokens()
    setSesion(null)
  }, [])

  const valor = useMemo(
    () => ({
      sesion,
      cargando,
      entrar,
      salir,
      recargar: cargar,
      rol: sesion?.rol ?? null,
      usuario: sesion?.usuario ?? null,
      permisos: sesion?.permisos ?? [],
      puede: (permiso) => (sesion?.permisos ?? []).includes(permiso),
    }),
    [sesion, cargando, entrar, salir, cargar],
  )

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>
}

export function useSesion() {
  const valor = useContext(ContextoSesion)
  if (valor === null) {
    throw new Error('useSesion debe usarse dentro de <ProveedorSesion>')
  }
  return valor
}
