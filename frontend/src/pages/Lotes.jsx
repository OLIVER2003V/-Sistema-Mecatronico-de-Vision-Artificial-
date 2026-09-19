// Gestion de lotes del Supervisor de calidad.
//
// Hay dos numeros distintos y conviene no confundirlos, asi que van en
// tarjetas separadas y cada una dice a que afecta:
//   * el tamano POR DEFECTO (configuracion.botellas_por_lote), que usan los
//     lotes que se abran de aca en adelante;
//   * la capacidad del lote ACTIVO, que se puede corregir sobre la marcha.
import { Package, Save, Square } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { api, filas } from '../api/cliente.js'
import LotesTable from '../components/LotesTable.jsx'
import Boton from '../components/ui/Boton.jsx'
import EstadoVacio from '../components/ui/EstadoVacio.jsx'
import { EsqueletoTarjeta } from '../components/ui/Esqueleto.jsx'
import Tarjeta from '../components/ui/Tarjeta.jsx'
import { useAvisos } from '../hooks/useAvisos.jsx'

const CLASES_NUMERO =
  'w-28 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-100 outline-none transition-colors focus:border-cyan-500'

export default function Lotes() {
  const avisar = useAvisos()
  const [config, setConfig] = useState(null)
  const [activo, setActivo] = useState(null)
  const [lotes, setLotes] = useState([])
  const [porDefecto, setPorDefecto] = useState('')
  const [capacidad, setCapacidad] = useState('')
  const [guardando, setGuardando] = useState(null)
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback(async () => {
    try {
      const [cfg, listado] = await Promise.all([api('/api/configuracion/'), api('/api/lotes/')])
      const todos = filas(listado)
      setConfig(cfg)
      setPorDefecto(String(cfg.botellas_por_lote))
      setLotes(todos)

      const enCurso = todos.find((l) => l.estado === 'ACTIVO') ?? null
      setActivo(enCurso)
      setCapacidad(enCurso ? String(enCurso.capacidad_lote) : '')
    } catch (e) {
      avisar.error(e.message)
    } finally {
      setCargando(false)
    }
  }, [avisar])

  useEffect(() => {
    cargar()
  }, [cargar])

  const ejecutar = async (clave, accion, mensaje) => {
    setGuardando(clave)
    try {
      await accion()
      avisar.exito(mensaje)
      await cargar()
    } catch (e) {
      avisar.error(e.message)
    } finally {
      setGuardando(null)
    }
  }

  const guardarPorDefecto = () =>
    ejecutar(
      'defecto',
      () =>
        api('/api/configuracion/', {
          metodo: 'PATCH',
          cuerpo: { botellas_por_lote: Number(porDefecto) },
        }),
      `Los proximos lotes se abriran con ${porDefecto} botellas.`,
    )

  const guardarCapacidad = () =>
    ejecutar(
      'capacidad',
      () =>
        api(`/api/lotes/${activo.id}/`, {
          metodo: 'PATCH',
          cuerpo: { capacidad_lote: Number(capacidad) },
        }),
      `Capacidad de ${activo.correlativo} actualizada.`,
    )

  const cerrarLote = () => {
    if (
      !window.confirm(
        `¿Cerrar ${activo.correlativo} con ${activo.total_inspecciones} de ${activo.capacidad_lote} botellas?\n\nSe abre un lote nuevo enseguida.`,
      )
    ) {
      return
    }
    return ejecutar(
      'cerrar',
      () => api(`/api/lotes/${activo.id}/cerrar/`, { metodo: 'POST' }),
      `${activo.correlativo} cerrado. Ya esta abierto el siguiente.`,
    )
  }

  if (cargando) {
    return (
      <div className="space-y-4">
        <EsqueletoTarjeta lineas={2} />
        <EsqueletoTarjeta lineas={4} />
      </div>
    )
  }

  const avance = activo?.capacidad_lote
    ? Math.min(100, Math.round((activo.total_inspecciones / activo.capacidad_lote) * 100))
    : 0
  const bajaDemasiado = activo && Number(capacidad) > 0 && Number(capacidad) <= activo.total_inspecciones

  return (
    <div className="space-y-4">
      <Tarjeta
        titulo="Tamaño de lote por defecto"
        icono={Package}
        descripcion={
          config?.ayuda?.botellas_por_lote ??
          'Se aplica a los lotes que se abran de aqui en adelante; no cambia el que esta en curso.'
        }
      >
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="por-defecto" className="sr-only">
            Botellas por lote
          </label>
          <input
            id="por-defecto"
            type="number"
            min="1"
            max="100000"
            value={porDefecto}
            onChange={(e) => setPorDefecto(e.target.value)}
            className={CLASES_NUMERO}
          />
          <span className="text-sm text-slate-400">botellas por lote</span>
          <Boton
            icono={Save}
            onClick={guardarPorDefecto}
            cargando={guardando === 'defecto'}
            disabled={guardando !== null || porDefecto === String(config?.botellas_por_lote)}
          >
            Guardar
          </Boton>
        </div>
      </Tarjeta>

      <Tarjeta titulo="Lote en curso">
        {!activo ? (
          <EstadoVacio
            icono={Package}
            titulo="No hay ningun lote abierto"
            mensaje="El primer lote se abre solo cuando la linea inspecciona la primera botella."
          />
        ) : (
          <>
            <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
              <span className="font-mono text-lg font-semibold text-cyan-400">{activo.correlativo}</span>
              <span className="cifra text-sm text-slate-300">
                {activo.total_inspecciones} / {activo.capacidad_lote} ({avance}%)
              </span>
            </div>
            <div
              className="mb-4 h-3 w-full overflow-hidden rounded-full bg-slate-700"
              role="progressbar"
              aria-valuenow={avance}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-500"
                style={{ width: `${avance}%` }}
              />
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <label htmlFor="capacidad" className="sr-only">
                Capacidad del lote activo
              </label>
              <input
                id="capacidad"
                type="number"
                min="1"
                max="100000"
                value={capacidad}
                onChange={(e) => setCapacidad(e.target.value)}
                className={CLASES_NUMERO}
              />
              <Boton
                icono={Save}
                onClick={guardarCapacidad}
                cargando={guardando === 'capacidad'}
                disabled={guardando !== null || capacidad === String(activo.capacidad_lote)}
              >
                Cambiar capacidad
              </Boton>
              <Boton
                icono={Square}
                variante="contorno"
                onClick={cerrarLote}
                cargando={guardando === 'cerrar'}
                disabled={guardando !== null}
              >
                Cerrar lote ahora
              </Boton>
            </div>

            <p className={`mt-2 text-xs ${bajaDemasiado ? 'text-amber-400' : 'text-slate-500'}`}>
              {bajaDemasiado
                ? `Con ${capacidad} botellas el lote ya estaria completo: al guardar se cierra y se abre el siguiente.`
                : 'Si baja la capacidad por debajo de lo ya producido, el lote se cierra en el acto.'}
            </p>
          </>
        )}
      </Tarjeta>

      <LotesTable lotes={lotes} />
    </div>
  )
}
