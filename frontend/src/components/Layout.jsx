// Armazon de la HMI: barra lateral con las pantallas que el rol en curso
// tiene permitidas, y cabecera con el titulo, el estado de la linea y el
// menu del usuario.
//
// El ProveedorTelemetria vive aca (dentro de la sesion iniciada) para que
// haya UN solo WebSocket para toda la app y el indicador de conexion se vea
// en todas las pantallas, no solo en las que muestran produccion.
import {
  BarChart3,
  ChevronDown,
  Factory,
  Gauge,
  Images,
  KeyRound,
  LogOut,
  Menu,
  Package,
  ScrollText,
  SlidersHorizontal,
  Sparkles,
  Users,
  X,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

import { useSesion } from '../hooks/useSesion.jsx'
import { ProveedorTelemetria, useTelemetria } from '../hooks/useTelemetria.jsx'
import AsistenteReportesModal from './AsistenteReportesModal.jsx'
import CambiarPassword from './CambiarPassword.jsx'
import EstadoConexion from './EstadoConexion.jsx'

// El 'permiso' de cada entrada lo decide el backend (PERMISOS_POR_ROL en
// cuentas/views.py); aca solo se filtra el menu con lo que vino en la sesion.
const SECCIONES = [
  {
    titulo: 'Operacion',
    entradas: [
      { a: '/monitoreo', texto: 'Monitoreo de linea', icono: Gauge, permiso: 'monitoreo' },
    ],
  },
  {
    titulo: 'Calidad',
    entradas: [
      { a: '/analiticos', texto: 'Analiticos', icono: BarChart3, permiso: 'analiticos' },
      { a: '/lotes', texto: 'Lotes de botellas', icono: Package, permiso: 'lotes' },
      {
        a: '/parametros',
        texto: 'Parametros de inspeccion',
        icono: SlidersHorizontal,
        permiso: 'parametros',
      },
      { a: '/mermas', texto: 'Galeria de mermas', icono: Images, permiso: 'mermas' },
    ],
  },
  {
    titulo: 'Administracion',
    entradas: [
      { a: '/usuarios', texto: 'Usuarios', icono: Users, permiso: 'usuarios' },
      { a: '/auditoria', texto: 'Bitacora', icono: ScrollText, permiso: 'auditoria' },
    ],
  },
]

const TODAS = SECCIONES.flatMap((s) => s.entradas)

const ROL_LEGIBLE = {
  ADMINISTRADOR: 'Administrador de sistemas',
  SUPERVISOR: 'Supervisor de calidad',
  OPERADOR: 'Operador de planta',
}

function MenuUsuario({ onCambiarPassword }) {
  const { usuario, rol, salir } = useSesion()
  const [abierto, setAbierto] = useState(false)
  const caja = useRef(null)

  useEffect(() => {
    if (!abierto) return
    const alClic = (ev) => !caja.current?.contains(ev.target) && setAbierto(false)
    const alTeclear = (ev) => ev.key === 'Escape' && setAbierto(false)
    document.addEventListener('mousedown', alClic)
    document.addEventListener('keydown', alTeclear)
    return () => {
      document.removeEventListener('mousedown', alClic)
      document.removeEventListener('keydown', alTeclear)
    }
  }, [abierto])

  const nombre =
    [usuario?.first_name, usuario?.last_name].filter(Boolean).join(' ') || usuario?.username
  const iniciales = (nombre || '?')
    .split(' ')
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')

  return (
    <div ref={caja} className="relative">
      <button
        onClick={() => setAbierto((v) => !v)}
        aria-expanded={abierto}
        aria-haspopup="menu"
        className="flex items-center gap-2 rounded-lg border border-slate-700 py-1.5 pl-1.5 pr-2.5 transition-colors hover:border-slate-600 hover:bg-slate-800"
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-cyan-500/20 text-xs font-bold text-cyan-300">
          {iniciales}
        </span>
        <span className="hidden text-left sm:block">
          <span className="block text-sm font-medium leading-tight text-slate-200">{nombre}</span>
          <span className="block text-xs leading-tight text-slate-500">{ROL_LEGIBLE[rol] ?? rol}</span>
        </span>
        <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform ${abierto ? 'rotate-180' : ''}`} />
      </button>

      {abierto && (
        <div
          role="menu"
          className="absolute right-0 top-full z-50 mt-1.5 w-60 animate-entrar overflow-hidden rounded-xl border border-slate-700 bg-slate-900 shadow-xl"
        >
          <div className="border-b border-slate-800 p-3 sm:hidden">
            <p className="text-sm font-medium text-slate-200">{nombre}</p>
            <p className="text-xs text-slate-500">{ROL_LEGIBLE[rol] ?? rol}</p>
          </div>
          <button
            role="menuitem"
            onClick={() => {
              setAbierto(false)
              onCambiarPassword()
            }}
            className="flex w-full items-center gap-2.5 px-3 py-2.5 text-sm text-slate-300 transition-colors hover:bg-slate-800 hover:text-slate-100"
          >
            <KeyRound className="h-4 w-4" /> Cambiar contraseña
          </button>
          <button
            role="menuitem"
            onClick={salir}
            className="flex w-full items-center gap-2.5 border-t border-slate-800 px-3 py-2.5 text-sm text-slate-300 transition-colors hover:bg-red-500/10 hover:text-red-300"
          >
            <LogOut className="h-4 w-4" /> Cerrar sesion
          </button>
        </div>
      )}
    </div>
  )
}

function Cabecera({ onAbrirMenu, onCambiarPassword, onAbrirReportes }) {
  const { pathname } = useLocation()
  const { conectado, ultimaSenal } = useTelemetria()
  const actual = TODAS.find((e) => e.a === pathname)

  useEffect(() => {
    document.title = actual ? `${actual.texto} · SORT-MATIC` : 'SORT-MATIC · EMBOL'
  }, [actual])

  return (
    <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-slate-800 bg-slate-900/90 px-4 py-3 backdrop-blur lg:px-6">
      <button
        onClick={onAbrirMenu}
        className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-800 lg:hidden"
        aria-label="Abrir menu de navegacion"
      >
        <Menu className="h-5 w-5" />
      </button>

      <h2 className="truncate text-base font-semibold text-slate-100">{actual?.texto ?? 'SORT-MATIC'}</h2>

      <div className="ml-auto flex items-center gap-3">
        <button
          onClick={onAbrirReportes}
          className="flex items-center gap-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold text-cyan-300 transition-colors hover:bg-cyan-500/20 hover:border-cyan-400 shadow-sm"
          title="Generar Reportes Dinámicos con IA (Voz / Prompt)"
        >
          <Sparkles className="h-4 w-4 text-cyan-400 animate-pulse" />
          <span className="hidden sm:inline">Reportes IA</span>
        </button>

        <EstadoConexion conectado={conectado} ultimaSenal={ultimaSenal} />
        <MenuUsuario onCambiarPassword={onCambiarPassword} />
      </div>
    </header>
  )
}

function Enlace({ entrada, onNavegar }) {
  const Icono = entrada.icono
  return (
    <NavLink
      to={entrada.a}
      onClick={onNavegar}
      className={({ isActive }) =>
        `relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
          isActive
            ? 'bg-cyan-500/10 font-medium text-cyan-300'
            : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span className="absolute inset-y-1.5 -left-1 w-0.5 rounded-full bg-cyan-400" aria-hidden="true" />
          )}
          <Icono className="h-4 w-4 flex-shrink-0" />
          <span className="truncate">{entrada.texto}</span>
        </>
      )}
    </NavLink>
  )
}

function Contenido() {
  const [menuAbierto, setMenuAbierto] = useState(false)
  const [cambiandoPassword, setCambiandoPassword] = useState(false)
  const [reportesAbierto, setReportesAbierto] = useState(false)
  const { permisos } = useSesion()
  const { pathname } = useLocation()

  useEffect(() => setMenuAbierto(false), [pathname])

  const secciones = SECCIONES.map((s) => ({
    ...s,
    entradas: s.entradas.filter((e) => permisos.includes(e.permiso)),
  })).filter((s) => s.entradas.length > 0)

  return (
    <div className="min-h-screen bg-slate-900 lg:flex relative">
      <a
        href="#contenido"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-cyan-600 focus:px-4 focus:py-2 focus:text-white"
      >
        Saltar al contenido
      </a>

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-800 bg-slate-950 transition-transform duration-200 lg:static lg:translate-x-0 ${
          menuAbierto ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center gap-3 p-4">
          <Factory className="h-8 w-8 flex-shrink-0 text-cyan-400" />
          <div className="min-w-0">
            <p className="text-lg font-bold leading-tight tracking-tight text-white">SORT-MATIC</p>
            <p className="truncate text-xs text-slate-500">EMBOL S.A. · Envasado</p>
          </div>
          <button
            onClick={() => setMenuAbierto(false)}
            className="ml-auto rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 lg:hidden"
            aria-label="Cerrar menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav aria-label="Secciones" className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
          {secciones.map((seccion) => (
            <div key={seccion.titulo}>
              <p className="mb-1.5 px-3 text-xs font-semibold uppercase tracking-wider text-slate-600">
                {seccion.titulo}
              </p>
              <div className="space-y-0.5">
                {seccion.entradas.map((entrada) => (
                  <Enlace key={entrada.a} entrada={entrada} onNavegar={() => setMenuAbierto(false)} />
                ))}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      {menuAbierto && (
        <button
          aria-label="Cerrar menu"
          onClick={() => setMenuAbierto(false)}
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
        />
      )}

      <div className="min-w-0 flex-1">
        <Cabecera
          onAbrirMenu={() => setMenuAbierto(true)}
          onCambiarPassword={() => setCambiandoPassword(true)}
          onAbrirReportes={() => setReportesAbierto(true)}
        />
        <main id="contenido" className="p-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      {/* Botón Flotante para Asistente & Reportes IA */}
      <button
        onClick={() => setReportesAbierto(true)}
        className="fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full bg-cyan-600 p-3.5 text-white shadow-xl transition-transform hover:scale-105 hover:bg-cyan-500 active:scale-95"
        title="Generar Reportes con IA (Voz / Prompt)"
      >
        <Sparkles className="h-6 w-6 text-white" />
        <span className="hidden font-bold text-sm pr-1 md:inline">Generar Reporte IA</span>
      </button>

      {reportesAbierto && <AsistenteReportesModal onCerrar={() => setReportesAbierto(false)} />}
      {cambiandoPassword && <CambiarPassword onCerrar={() => setCambiandoPassword(false)} />}
    </div>
  )
}

export default function Layout() {
  return (
    <ProveedorTelemetria>
      <Contenido />
    </ProveedorTelemetria>
  )
}
