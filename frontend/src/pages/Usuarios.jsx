// Gestion de usuarios del Administrador de sistemas.
//
// El backend impide quedarse sin administradores (no se puede borrar,
// desactivar ni degradar al ultimo): si eso pasa responde 400 y el mensaje se
// muestra tal cual. Aca no se duplica esa regla, se confia en el servidor.
import { Pencil, Plus, Search, Trash2, UserX, Users as IconoUsuarios } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { api, filas } from '../api/cliente.js'
import Boton from '../components/ui/Boton.jsx'
import { CampoCasilla, CampoSelect, CampoTexto } from '../components/ui/Campo.jsx'
import EstadoVacio from '../components/ui/EstadoVacio.jsx'
import { EsqueletoTabla } from '../components/ui/Esqueleto.jsx'
import Insignia from '../components/ui/Insignia.jsx'
import Modal from '../components/ui/Modal.jsx'
import { useAvisos } from '../hooks/useAvisos.jsx'
import { useSesion } from '../hooks/useSesion.jsx'

const ROLES = [
  {
    valor: 'OPERADOR',
    texto: 'Operador de planta',
    ayuda: 'Monitorea la linea y arranca/para la faja.',
  },
  {
    valor: 'SUPERVISOR',
    texto: 'Supervisor de calidad',
    ayuda: 'Analiticos, lotes, parametros de inspeccion y galeria de mermas.',
  },
  {
    valor: 'ADMINISTRADOR',
    texto: 'Administrador de sistemas',
    ayuda: 'Gestiona usuarios y bitacora. Ademas accede a todo lo anterior.',
  },
]

const TONO_ROL = { ADMINISTRADOR: 'violeta', SUPERVISOR: 'info', OPERADOR: 'neutro' }

const VACIO = {
  username: '',
  first_name: '',
  last_name: '',
  email: '',
  telefono: '',
  rol: 'OPERADOR',
  is_active: true,
  password: '',
}

function Formulario({ inicial, onGuardar, onCerrar, guardando, error }) {
  const [datos, setDatos] = useState(inicial)
  const editando = Boolean(inicial.id)
  const campo = (k) => (e) => setDatos({ ...datos, [k]: e.target.value })

  return (
    <Modal
      titulo={editando ? `Editar ${inicial.username}` : 'Nuevo usuario'}
      onCerrar={onCerrar}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault()
          onGuardar(datos)
        }}
        className="space-y-3.5 p-4"
      >
        <CampoTexto
          etiqueta="Usuario"
          requerido
          value={datos.username}
          onChange={campo('username')}
          autoComplete="off"
          autoFocus={!editando}
          error={error}
        />

        <div className="grid grid-cols-2 gap-3">
          <CampoTexto etiqueta="Nombre" value={datos.first_name} onChange={campo('first_name')} />
          <CampoTexto etiqueta="Apellido" value={datos.last_name} onChange={campo('last_name')} />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <CampoTexto etiqueta="Correo" type="email" value={datos.email} onChange={campo('email')} />
          <CampoTexto etiqueta="Telefono" value={datos.telefono} onChange={campo('telefono')} />
        </div>

        <CampoSelect
          etiqueta="Rol"
          requerido
          value={datos.rol}
          onChange={campo('rol')}
          opciones={ROLES}
          ayuda={ROLES.find((r) => r.valor === datos.rol)?.ayuda}
        />

        <CampoTexto
          etiqueta={editando ? 'Nueva contraseña' : 'Contraseña'}
          type="password"
          requerido={!editando}
          value={datos.password}
          onChange={campo('password')}
          autoComplete="new-password"
          ayuda={
            editando
              ? 'Dejar vacio para no cambiarla.'
              : 'Minimo 8 caracteres, que no sea solo numeros ni una contraseña comun.'
          }
        />

        <CampoCasilla
          etiqueta="Cuenta activa"
          ayuda="Si se desactiva, el usuario no puede iniciar sesion pero su historial se conserva."
          checked={datos.is_active}
          onChange={(e) => setDatos({ ...datos, is_active: e.target.checked })}
        />

        <div className="flex justify-end gap-3 pt-2">
          <Boton type="button" variante="contorno" onClick={onCerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" cargando={guardando}>
            {editando ? 'Guardar cambios' : 'Crear usuario'}
          </Boton>
        </div>
      </form>
    </Modal>
  )
}

export default function Usuarios() {
  const avisar = useAvisos()
  const { usuario: yo, recargar } = useSesion()
  const [lista, setLista] = useState([])
  const [buscar, setBuscar] = useState('')
  const [filtroRol, setFiltroRol] = useState('')
  const [cargando, setCargando] = useState(true)
  const [editando, setEditando] = useState(null)
  const [guardando, setGuardando] = useState(false)
  const [errorForm, setErrorForm] = useState(null)

  const cargar = useCallback(async () => {
    const parametros = new URLSearchParams()
    if (buscar) parametros.set('buscar', buscar)
    if (filtroRol) parametros.set('rol', filtroRol)
    try {
      setLista(filas(await api(`/api/usuarios/?${parametros.toString()}`)))
    } catch (e) {
      avisar.error(e.message)
    } finally {
      setCargando(false)
    }
  }, [buscar, filtroRol, avisar])

  useEffect(() => {
    const id = setTimeout(cargar, 250) // no consultar en cada tecla
    return () => clearTimeout(id)
  }, [cargar])

  const guardar = async (datos) => {
    setGuardando(true)
    setErrorForm(null)
    const cuerpo = { ...datos }
    if (!cuerpo.password) delete cuerpo.password
    try {
      if (datos.id) {
        await api(`/api/usuarios/${datos.id}/`, { metodo: 'PATCH', cuerpo })
        avisar.exito(`Usuario ${datos.username} actualizado.`)
        if (datos.id === yo?.id) await recargar()
      } else {
        await api('/api/usuarios/', { metodo: 'POST', cuerpo })
        avisar.exito(`Usuario ${datos.username} creado.`)
      }
      setEditando(null)
      await cargar()
    } catch (e) {
      setErrorForm(e.message)
    } finally {
      setGuardando(false)
    }
  }

  const eliminar = async (fila) => {
    if (!window.confirm(`¿Eliminar al usuario "${fila.username}"?\n\nNo se puede deshacer.`)) return
    try {
      await api(`/api/usuarios/${fila.id}/`, { metodo: 'DELETE' })
      avisar.exito(`Usuario ${fila.username} eliminado.`)
      await cargar()
    } catch (e) {
      avisar.error(e.message)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-400">
          Altas, bajas, cambios de rol y reseteo de contraseñas.
        </p>
        <Boton
          icono={Plus}
          onClick={() => {
            setErrorForm(null)
            setEditando({ ...VACIO })
          }}
        >
          Nuevo usuario
        </Boton>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="min-w-[14rem] flex-1">
          <CampoTexto
            icono={Search}
            value={buscar}
            onChange={(e) => setBuscar(e.target.value)}
            placeholder="Buscar por nombre, usuario o correo"
            aria-label="Buscar usuarios"
          />
        </div>
        <CampoSelect
          value={filtroRol}
          onChange={(e) => setFiltroRol(e.target.value)}
          aria-label="Filtrar por rol"
          opciones={[{ valor: '', texto: 'Todos los roles' }, ...ROLES]}
        />
      </div>

      {cargando ? (
        <EsqueletoTabla filas={4} columnas={5} />
      ) : lista.length === 0 ? (
        <EstadoVacio
          icono={IconoUsuarios}
          titulo="Ningun usuario coincide con la busqueda"
          mensaje="Pruebe con otro texto o quite el filtro de rol."
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-800/40">
          <table className="w-full text-left text-sm">
            <thead className="text-slate-400">
              <tr className="border-b border-slate-700">
                <th scope="col" className="p-3">Usuario</th>
                <th scope="col" className="hidden p-3 sm:table-cell">Nombre</th>
                <th scope="col" className="p-3">Rol</th>
                <th scope="col" className="p-3">Estado</th>
                <th scope="col" className="hidden p-3 lg:table-cell">Ultimo acceso</th>
                <th scope="col" className="p-3 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {lista.map((fila) => (
                <tr
                  key={fila.id}
                  className="border-b border-slate-800 text-slate-200 transition-colors last:border-0 hover:bg-slate-800/40"
                >
                  <td className="p-3 font-mono">
                    {fila.username}
                    {fila.id === yo?.id && (
                      <span className="ml-2 text-xs font-sans text-cyan-400">(usted)</span>
                    )}
                  </td>
                  <td className="hidden p-3 sm:table-cell">
                    {[fila.first_name, fila.last_name].filter(Boolean).join(' ') || '—'}
                  </td>
                  <td className="p-3">
                    <Insignia tono={TONO_ROL[fila.rol] ?? 'neutro'}>{fila.rol_nombre}</Insignia>
                  </td>
                  <td className="p-3">
                    {fila.is_active ? (
                      <Insignia tono="exito">Activo</Insignia>
                    ) : (
                      <Insignia tono="neutro" icono={UserX}>
                        Inactivo
                      </Insignia>
                    )}
                  </td>
                  <td className="hidden p-3 text-slate-400 lg:table-cell">
                    {fila.last_login ? new Date(fila.last_login).toLocaleString() : 'nunca'}
                  </td>
                  <td className="p-3">
                    <div className="flex justify-end gap-2">
                      <Boton
                        variante="contorno"
                        tamano="sm"
                        icono={Pencil}
                        aria-label={`Editar ${fila.username}`}
                        onClick={() => {
                          setErrorForm(null)
                          setEditando({ ...VACIO, ...fila, password: '' })
                        }}
                      />
                      <Boton
                        variante="contorno"
                        tamano="sm"
                        icono={Trash2}
                        aria-label={`Eliminar ${fila.username}`}
                        className="hover:border-red-500/60 hover:text-red-400"
                        onClick={() => eliminar(fila)}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editando && (
        <Formulario
          inicial={editando}
          onGuardar={guardar}
          onCerrar={() => setEditando(null)}
          guardando={guardando}
          error={errorForm}
        />
      )}
    </div>
  )
}
