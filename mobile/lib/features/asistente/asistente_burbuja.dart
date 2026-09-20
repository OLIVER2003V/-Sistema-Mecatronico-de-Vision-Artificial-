import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import '../../core/auth_service.dart';
import '../../core/ia_service.dart';
import '../../core/chat_history_service.dart';
import '../dashboard/componentes_dinamicos.dart';

class AsistenteBurbujaModal extends StatefulWidget {
  final UsuarioSesion? usuarioSesion;
  final VoidCallback? onComandoEjecutado;
  final Function(ComponenteDinamicoData)? onNuevoComponenteSolicitado;
  final Function(String accion, List<ComponenteDinamicoData> componentes)? onAccionCanvasSolicitada;

  const AsistenteBurbujaModal({
    Key? key,
    this.usuarioSesion,
    this.onComandoEjecutado,
    this.onNuevoComponenteSolicitado,
    this.onAccionCanvasSolicitada,
  }) : super(key: key);

  @override
  _AsistenteBurbujaModalState createState() => _AsistenteBurbujaModalState();
}

class _AsistenteBurbujaModalState extends State<AsistenteBurbujaModal> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<MensajeHistorial> _mensajes = [];

  bool _estaCargando = false;
  bool _escuchandoVoz = false;
  late stt.SpeechToText _speech;
  late FlutterTts _flutterTts;

  String get _username => widget.usuarioSesion?.username ?? 'operador';
  String get _nombreUsuario => widget.usuarioSesion?.nombreCompleto ?? 'Operador';
  String get _rolUsuario => widget.usuarioSesion?.rol ?? 'OPERADOR';
  String get _rolEtiqueta => widget.usuarioSesion?.esSupervisor == true ? 'Supervisor' : 'Operador';

  @override
  void initState() {
    super.initState();
    _speech = stt.SpeechToText();
    _flutterTts = FlutterTts();
    _initTts();
    _cargarHistorialUsuario();
  }

  void _initTts() async {
    await _flutterTts.setLanguage("es-ES");
    await _flutterTts.setSpeechRate(0.9);
  }

  void _cargarHistorialUsuario() async {
    final historial = await ChatHistoryService.cargarHistorial(_username);
    setState(() {
      _mensajes.clear();
      if (historial.isNotEmpty) {
        _mensajes.addAll(historial);
      } else {
        // Mensaje de bienvenida inicial si es el primer chat
        final msjInicial = MensajeHistorial(
          id: 'init_1',
          texto: "🤖 **Asistente Virtual:** Hola **$_nombreUsuario** ($rolLabel). Escribe o dicta tu consulta. Cada solicitud generará componentes visuales en tu pantalla principal.",
          esUsuario: false,
          fecha: DateTime.now(),
        );
        _mensajes.add(msjInicial);
        ChatHistoryService.agregarMensaje(_username, msjInicial);
      }
    });
    _scrollHaciaAbajo();
  }

  String get rolLabel => _rolEtiqueta;

  void _hablar(String texto) async {
    String limpio = texto.replaceAll(RegExp(r'[*#_`]'), '');
    await _flutterTts.speak(limpio);
  }

  void _escucharVoz() async {
    if (!_escuchandoVoz) {
      bool disponible = await _speech.initialize();
      if (disponible) {
        setState(() => _escuchandoVoz = true);
        _speech.listen(
          onResult: (val) {
            setState(() {
              _textController.text = val.recognizedWords;
            });
          },
        );
      }
    } else {
      setState(() => _escuchandoVoz = false);
      _speech.stop();
      if (_textController.text.isNotEmpty) {
        _enviarMensaje();
      }
    }
  }

  void _enviarMensaje([String? textoPersonalizado]) async {
    final texto = textoPersonalizado ?? _textController.text.trim();
    if (texto.isEmpty) return;

    _textController.clear();
    final mensajeUser = MensajeHistorial(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      texto: texto,
      esUsuario: true,
      fecha: DateTime.now(),
    );

    setState(() {
      _mensajes.add(mensajeUser);
      _estaCargando = true;
    });
    _scrollHaciaAbajo();
    await ChatHistoryService.agregarMensaje(_username, mensajeUser);

    // Preparar historial reciente para mantener el contexto de conversación con Gemini
    final historialTurnos = _mensajes.map((m) => {
      'es_usuario': m.esUsuario,
      'texto': m.texto,
    }).toList();

    // Consulta al Microservicio de IA con conversacion_id e historial
    final res = await IAService.enviarPregunta(
      pregunta: texto,
      usuario: _nombreUsuario,
      rol: _rolUsuario,
      conversacionId: _username,
      historial: historialTurnos,
    );

    if (!mounted) return;

    final respuestaText = res['respuesta'] ?? 'Sin respuesta';
    final accionCanvas = (res['accion_canvas'] ?? 'reemplazar').toString();
    final rawWidgets = res['widgets'] is List ? (res['widgets'] as List) : [];

    List<ComponenteDinamicoData> nuevosComponentes = [];
    List<Map<String, dynamic>> widgetsJson = [];

    for (var w in rawWidgets) {
      if (w is Map) {
        final wMap = Map<String, dynamic>.from(w);
        widgetsJson.add(wMap);
        nuevosComponentes.add(ComponenteDinamicoData.fromJson(wMap));
      }
    }

    final mensajeIA = MensajeHistorial(
      id: (DateTime.now().millisecondsSinceEpoch + 1).toString(),
      texto: respuestaText,
      esUsuario: false,
      fecha: DateTime.now(),
      widgets: widgetsJson.isNotEmpty ? widgetsJson : null,
      accionCanvas: accionCanvas,
    );

    setState(() {
      _estaCargando = false;
      _mensajes.add(mensajeIA);
    });
    _scrollHaciaAbajo();
    await ChatHistoryService.agregarMensaje(_username, mensajeIA);

    _hablar(respuestaText);

    // Notificar al lienzo principal con la acción y los componentes
    if (nuevosComponentes.isNotEmpty) {
      widget.onAccionCanvasSolicitada?.call(accionCanvas, nuevosComponentes);
    } else {
      // Fallback si no vinieron widgets explícitos en JSON
      _detectarYGenerarComponentesDinamicos(texto, respuestaText, res);
    }
  }

  void _detectarYGenerarComponentesDinamicos(String pregunta, String respuesta, Map<String, dynamic> resRaw) {
    final pLower = pregunta.toLowerCase();
    final ctx = (resRaw['contexto_usado'] ?? '').toString();

    // Extraer datos reales del contexto RAG devuelto por el backend Django
    final int? totalReal = _extraerInt(ctx, r'Total Botellas Inspeccionadas \(Lote Activo\):\s*(\d+)');
    final int? aceptadasReal = _extraerInt(ctx, r'Conteo Aceptadas:\s*(\d+)');
    final int? sinTapaReal = _extraerInt(ctx, r'Sin Tapa:\s*(\d+)');
    final int? sinEtiquetaReal = _extraerInt(ctx, r'Sin Etiqueta:\s*(\d+)');
    final int? defectuosaReal = _extraerInt(ctx, r'Conteo Defectuosas Estación 1 \(Físicas\):\s*(\d+)');
    final int? llenadoBajoReal = _extraerInt(ctx, r'Conteo Llenado Bajo Estación 2:\s*(\d+)');

    final double? yieldRateReal = _extraerDouble(ctx, r'Tasa de Aprobación \(Yield Rate\):\s*([\d\.]+)%');
    final double? rejectRateReal = _extraerDouble(ctx, r'Tasa de Rechazo \(Mermas\):\s*([\d\.]+)%');

    final int total = totalReal ?? 0;
    final int aceptadas = aceptadasReal ?? 0;
    final int defectuosa = defectuosaReal ?? 0;
    final int llenadoBajo = llenadoBajoReal ?? 0;
    final int rechazadas = (total > 0 && total >= aceptadas) ? (total - aceptadas) : (defectuosa + llenadoBajo);

    if (pLower.contains('botella') || pLower.contains('conteo') || pLower.contains('inspección') || pLower.contains('inspeccion')) {
      widget.onNuevoComponenteSolicitado?.call(
        ComponenteDinamicoData(
          id: 'conteo_${DateTime.now().millisecondsSinceEpoch}',
          titulo: 'Botellas Inspeccionadas en Planta',
          tipo: TipoComponenteDinamico.metricaConteo,
          datos: {
            'total': total,
            'aceptadas': aceptadas,
            'rechazadas': rechazadas,
          },
        ),
      );
    } else if (pLower.contains('gráfico') || pLower.contains('grafico') || pLower.contains('merma') || pLower.contains('defecto')) {
      widget.onNuevoComponenteSolicitado?.call(
        ComponenteDinamicoData(
          id: 'mermas_${DateTime.now().millisecondsSinceEpoch}',
          titulo: 'Análisis de Mermas por Estación',
          tipo: TipoComponenteDinamico.graficoBarrasMermas,
          datos: {
            'sin_tapa': sinTapaReal ?? 0,
            'sin_etiqueta': sinEtiquetaReal ?? 0,
            'defectuosa': defectuosa,
            'llenado_bajo': llenadoBajo,
          },
        ),
      );
    } else if (pLower.contains('rendimiento') || pLower.contains('yield') || pLower.contains('tasa')) {
      widget.onNuevoComponenteSolicitado?.call(
        ComponenteDinamicoData(
          id: 'yield_${DateTime.now().millisecondsSinceEpoch}',
          titulo: 'Rendimiento Global de Calidad',
          tipo: TipoComponenteDinamico.graficoDonutYield,
          datos: {
            'yield_rate': yieldRateReal ?? 0.0,
            'reject_rate': rejectRateReal ?? 0.0,
          },
        ),
      );
    } else if (pLower.contains('faja') || pLower.contains('parar') || pLower.contains('arrancar') || pLower.contains('estado')) {
      bool enMarcha = ctx.contains('EN MARCHA') || !pLower.contains('parar');
      bool arduino = !ctx.contains('DESCONECTADO');
      widget.onNuevoComponenteSolicitado?.call(
        ComponenteDinamicoData(
          id: 'faja_${DateTime.now().millisecondsSinceEpoch}',
          titulo: 'Control de la Faja Transportadora',
          tipo: TipoComponenteDinamico.estadoFaja,
          datos: {'en_marcha': enMarcha, 'arduino': arduino},
        ),
      );
    } else if (pLower.contains('reporte') || pLower.contains('ejecutivo')) {
      widget.onNuevoComponenteSolicitado?.call(
        ComponenteDinamicoData(
          id: 'rep_${DateTime.now().millisecondsSinceEpoch}',
          titulo: 'Reporte Ejecutivo Generativo',
          tipo: TipoComponenteDinamico.reporteMarkdown,
          datos: {'reporte': respuesta},
        ),
      );
    }
  }

  int? _extraerInt(String texto, String patron) {
    final match = RegExp(patron).firstMatch(texto);
    if (match != null && match.groupCount >= 1) {
      return int.tryParse(match.group(1)!);
    }
    return null;
  }

  double? _extraerDouble(String texto, String patron) {
    final match = RegExp(patron).firstMatch(texto);
    if (match != null && match.groupCount >= 1) {
      return double.tryParse(match.group(1)!);
    }
    return null;
  }

  void _limpiarHistorial() async {
    await ChatHistoryService.borrarHistorial(_username);
    setState(() {
      _mensajes.clear();
      _mensajes.add(MensajeHistorial(
        id: 'init_reset',
        texto: "🧹 **Historial Reiniciado:** Puedes continuar conversando.",
        esUsuario: false,
        fecha: DateTime.now(),
      ));
    });
  }

  void _scrollHaciaAbajo() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.75,
      decoration: const BoxDecoration(
        color: Color(0xFF1E293B),
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          // Header de la Burbuja con Historial de Usuario
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              color: Color(0xFF0F172A),
              borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: const BoxDecoration(color: Colors.cyan, shape: BoxShape.circle),
                  child: const Icon(Icons.smart_toy_rounded, color: Colors.black, size: 20),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("ASISTENTE VIRTUAL IA", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13)),
                      Text("👤 $_nombreUsuario ($rolLabel) - Historial Activo", style: const TextStyle(color: Colors.grey, fontSize: 10)),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.delete_outline_rounded, color: Colors.amberAccent, size: 20),
                  onPressed: _limpiarHistorial,
                  tooltip: 'Borrar historial de chat',
                ),
                IconButton(
                  icon: const Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),

          // Chips de Solicitud de Componentes Dinámicos
          Container(
            height: 42,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            color: const Color(0xFF1A2234),
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                ActionChip(
                  avatar: const Icon(Icons.inventory_2, size: 14, color: Colors.cyanAccent),
                  label: const Text('🍾 Botellas Escaneadas', style: TextStyle(color: Colors.white, fontSize: 10)),
                  backgroundColor: const Color(0xFF334155),
                  onPressed: () => _enviarMensaje("Muestra las botellas escaneadas"),
                ),
                const SizedBox(width: 6),
                ActionChip(
                  avatar: const Icon(Icons.bar_chart, size: 14, color: Colors.orangeAccent),
                  label: const Text('📊 Gráfico Mermas', style: TextStyle(color: Colors.white, fontSize: 10)),
                  backgroundColor: const Color(0xFF334155),
                  onPressed: () => _enviarMensaje("Genera el gráfico de mermas por estación"),
                ),
                const SizedBox(width: 6),
                ActionChip(
                  avatar: const Icon(Icons.pie_chart, size: 14, color: Colors.greenAccent),
                  label: const Text('📈 Rendimiento Yield', style: TextStyle(color: Colors.white, fontSize: 10)),
                  backgroundColor: const Color(0xFF334155),
                  onPressed: () => _enviarMensaje("Muestra el gráfico de rendimiento yield"),
                ),
                const SizedBox(width: 6),
                ActionChip(
                  avatar: const Icon(Icons.speed, size: 14, color: Colors.redAccent),
                  label: const Text('⚙️ Estado de Faja', style: TextStyle(color: Colors.white, fontSize: 10)),
                  backgroundColor: const Color(0xFF334155),
                  onPressed: () => _enviarMensaje("Muestra el estado de la faja"),
                ),
              ],
            ),
          ),

          // Lista de Mensajes del Historial del Usuario
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(12),
              itemCount: _mensajes.length,
              itemBuilder: (context, index) {
                final m = _mensajes[index];
                return Align(
                  alignment: m.esUsuario ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 4),
                    padding: const EdgeInsets.all(12),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.8),
                    decoration: BoxDecoration(
                      color: m.esUsuario ? Colors.cyan.shade700 : const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: MarkdownBody(
                      data: m.texto,
                      styleSheet: MarkdownStyleSheet(
                        p: const TextStyle(color: Colors.white, fontSize: 13),
                        strong: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                );
              },
            ),
          ),

          if (_estaCargando)
            const LinearProgressIndicator(backgroundColor: Color(0xFF1E293B), color: Colors.cyan),

          // Entrada inferior
          Container(
            padding: const EdgeInsets.all(8),
            color: const Color(0xFF0F172A),
            child: SafeArea(
              child: Row(
                children: [
                  IconButton(
                    icon: Icon(_escuchandoVoz ? Icons.mic : Icons.mic_none, color: _escuchandoVoz ? Colors.redAccent : Colors.cyan),
                    onPressed: _escucharVoz,
                  ),
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                      decoration: InputDecoration(
                        hintText: "Escribe tu consulta o comando...",
                        hintStyle: TextStyle(color: Colors.grey.shade500, fontSize: 12),
                        filled: true,
                        fillColor: const Color(0xFF1E293B),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(20), borderSide: BorderSide.none),
                      ),
                      onSubmitted: (_) => _enviarMensaje(),
                    ),
                  ),
                  const SizedBox(width: 6),
                  CircleAvatar(
                    backgroundColor: Colors.cyan,
                    radius: 20,
                    child: IconButton(
                      icon: const Icon(Icons.send, color: Colors.black, size: 18),
                      onPressed: () => _enviarMensaje(),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

extension StringExtension on String {
  String get lowerCase => toLowerCase();
}
