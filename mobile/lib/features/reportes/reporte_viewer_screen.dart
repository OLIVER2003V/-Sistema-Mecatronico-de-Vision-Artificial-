import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_tts/flutter_tts.dart';
import '../../core/auth_service.dart';
import '../../core/ia_service.dart';

class ReporteViewerScreen extends StatefulWidget {
  final UsuarioSesion? usuarioSesion;

  const ReporteViewerScreen({Key? key, this.usuarioSesion}) : super(key: key);

  @override
  _ReporteViewerScreenState createState() => _ReporteViewerScreenState();
}

class _ReporteViewerScreenState extends State<ReporteViewerScreen> {
  bool _estaCargando = false;
  String _reporteMarkdown = '';
  late FlutterTts _flutterTts;
  bool _leyendoVoz = false;

  String get _nombreUsuario => widget.usuarioSesion?.nombreCompleto ?? 'Supervisor';

  @override
  void initState() {
    super.initState();
    _flutterTts = FlutterTts();
    _initTts();
    _generarReporte();
  }

  void _initTts() async {
    await _flutterTts.setLanguage("es-ES");
    await _flutterTts.setSpeechRate(0.9);
  }

  void _generarReporte() async {
    setState(() {
      _estaCargando = true;
      _reporteMarkdown = '';
    });

    final reporte = await IAService.solicitarReporteGenerativo(
      tipo: 'turno',
      usuario: _nombreUsuario,
    );

    if (mounted) {
      setState(() {
        _estaCargando = false;
        _reporteMarkdown = reporte;
      });
    }
  }

  void _toggleLecturaVoz() async {
    if (_leyendoVoz) {
      await _flutterTts.stop();
      setState(() => _leyendoVoz = false);
    } else {
      String limpio = _reporteMarkdown.replaceAll(RegExp(r'[*#_`]'), '');
      setState(() => _leyendoVoz = true);
      await _flutterTts.speak(limpio);
      _flutterTts.setCompletionHandler(() {
        if (mounted) setState(() => _leyendoVoz = false);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text("Reporte Ejecutivo Generativo", style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        actions: [
          IconButton(
            icon: Icon(_leyendoVoz ? Icons.volume_up_rounded : Icons.volume_mute_rounded, color: Colors.cyanAccent),
            tooltip: 'Lectura por Voz',
            onPressed: _reporteMarkdown.isEmpty ? null : _toggleLecturaVoz,
          ),
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.amberAccent),
            tooltip: 'Regenerar Reporte',
            onPressed: _generarReporte,
          ),
        ],
      ),
      body: _estaCargando
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: const [
                  CircularProgressIndicator(color: Colors.cyanAccent),
                  SizedBox(height: 16),
                  Text("Generando Reporte con Gemini AI...", style: TextStyle(color: Colors.white, fontSize: 13)),
                ],
              ),
            )
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.white.withOpacity(0.1)),
                ),
                child: MarkdownBody(
                  data: _reporteMarkdown,
                  styleSheet: MarkdownStyleSheet(
                    h1: const TextStyle(color: Colors.cyanAccent, fontSize: 20, fontWeight: FontWeight.bold),
                    h2: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
                    p: const TextStyle(color: Colors.white70, fontSize: 14, height: 1.5),
                    strong: const TextStyle(color: Colors.amberAccent, fontWeight: FontWeight.bold),
                    listBullet: const TextStyle(color: Colors.cyanAccent),
                  ),
                ),
              ),
            ),
    );
  }
}
