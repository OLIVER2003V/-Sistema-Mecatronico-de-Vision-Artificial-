// Bitacora del sistema: quien hizo que, cuando y desde donde.
// Es de solo lectura: las filas las escribe el backend (cuentas/models.registrar).
import { ChevronLeft, ChevronRight, Loader2, ScrollText } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { api, filas } from '../api/cliente.js'
import Boton from '../components/ui/Boton.jsx'
import { CampoSelect } from '../components/ui/Campo.jsx'
import EstadoVacio from '../components/ui/EstadoVacio.jsx'
import { EsqueletoTabla } from '../components/ui/Esqueleto.jsx'
import Insignia from '../components/ui/Insignia.jsx'
import { useAvisos } from '../hooks/useAvisos.jsx'

const ACCIONES = [
  { valor: '', texto: 'Todas las acciones' },
  { valor: 'INICIO_SESION', texto: 'Inicio de sesion' },
  { valor: 'USUARIO_CREADO', texto: 'Usuario creado' },
  { valor: 'USUARIO_ACTUALIZADO', texto: 'Usuario actualizado' },
  { valor: 'USUARIO_ELIMINADO', texto: 'Usuario eliminado' },
  { valor: 'CONFIG_ACTUALIZADA', texto: 'Configuracion actualizada' },
  { valor: 'COMANDO_FAJA', texto: 'Comando a la faja' },
  { valor: 'LOTE_ACTUALIZADO', texto: 'Lote actualizado' },
  { valor: 'LOTE_CERRADO', texto: 'Lote cerrado' },
]

const TONO = {
  INICIO_SESION: 'neutro',
  USUARIO_CREADO: 'exito',
  USUARIO_ACTUALIZADO: 'info',
  USUARIO_ELIMINADO: 'peligro',
  CONFIG_ACTUALIZADA: 'alerta',
  COMANDO_FAJA: 'violeta',
  LOTE_ACTUALIZADO: 'info',
  LOTE_CERRADO: 'alerta',
}

export default function Auditoria() {
  const avisar = useAvisos()
  const [accion, setAccion] = useState('')
  const [pagina, setPagina] = useState(1)
  const [datos, setDatos] = useState({ results: [], count: 0, next: null, previous: null })
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(async () => {
    setCargando(true)
    const parametros = new URLSearchParams({ page: String(pagina) })
    if (accion) parametros.set('accion', accion)
    try {
      setDatos(await api(`/api/auditoria/?${parametros.toString()}`))
    } catch (e) {
      avisar.error(e.message)
    } finally {
      setCargando(false)
    }
  }, [accion, pagina, avisar])

  useEffect(() => {
    cargar()
  }, [cargar])

  const registros = filas(datos)

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-400">
        Registro de accesos y de todo cambio sensible. No se puede editar ni borrar.
      </p>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <CampoSelect
          value={accion}
          aria-label="Filtrar por accion"
          onChange={(e) => {
            setAccion(e.target.value)
            setPagina(1)
          }}
          opciones={ACCIONES}
        />

        <div className="flex items-center gap-2 text-sm text-slate-400">
          {cargando && <Loader2 className="h-4 w-4 animate-spin" />}
          <span className="cifra">{datos.count ?? registros.length}</span> registro(s)
          <Boton
            variante="contorno"
            tamano="sm"
            icono={ChevronLeft}
            aria-label="Pagina anterior"
            onClick={() => setPagina((p) => Math.max(1, p - 1))}
            disabled={!datos.previous || cargando}
          />
          <span className="cifra px-1">{pagina}</span>
          <Boton
            variante="contorno"
            tamano="sm"
            icono={ChevronRight}
            aria-label="Pagina siguiente"
            onClick={() => setPagina((p) => p + 1)}
            disabled={!datos.next || cargando}
          />
        </div>
      </div>

      {cargando ? (
        <EsqueletoTabla filas={6} columnas={5} />
      ) : registros.length === 0 ? (
        <EstadoVacio
          icono={ScrollText}
          titulo="Sin registros para este filtro"
          mensaje="La bitacora anota inicios de sesion, cambios de usuarios y de configuracion, y comandos a la faja."
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-800/40">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-400">
              <tr className="border-b border-slate-700">
                <th scope="col" className="p-3">Fecha y hora</th>
                <th scope="col" className="p-3">Usuario</th>
                <th scope="col" className="p-3">Accion</th>
                <th scope="col" className="hidden p-3 md:table-cell">Detalle</th>
                <th scope="col" className="hidden p-3 lg:table-cell">Origen</th>
              </tr>
            </thead>
            <tbody>
              {registros.map((fila) => (
                <tr
                  key={fila.id}
                  className="border-b border-slate-800 text-slate-200 transition-colors last:border-0 hover:bg-slate-800/40"
                >
                  <td className="whitespace-nowrap p-3 text-slate-400">
                    {new Date(fila.creado_en).toLocaleString()}
                  </td>
                  <td className="p-3 font-mono">{fila.usuario_nombre}</td>
                  <td className="p-3">
                    <Insignia tono={TONO[fila.accion] ?? 'neutro'}>{fila.accion_nombre}</Insignia>
                  </td>
                  <td className="hidden max-w-md p-3 text-slate-300 md:table-cell">
                    {fila.descripcion || '—'}
                  </td>
                  <td className="hidden p-3 font-mono text-xs text-slate-500 lg:table-cell">
                    {fila.direccion_ip || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
