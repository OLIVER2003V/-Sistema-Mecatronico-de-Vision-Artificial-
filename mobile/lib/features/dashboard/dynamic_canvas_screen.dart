import 'package:flutter/material.dart';
import '../../core/auth_service.dart';
import '../../core/ia_service.dart';
import '../../core/reporte_exporter.dart';
import '../asistente/asistente_burbuja.dart';
import '../auth/login_screen.dart';
import 'componentes_dinamicos.dart';

class DynamicCanvasScreen extends StatefulWidget {
  final UsuarioSesion? usuarioSesion;

  const DynamicCanvasScreen({Key? key, this.usuarioSesion}) : super(key: key);

  @override
  _DynamicCanvasScreenState createState() => _DynamicCanvasScreenState();
}

class _DynamicCanvasScreenState extends State<DynamicCanvasScreen> {
  final List<ComponenteDinamicoData> _componentesActivos = [];

  String get _nombreUsuario => widget.usuarioSesion?.nombreCompleto ?? 'Operador';
  String get _rolUsuario => widget.usuarioSesion?.rol ?? 'OPERADOR';

  @override
  void initState() {
    super.initState();
  }

  /// Método público invocado desde la Burbuja del Asistente para procesar acciones de lienzo
  void procesarAccionCanvas(String accion, List<ComponenteDinamicoData> componentes) {
    setState(() {
      if (accion == 'limpiar') {
        _componentesActivos.clear();
      } else if (accion == 'reemplazar') {
        _componentesActivos.clear();
        _componentesActivos.addAll(componentes);
      } else {
        // 'agregar'
        for (var c in componentes.reversed) {
          _componentesActivos.removeWhere((item) => item.id == c.id);
          _componentesActivos.insert(0, c);
        }
      }
    });
  }

  void agregarComponenteDinamico(ComponenteDinamicoData nuevo) {
    setState(() {
      _componentesActivos.removeWhere((item) => item.tipo == nuevo.tipo);
      _componentesActivos.insert(0, nuevo);
    });
  }

  void _eliminarComponente(String id) {
    setState(() {
      _componentesActivos.removeWhere((item) => item.id == id);
    });
  }

  void _limpiarTapiz() {
    setState(() {
      _componentesActivos.clear();
    });
  }

  void _exportarCanvasCompleto() {
    if (_componentesActivos.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No hay reportes ni componentes generados en la página principal para exportar.')),
      );
      return;
    }

    final sb = StringBuffer();
    sb.writeln('# Reporte Consolidado de la Página Principal (SORT-MATIC)');
    sb.writeln('**Generado Por:** $_nombreUsuario ($_rolUsuario)');
    sb.writeln('**Fecha:** ${DateTime.now().toString().substring(0, 19)}');
    sb.writeln('**Cantidad de Reportes / Componentes Generados:** ${_componentesActivos.length}');
    sb.writeln('\n---');

    for (final comp in _componentesActivos) {
      sb.writeln('\n## ${comp.titulo}');
      final datos = comp.datos;

      switch (comp.tipo) {
        case TipoComponenteDinamico.reporteMarkdown:
          final contenido = datos['contenido'] ?? datos['texto'] ?? datos['markdown'] ?? '';
          sb.writeln(contenido);
          break;

        case TipoComponenteDinamico.kpiCard:
        case TipoComponenteDinamico.metricaConteo:
          final valor = datos['valor'] ?? datos['value'] ?? datos['conteo'] ?? '0';
          final subtitulo = datos['subtitulo'] ?? datos['subtitle'] ?? '';
          sb.writeln('- **Valor:** $valor');
          if (subtitulo.isNotEmpty) sb.writeln('- **Detalle:** $subtitulo');
          break;

        case TipoComponenteDinamico.tablaDatos:
          final encabezados = datos['encabezados'] as List? ?? datos['headers'] as List? ?? [];
          final filas = datos['filas'] as List? ?? datos['rows'] as List? ?? [];
          if (encabezados.isNotEmpty) {
            sb.writeln('| ${encabezados.join(' | ')} |');
            sb.writeln('| ${encabezados.map((_) => '---').join(' | ')} |');
            for (final fila in filas) {
              if (fila is List) {
                sb.writeln('| ${fila.join(' | ')} |');
              } else if (fila is Map) {
                sb.writeln('| ${fila.values.join(' | ')} |');
              }
            }
          }
          break;

        case TipoComponenteDinamico.graficoBarras:
        case TipoComponenteDinamico.graficoPie:
        case TipoComponenteDinamico.graficoBarrasMermas:
        case TipoComponenteDinamico.graficoDonutYield:
          final items = datos['datos'] as List? ?? datos['series'] as List? ?? datos['items'] as List? ?? [];
          if (items.isNotEmpty) {
            for (final item in items) {
              if (item is Map) {
                final label = item['etiqueta'] ?? item['nombre'] ?? item['x'] ?? 'Categoría';
                final val = item['valor'] ?? item['value'] ?? item['y'] ?? '0';
                sb.writeln('- **$label:** $val');
              }
            }
          } else {
            sb.writeln('- Gráfico visual generado.');
          }
          break;

        case TipoComponenteDinamico.alertaStatus:
        case TipoComponenteDinamico.estadoFaja:
          final msg = datos['mensaje'] ?? datos['estado'] ?? datos['status'] ?? 'Sin detalle';
          final nivel = datos['nivel'] ?? datos['level'] ?? 'INFO';
          sb.writeln('- **Nivel / Estado:** $nivel');
          sb.writeln('- **Mensaje:** $msg');
          break;
      }
    }

    ReporteExporter.mostrarOpcionesExportacion(
      context: context,
      contenidoMarkdown: sb.toString(),
      usuario: _nombreUsuario,
    );
  }

  void _ejecutarComandoFaja(String accion) async {
    final res = await IAService.enviarPregunta(
      pregunta: "$accion la faja transportadora",
      usuario: _nombreUsuario,
      rol: _rolUsuario,
    );

    if (!mounted) return;

    final msg = res['respuesta'] ?? 'Comando ejecutado.';
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: accion == 'STOP' ? Colors.redAccent : Colors.green,
      ),
    );
  }

  void _abrirAsistenteBurbuja() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => AsistenteBurbujaModal(
        usuarioSesion: widget.usuarioSesion,
        onNuevoComponenteSolicitado: (componente) {
          agregarComponenteDinamico(componente);
        },
        onAccionCanvasSolicitada: (accion, componentes) {
          procesarAccionCanvas(accion, componentes);
        },
      ),
    );
  }

  void _cerrarSesion() async {
    await AuthService.cerrarSesion();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (context) => const LoginScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 4,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "SORT-MATIC Canvas",
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 1.2),
            ),
            Text(
              "👤 $_nombreUsuario ($_rolUsuario)",
              style: const TextStyle(fontSize: 11, color: Colors.cyanAccent),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.file_download_outlined, color: Colors.cyanAccent),
            onPressed: _exportarCanvasCompleto,
            tooltip: 'Exportar Reportes a PDF / Excel',
          ),
          if (_componentesActivos.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete_sweep_rounded, color: Colors.orangeAccent),
              onPressed: _limpiarTapiz,
              tooltip: 'Limpiar Tapiz',
            ),
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Colors.redAccent),
            onPressed: _cerrarSesion,
            tooltip: 'Cerrar Sesión',
          ),
        ],
      ),
      body: _componentesActivos.isEmpty
          ? _buildEstadoTapizVacio()
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _componentesActivos.length,
              itemBuilder: (context, index) {
                final comp = _componentesActivos[index];
                return ComponenteDinamicoWidget(
                  data: comp,
                  onEliminar: () => _eliminarComponente(comp.id),
                  onEjecutarComando: _ejecutarComandoFaja,
                );
              },
            ),

      // BOTÓN FLOTANTE BURBUJA ASISTENTE IA
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _abrirAsistenteBurbuja,
        backgroundColor: Colors.transparent,
        elevation: 8,
        label: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(30),
            gradient: LinearGradient(
              colors: [Colors.cyan.shade500, Colors.blue.shade700],
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.cyan.withOpacity(0.4),
                blurRadius: 15,
                spreadRadius: 2,
              )
            ],
          ),
          child: Row(
            children: const [
              Icon(Icons.smart_toy_rounded, color: Colors.white, size: 24),
              SizedBox(width: 8),
              Text(
                "Asistente IA",
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEstadoTapizVacio() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                shape: BoxShape.circle,
                border: Border.all(color: Colors.cyan.withOpacity(0.3), width: 2),
              ),
              child: const Icon(
                Icons.space_dashboard_rounded,
                size: 64,
                color: Colors.cyanAccent,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              "TAPIZ PRINCIPAL VACÍO",
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.5,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              "Haz una consulta en la burbuja del Asistente IA 🤖 para generar tarjetas de botellas, gráficos de mermas o controles de la faja en tiempo real.",
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.grey.shade400,
                fontSize: 13,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 28),
            ElevatedButton.icon(
              onPressed: _abrirAsistenteBurbuja,
              icon: const Icon(Icons.smart_toy_rounded, color: Colors.black),
              label: const Text("Abrir Asistente IA", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold)),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.cyanAccent,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
