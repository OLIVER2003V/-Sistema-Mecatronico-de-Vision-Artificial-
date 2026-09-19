// Rutas de la HMI. Cada pantalla declara el permiso que necesita; el filtro
// real lo aplica el backend en cada endpoint (ver cuentas/permisos.py).
import { Navigate, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout.jsx'
import RutaProtegida from './components/RutaProtegida.jsx'
import { useSesion } from './hooks/useSesion.jsx'
import Analiticos from './pages/Analiticos.jsx'
import Auditoria from './pages/Auditoria.jsx'
import Login, { inicioDe } from './pages/Login.jsx'
import Lotes from './pages/Lotes.jsx'
import Mermas from './pages/Mermas.jsx'
import Monitoreo from './pages/Monitoreo.jsx'
import Parametros from './pages/Parametros.jsx'
import Usuarios from './pages/Usuarios.jsx'

/** Manda a cada rol a la pantalla con la que trabaja todo el dia. */
function Inicio() {
  const { rol } = useSesion()
  return <Navigate to={inicioDe(rol)} replace />
}

const PANTALLAS = [
  { ruta: 'monitoreo', permiso: 'monitoreo', Componente: Monitoreo },
  { ruta: 'analiticos', permiso: 'analiticos', Componente: Analiticos },
  { ruta: 'lotes', permiso: 'lotes', Componente: Lotes },
  { ruta: 'parametros', permiso: 'parametros', Componente: Parametros },
  { ruta: 'mermas', permiso: 'mermas', Componente: Mermas },
  { ruta: 'usuarios', permiso: 'usuarios', Componente: Usuarios },
  { ruta: 'auditoria', permiso: 'auditoria', Componente: Auditoria },
]

export default function App() {
  return (
    <Routes>
      <Route path="/entrar" element={<Login />} />

      <Route
        element={
          <RutaProtegida>
            <Layout />
          </RutaProtegida>
        }
      >
        <Route index element={<Inicio />} />
        {PANTALLAS.map(({ ruta, permiso, Componente }) => (
          <Route
            key={ruta}
            path={ruta}
            element={
              <RutaProtegida permiso={permiso}>
                <Componente />
              </RutaProtegida>
            }
          />
        ))}
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
