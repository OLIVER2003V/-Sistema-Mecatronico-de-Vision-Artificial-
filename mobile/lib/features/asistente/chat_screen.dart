import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';
import '../../core/ia_service.dart';

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
  const ChatAsistenteScreen({Key? key}) : super(key: key);

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

  @override
  void initState() {
    super.initState();
    _speech = stt.SpeechToText();
    _flutterTts = FlutterTts();
    _initTts();

    // Mensaje inicial de bienvenida
    _mensajes.add(MensajeChat(
      texto: "👋 ¡Hola! Soy el **Asistente Virtual Generativo de SORT-MATIC**.\n\nPuedes preguntarme sobre el estado de la faja, solicitar un reporte de mermas o dictarme instrucciones por voz.",
      esUsuario: false,
    ));
  }

  void _initTts() async {
    await _flutterTts.setLanguage("es-ES");
    await _flutterTts.setSpeechRate(0.9);
  }

  void _hablar(String texto) async {
    // Limpiar sintaxis de markdown básica para lectura por voz fluida
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

    // Consulta al Microservicio de IA
    final res = await IAService.enviarPregunta(pregunta: texto);
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
      _mensajes.add(MensajeChat(texto: "📊 *Generando Reporte Ejecutivo...*", esUsuario: true));
    });
    _scrollHaciaAbajo();

    final reporte = await IAService.solicitarReporteGenerativo(tipo: 'turno');

    setState(() {
      _estaCargando = false;
      _mensajes.add(MensajeChat(texto: reporte, esUsuario: false));
    });
    _scrollHaciaAbajo();
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
    return Scaffold(
      backgroundColor: const Color(0xFF12141C),
      appBar: AppBar(
        title: const Text("Asistente Virtual SORT-MATIC", style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: const Color(0xFF1E2230),
        elevation: 4,
        actions: [
          IconButton(
            icon: const Icon(Icons.picture_as_pdf, color: Colors.cyanAccent),
            tooltip: 'Generar Reporte',
            onPressed: _pedirReporteGenerativo,
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
                const Text("Conectado a AWS Cloud", style: TextStyle(color: Colors.grey, fontSize: 12)),
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

          // Lista de Mensajes Conversacionales
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _mensajes.length,
              itemBuilder: (context, index) {
                final m = _mensajes[index];
                return Align(
                  alignment: m.esUsuario ? Alignment.centerRight : Alignment.centerLeft,
                  child: Container(
                    margin: const EdgeInsets.symmetric(vertical: 6),
                    padding: const EdgeInsets.all(14),
                    constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.85),
                    decoration: BoxDecoration(
                      color: m.esUsuario ? const Color(0xFF2B5278) : const Color(0xFF1E2230),
                      borderRadius: BorderRadius.only(
                        topLeft: const Radius.circular(16),
                        topRight: const Radius.circular(16),
                        bottomLeft: m.esUsuario ? const Radius.circular(16) : Radius.zero,
                        bottomRight: m.esUsuario ? Radius.zero : const Radius.circular(16),
                      ),
                      border: m.esUsuario ? null : Border.all(color: Colors.white10),
                    ),
                    child: m.esUsuario
                        ? Text(m.texto, style: const TextStyle(color: Colors.white, fontSize: 15))
                        : MarkdownBody(
                            data: m.texto,
                            styleSheet: MarkdownStyleSheet(
                              p: const TextStyle(color: Colors.white70, fontSize: 14),
                              h1: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold),
                              h2: const TextStyle(color: Colors.cyan, fontWeight: FontWeight.bold),
                              code: const TextStyle(backgroundColor: Colors.black45, color: Colors.amberAccent),
                            ),
                          ),
                  ),
                );
              },
            ),
          ),

          if (_estaCargando)
            const Padding(
              padding: EdgeInsets.all(8.0),
              child: CircularProgressIndicator(color: Colors.cyanAccent),
            ),

          // Barra Inferior de Entrada (Texto y Micrófono)
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
                    ),
                    onPressed: _escucharVoz,
                  ),
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      style: const TextStyle(color: Colors.white),
                      decoration: const InputDecoration(
                        hintText: "Pregunta o dicta un comando...",
                        hintStyle: TextStyle(color: Colors.grey),
                        border: InputBorder.none,
                      ),
                      onSubmitted: (_) => _enviarMensaje(),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send, color: Colors.cyanAccent),
                    onPressed: () => _enviarMensaje(),
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
