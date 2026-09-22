// Modal del Asistente Virtual IA y Generador de Reportes Dinámicos
// Soporta prompt libre por texto, dictado por voz (Web Speech API)
// y exportación directa a PDF e EXCEL.
import {
  Bot,
  Check,
  Copy,
  FileSpreadsheet,
  FileText,
  Loader2,
  Mic,
  MicOff,
  Printer,
  Send,
  Sparkles,
  User,
  Wand2,
  X,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useSesion } from '../hooks/useSesion.jsx'
import Boton from './ui/Boton.jsx'

const PROMPTS_SUGERIDOS = [
  '📊 Reporte Ejecutivo de Mermas y Calidad del Lote',
  '⚡ Análisis de Eficiencia y Estado de la Faja Transportadora',
  '⚠️ Diagnóstico de Anomalías y Descalibración de Estaciones',
  '📈 Resumen de Producción por Turno e Inspección Físico-Óptica',
]

// Convertidor ligero de Markdown a HTML para vista y PDF
function markdownAHtml(md) {
  if (!md) return ''
  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Encabezados
    .replace(/^### (.*$)/gim, '<h3 class="text-base font-bold text-cyan-400 mt-4 mb-2">$1</h3>')
    .replace(/^## (.*$)/gim, '<h2 class="text-lg font-bold text-cyan-300 mt-5 mb-2 border-b border-slate-700 pb-1">$1</h2>')
    .replace(/^# (.*$)/gim, '<h1 class="text-xl font-extrabold text-cyan-200 mt-6 mb-3">$1</h1>')
    // Negrita e itálica
    .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-amber-300">$1</strong>')
    .replace(/\*(.*?)\*/g, '<em class="italic text-slate-300">$1</em>')
    // Listas
    .replace(/^\* (.*$)/gim, '<li class="ml-4 list-disc text-slate-300 my-1">$1</li>')
    .replace(/^- (.*$)/gim, '<li class="ml-4 list-disc text-slate-300 my-1">$1</li>')
    // Saltos de línea
    .replace(/\n/g, '<br />')

  return html
}

// Exportador a PDF utilizando la API de Impresión del Navegador con estilo industrial
function exportarPDF(reporteMarkdown, titulo = 'Reporte Ejecutivo SORT-MATIC', usuario = 'Supervisor') {
  const ventana = window.open('', '_blank')
  if (!ventana) {
    alert('Permite las ventanas emergentes en tu navegador para generar el PDF.')
    return
  }

  const htmlContenido = markdownAHtml(reporteMarkdown)

  ventana.document.write(`
    <!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8">
      <title>${titulo}</title>
      <style>
        body {
          font-family: 'Segoe UI', Arial, sans-serif;
          margin: 0;
          padding: 40px;
          color: #1e293b;
          background: #ffffff;
          line-height: 1.6;
        }
        .header {
          border-bottom: 3px solid #0891b2;
          padding-bottom: 16px;
          margin-bottom: 24px;
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
        }
        .brand {
          font-size: 24px;
          font-weight: 800;
          color: #0f172a;
          letter-spacing: -0.5px;
        }
        .brand span { color: #0891b2; }
        .meta {
          font-size: 11px;
          color: #64748b;
          text-align: right;
        }
        .title-box {
          background: #f8fafc;
          border-left: 4px solid #0891b2;
          padding: 12px 16px;
          margin-bottom: 24px;
          border-radius: 4px;
        }
        .title-box h1 {
          margin: 0;
          font-size: 18px;
          color: #0f172a;
        }
        h1, h2, h3 { color: #0891b2; margin-top: 20px; }
        ul, ol { padding-left: 20px; }
        li { margin-bottom: 4px; }
        strong { color: #0f172a; }
        .footer {
          margin-top: 50px;
          border-top: 1px solid #e2e8f0;
          padding-top: 16px;
          font-size: 11px;
          color: #94a3b8;
          text-align: center;
        }
      </style>
    </head>
    <body>
      <div class="header">
        <div>
          <div class="brand">SORT-<span>MATIC</span></div>
          <div style="font-size: 12px; color: #475569;">Sistema Mecatrónico de Visión Artificial · EMBOL S.A.</div>
        </div>
        <div class="meta">
          <div><strong>Fecha:</strong> ${new Date().toLocaleString()}</div>
          <div><strong>Generado Por:</strong> ${usuario}</div>
        </div>
      </div>
      <div class="title-box">
        <h1>${titulo}</h1>
      </div>
      <div class="content">
        ${htmlContenido}
      </div>
      <div class="footer">
        SORT-MATIC Industrial AI System — Reporte Generado Dinámicamente por IA
      </div>
      <script>
        window.onload = function() {
          setTimeout(function() {
            window.print();
          }, 300);
        };
      </script>
    </body>
    </html>
  `)
  ventana.document.close()
}

// Exportador a EXCEL (formato .csv estructurado compatible con UTF-8 para Excel)
function exportarExcel(reporteMarkdown, titulo = 'Reporte_SORTMATIC', usuario = 'Supervisor') {
  const lineas = reporteMarkdown.split('\n')
  let csv = '\uFEFF' // BOM para UTF-8 en Microsoft Excel

  csv += `SORT-MATIC - REPORTE DE PRODUCCION Y IA GENERATIVA\n`
  csv += `Fecha de Generacion,${new Date().toLocaleString()}\n`
  csv += `Generado Por,${usuario}\n\n`
  csv += `Seccion / Categoria,Metrica / Detalle,Valor / Estado\n`

  let seccion = 'Resumen General'

  for (const l of lineas) {
    const trim = l.trim()
    if (!trim) continue

    if (trim.startsWith('#')) {
      seccion = trim.replace(/#/g, '').replace(/\*/g, '').trim()
      csv += `"${escaparCsv(seccion)}","---","---"\n`
    } else if (trim.startsWith('*') || trim.startsWith('-')) {
      const contenido = trim.substring(1).replace(/\*/g, '').trim()
      const partes = contenido.split(':')
      if (partes.length >= 2) {
        const clave = partes[0].trim()
        const valor = partes.slice(1).join(':').trim()
        csv += `"${escaparCsv(seccion)}","${escaparCsv(clave)}","${escaparCsv(valor)}"\n`
      } else {
        csv += `"${escaparCsv(seccion)}","${escaparCsv(contenido)}","OK"\n`
      }
    } else {
      const partes = trim.split(':')
      if (partes.length >= 2) {
        const clave = partes[0].replace(/\*/g, '').trim()
        const valor = partes.slice(1).join(':').replace(/\*/g, '').trim()
        csv += `"${escaparCsv(seccion)}","${escaparCsv(clave)}","${escaparCsv(valor)}"\n`
      } else {
        csv += `"${escaparCsv(seccion)}","${escaparCsv(trim.replace(/\*/g, ''))}","Info"\n`
      }
    }
  }

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url;
  a.download = `${titulo.replace(/\s+/g, '_')}_${Date.now()}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function escapingCsv(texto) {
  return (texto || '').replace(/"/g, '""')
}

function escaparCsv(t) {
  return escapingCsv(t)
}

export default function AsistenteReportesModal({ onCerrar }) {
  const { usuario, rol } = useSesion()
  const [prompt, setPrompt] = useState('')
  const [cargando, setCargando] = useState(false)
  const [reporteActual, setReporteActual] = useState('')
  const [escuchandoVoz, setEscuchandoVoz] = useState(false)
  const [copiado, setCopiado] = useState(false)

  const recognitionRef = useRef(null)
  const scrollRef = useRef(null)

  const nombreUsuario =
    [usuario?.first_name, usuario?.last_name].filter(Boolean).join(' ') || usuario?.username || 'Supervisor'

  // Inicializar reconocimiento de voz Web Speech API si el navegador lo soporta
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      const rec = new SpeechRecognition()
      rec.continuous = false
      rec.interimResults = false
      rec.lang = 'es-ES'

      rec.onresult = (e) => {
        const transcripcion = e.results[0][0].transcript
        setPrompt((prev) => (prev ? `${prev} ${transcripcion}` : transcripcion))
        setEscuchandoVoz(false)
      }

      rec.onerror = () => setEscuchandoVoz(false)
      rec.onend = () => setEscuchandoVoz(false)
      recognitionRef.current = rec
    }
  }, [])

  const toggleVoz = () => {
    if (!recognitionRef.current) {
      alert('Tu navegador no soporta el reconocimiento de voz por micrófono.')
      return
    }
    if (escuchandoVoz) {
      recognitionRef.current.stop()
      setEscuchandoVoz(false)
    } else {
      setEscuchandoVoz(true)
      recognitionRef.current.start()
    }
  }

  const generarReporte = async (promptPersonalizado) => {
    const textoConsulta = promptPersonalizado || prompt
    if (!textoConsulta.trim()) return

    setCargando(true)
    setReporteActual('')

    try {
      // Determinar si es un pedido explícito de reporte o una consulta conversacional
      const urlIa =
        import.meta.env.VITE_IA_URL ||
        (window.location.hostname === 'localhost' ? 'http://localhost:8001' : '/ia')

      let res
      if (textoConsulta.toLowerCase().includes('reporte') || textoConsulta.toLowerCase().includes('ejecutivo')) {
        const resp = await fetch(`${urlIa}/reporte`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tipo: 'turno', usuario: nombreUsuario }),
        })
        const data = await resp.json()
        res = data.reporte_markdown || 'No se recibió respuesta del microservicio de IA.'
      } else {
        const resp = await fetch(`${urlIa}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pregunta: textoConsulta, usuario: nombreUsuario, rol }),
        })
        const data = await resp.json()
        res = data.respuesta || 'No se recibió respuesta.'
      }

      setReporteActual(res)
    } catch (err) {
      console.error('Error generando reporte con IA:', err)
      setReporteActual(
        `⚠️ **Error de conexión con el Microservicio de IA:** No se pudo contactar al servidor (${err.message}). Intenta nuevamente.`,
      )
    } finally {
      setCargando(false)
    }
  }

  const copiarTexto = () => {
    if (!reporteActual) return
    navigator.clipboard.writeText(reporteActual)
    setCopiado(true)
    setTimeout(() => setCopiado(false), 2000)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
      onMouseDown={(e) => e.target === e.currentTarget && onCerrar()}
    >
      <div className="flex h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
        {/* Cabecera del Modal */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/20 text-cyan-400">
              <Sparkles className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Generador Dinámico de Reportes IA</h3>
              <p className="text-xs text-slate-400">
                Consulta por voz o prompt libre · Exportación a PDF y Excel
              </p>
            </div>
          </div>
          <button
            onClick={onCerrar}
            className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Cuerpo Principal */}
        <div className="flex flex-1 flex-col overflow-hidden p-6">
          {/* Prompts Sugeridos Rápidos */}
          <div className="mb-4 flex flex-wrap gap-2">
            {PROMPTS_SUGERIDOS.map((p) => (
              <button
                key={p}
                onClick={() => {
                  setPrompt(p)
                  generarReporte(p)
                }}
                className="rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-cyan-500 hover:bg-cyan-500/10 hover:text-cyan-300"
              >
                {p}
              </button>
            ))}
          </div>

          {/* Área de Visualización del Reporte */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950/80 p-5 font-sans"
          >
            {cargando ? (
              <div className="flex h-full flex-col items-center justify-center space-y-4 text-cyan-400">
                <Loader2 className="h-10 w-10 animate-spin" />
                <p className="text-sm font-medium">Analizando datos de la planta e inspecciones con Gemini AI...</p>
              </div>
            ) : reporteActual ? (
              <div>
                <div
                  className="prose prose-invert max-w-none text-sm text-slate-200"
                  dangerouslySetInnerHTML={{ __html: markdownAHtml(reporteActual) }}
                />
              </div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center text-center text-slate-500">
                <Wand2 className="mb-3 h-12 w-12 text-slate-700" />
                <p className="text-base font-semibold text-slate-400">¿Qué reporte deseas generar hoy?</p>
                <p className="mt-1 max-w-md text-xs">
                  Haz un clic en cualquiera de las sugerencias superiores, dicta tu instrucción con el micrófono o escribe un prompt libre abajo.
                </p>
              </div>
            )}
          </div>

          {/* Barra de Acciones y Exportación (si existe reporte cargado) */}
          {reporteActual && !cargando && (
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-4">
              <div className="flex items-center gap-2">
                <button
                  onClick={copiarTexto}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:bg-slate-700"
                >
                  {copiado ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  {copiado ? 'Copiado!' : 'Copiar Texto'}
                </button>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => exportarPDF(reporteActual, 'Reporte Ejecutivo SORT-MATIC', nombreUsuario)}
                  className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-red-500 shadow-lg"
                >
                  <FileText className="h-4 w-4" /> Exportar PDF
                </button>
                <button
                  onClick={() => exportarExcel(reporteActual, 'Reporte_SORTMATIC', nombreUsuario)}
                  className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white transition-colors hover:bg-emerald-500 shadow-lg"
                >
                  <FileSpreadsheet className="h-4 w-4" /> Exportar Excel
                </button>
              </div>
            </div>
          )}

          {/* Entrada de Texto y Micrófono */}
          <div className="mt-4 flex items-center gap-2">
            <button
              onClick={toggleVoz}
              className={`flex h-11 w-11 items-center justify-center rounded-xl border transition-all ${
                escuchandoVoz
                  ? 'animate-pulse border-red-500 bg-red-500/20 text-red-400'
                  : 'border-slate-700 bg-slate-800 text-slate-300 hover:border-cyan-500 hover:text-cyan-300'
              }`}
              title={escuchandoVoz ? 'Detener Micrófono' : 'Dictar por Voz (Micrófono)'}
            >
              {escuchandoVoz ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
            </button>

            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && generarReporte()}
              placeholder={escuchandoVoz ? 'Escuchando dictado por voz...' : 'Escribe tu consulta o pide cualquier tipo de reporte...'}
              className="flex-1 rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition-colors focus:border-cyan-500"
            />

            <Boton
              icono={Send}
              onClick={() => generarReporte()}
              cargando={cargando}
              disabled={cargando || !prompt.trim()}
            >
              Generar
            </Boton>
          </div>
        </div>
      </div>
    </div>
  )
}
