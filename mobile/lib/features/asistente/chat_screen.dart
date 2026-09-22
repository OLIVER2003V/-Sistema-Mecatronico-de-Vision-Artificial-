import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import '../../core/ia_service.dart';
import '../../core/auth_service.dart';
import '../../core/reporte_exporter.dart';
import '../auth/login_screen.dart';
import '../reportes/reporte_viewer_screen.dart';

class MensajeChat {
  final String texto;
  final bool esUsuario;
  final DateTime fecha;

  MensajeChat({
    required this.texto,
    required this.esUsuario,
    DateTime? fecha,
  }) : fecha = fecha ?? DateTime.now();
}

class ChatAsistenteScreen extends StatefulWidget {
  final UsuarioSesion? usuarioSesion;

  const ChatAsistenteScreen({Key? key, this.usuarioSesion}) : super(key: key);

  @override
  _ChatAsistenteScreenState createState() => _ChatAsistenteScreenState();
}

class _ChatAsistenteScreenState extends State<ChatAsistenteScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<MensajeChat> _mensajes = [];

  bool _estaCargando = false;
  bool _escuchandoVoz = false;
  late stt.SpeechToText _speech;
  late FlutterTts _flutterTts;

  String get _nombreUsuario => widget.usuarioSesion?.nombreCompleto ?? 'Operador Móvil';
  String get _rolUsuario => widget.usuarioSesion?.rol ?? 'OPERADOR';

  @override
  void initState() {
    super.initState();
    _speech = stt.SpeechToText();
    _flutterTts = FlutterTts();
    _initTts();

    // Mensaje inicial personalizado por usuario y rol
    final rolTexto = widget.usuarioSesion?.esSupervisor == true ? 'Supervisor de Calidad' : 'Operador de Planta';
    _mensajes.add(MensajeChat(
      texto: "👋 ¡Hola **$_nombreUsuario**! Sesión iniciada como **$rolTexto**.\n\nSoy el **Asistente Virtual Generativo de SORT-MATIC**. Puedes preguntarme sobre el estado de la faja, solicitar reportes de mermas o enviarme instrucciones por voz.",
      esUsuario: false,
    ));
  }

  void _initTts() async {
    await _flutterTts.setLanguage("es-ES");
    await _flutterTts.setSpeechRate(0.9);
  }

  void _hablar(String texto) async {
    String limpio = texto.replaceAll(RegExp(r'[*#_`]'), '');
    await _flutterTts.speak(limpio);
  }

  void _escucharVoz() async {
    if (!_escuchandoVoz) {
      bool disponible = await _speech.initialize(
        onStatus: (val) => print('Voz Status: $val'),
        onError: (val) => print('Voz Error: $val'),
      );

      if (disponible) {
        setState(() => _escuchandoVoz = true);
        _speech.listen(
          onResult: (val) {
            setState(() {
              _textController.text = val.recognizedWords;
            });
          },
          localeId: 'es_ES',
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
    setState(() {
      _mensajes.add(MensajeChat(texto: texto, esUsuario: true));
      _estaCargando = true;
    });
    _scrollHaciaAbajo();

    // Consulta al Microservicio de IA pasando el nombre y rol del usuario logueado
    final res = await IAService.enviarPregunta(
      pregunta: texto,
      usuario: _nombreUsuario,
      rol: _rolUsuario,
    );
    final respuestaTexto = res['respuesta'] ?? 'Sin respuesta';

    setState(() {
      _estaCargando = false;
      _mensajes.add(MensajeChat(texto: respuestaTexto, esUsuario: false));
    });
    _scrollHaciaAbajo();

    // Leer respuesta en voz alta
    _hablar(respuestaTexto);
  }

  void _pedirReporteGenerativo() async {
    setState(() {
      _estaCargando = true;
      _mensajes.add(MensajeChat(texto: "📊 *Solicitando Reporte Ejecutivo de Mermas...*", esUsuario: true));
    });
    _scrollHaciaAbajo();

    final reporte = await IAService.solicitarReporteGenerativo(
      tipo: 'turno',
      usuario: _nombreUsuario,
    );

    setState(() {
      _estaCargando = false;
      _mensajes.add(MensajeChat(texto: reporte, esUsuario: false));
    });
    _scrollHaciaAbajo();
  }

  void _cerrarSesion() async {
    await AuthService.cerrarSesion();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (context) => const LoginScreen()),
    );
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
    final esSupervisor = widget.usuarioSesion?.esSupervisor ?? false;

    return Scaffold(
      backgroundColor: const Color(0xFF12141C),
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "SORT-MATIC Assistant",
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            Text(
              "👤 $_nombreUsuario ($_rolUsuario)",
              style: const TextStyle(fontSize: 11, color: Colors.cyanAccent),
            ),
          ],
        ),
        backgroundColor: const Color(0xFF1E2230),
        elevation: 4,
        actions: [
          IconButton(
            icon: const Icon(Icons.description_rounded, color: Colors.amberAccent),
            tooltip: 'Generar Reporte Ejecutivo',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => ReporteViewerScreen(usuarioSesion: widget.usuarioSesion),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.file_download_outlined, color: Colors.cyanAccent),
            tooltip: 'Exportar PDF / Excel',
            onPressed: () {
              final ultimoReporte = _mensajes.lastWhere(
                (m) => !m.esUsuario && (m.texto.contains('#') || m.texto.contains('Reporte') || m.texto.length > 100),
                orElse: () => MensajeChat(texto: "Reporte de Mermas y Calidad SORT-MATIC\nEstado del sistema operativo e indicadores de producción.", esUsuario: false),
              );
              ReporteExporter.mostrarOpcionesExportacion(
                context: context,
                contenidoMarkdown: ultimoReporte.texto,
                usuario: _nombreUsuario,
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Colors.redAccent),
            tooltip: 'Cerrar Sesión',
            onPressed: _cerrarSesion,
          ),
        ],
      ),
      body: Column(
        children: [
          // Barra superior de estado en vivo
          Container(
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
            color: const Color(0xFF1A1D2B),
            child: Row(
              children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: const BoxDecoration(color: Colors.greenAccent, shape: BoxShape.circle),
                ),
                const SizedBox(width: 8),
                Text(
                  "Conectado AWS | Rol: $_rolUsuario",
                  style: const TextStyle(color: Colors.grey, fontSize: 11),
                ),
                const Spacer(),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.redAccent,
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  ),
                  icon: const Icon(Icons.stop, size: 16),
                  label: const Text("Parar Faja", style: TextStyle(fontSize: 12)),
                  onPressed: () => _enviarMensaje("Parar la faja de emergencia"),
                ),
              ],
            ),
          ),

          // Chips de sugerencias siempre disponibles para todos los usuarios
          Container(
            height: 42,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                ActionChip(
                  avatar: const Icon(Icons.speed, size: 16, color: Colors.cyan),
                  label: const Text('Estado Faja', style: TextStyle(color: Colors.white, fontSize: 11)),
                  backgroundColor: const Color(0xFF1E293B),
                  onPressed: () => _enviarMensaje("¿Cuál es el estado actual de la faja?"),
                ),
                const SizedBox(width: 8),
                ActionChip(
                  avatar: const Icon(Icons.pie_chart, size: 16, color: Colors.orangeAccent),
                  label: const Text('Métricas Lote', style: TextStyle(color: Colors.white, fontSize: 11)),
                  backgroundColor: const Color(0xFF1E293B),
                  onPressed: () => _enviarMensaje("Muestra las métricas del lote actual"),
                ),
                const SizedBox(width: 8),
                ActionChip(
                  avatar: const Icon(Icons.assessment, size: 16, color: Colors.greenAccent),
                  label: const Text('Generar Reporte IA', style: TextStyle(color: Colors.white, fontSize: 11)),
                  backgroundColor: const Color(0xFF1E293B),
                  onPressed: _pedirReporteGenerativo,
                ),
              ],
            ),
          ),

          // Lista de Mensajes Conversacionales
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _mensajes.length,
              itemBuilder: (context, index) {
                final m = _mensajes[index];
                final esReporteOTextoLargo = !m.esUsuario && (m.texto.contains('#') || m.texto.contains('Reporte') || m.texto.length > 150);

                return Align(
                  alignment: m.esUsuario ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    padding: const EdgeInsets.all(14),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.88),
                    decoration: BoxDecoration(
                      color: m.esUsuario ? const Color(0xFF007ACC) : const Color(0xFF252A3A),
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(16),
                        topRight: const Radius.circular(16),
                        bottomLeft: m.esUsuario ? const Radius.circular(16) : const Radius.circular(4),
                        bottomRight: m.esUsuario ? const Radius.circular(4) : const Radius.circular(16),
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.2),
                          blurRadius: 4,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        MarkdownBody(
                          data: m.texto,
                          styleSheet: MarkdownStyleSheet(
                            p: const TextStyle(color: Colors.white, fontSize: 14),
                            strong: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold),
                            h1: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                            h2: const TextStyle(color: Colors.cyanAccent, fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                        ),
                        if (esReporteOTextoLargo) ...[
                          const SizedBox(height: 12),
                          const Divider(color: Colors.white24, height: 1),
                          const SizedBox(height: 8),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              TextButton.icon(
                                style: TextButton.styleFrom(
                                  foregroundColor: Colors.redAccent,
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                ),
                                icon: const Icon(Icons.picture_as_pdf, size: 16),
                                label: const Text("PDF", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                                onPressed: () => ReporteExporter.exportarPDF(
                                  context: context,
                                  contenidoMarkdown: m.texto,
                                  usuario: _nombreUsuario,
                                ),
                              ),
                              const SizedBox(width: 4),
                              TextButton.icon(
                                style: TextButton.styleFrom(
                                  foregroundColor: Colors.greenAccent,
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                ),
                                icon: const Icon(Icons.table_chart, size: 16),
                                label: const Text("Excel", style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                                onPressed: () => ReporteExporter.exportarExcel(
                                  context: context,
                                  contenidoMarkdown: m.texto,
                                  usuario: _nombreUsuario,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
            ),
          ),

          if (_estaCargando)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: LinearProgressIndicator(backgroundColor: Color(0xFF1E2230), color: Colors.cyanAccent),
            ),

          // Barra inferior de entrada de texto y voz
          Container(
            padding: const EdgeInsets.all(12),
            color: const Color(0xFF1E2230),
            child: SafeArea(
              child: Row(
                children: [
                  IconButton(
                    icon: Icon(
                      _escuchandoVoz ? Icons.mic : Icons.mic_none,
                      color: _escuchandoVoz ? Colors.redAccent : Colors.cyanAccent,
                      size: 28,
                    ),
                    onPressed: _escucharVoz,
                    tooltip: 'Dictado por Voz',
                  ),
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      style: const TextStyle(color: Colors.white),
                      decoration: InputDecoration(
                        hintText: _escuchandoVoz ? "Escuchando voz..." : "Escribe una consulta o comando...",
                        hintStyle: TextStyle(color: Colors.grey.shade500, fontSize: 13),
                        filled: true,
                        fillColor: const Color(0xFF12141C),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none,
                        ),
                      ),
                      onSubmitted: (_) => _enviarMensaje(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  CircleAvatar(
                    backgroundColor: Colors.cyanAccent,
                    child: IconButton(
                      icon: const Icon(Icons.send, color: Colors.black),
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
