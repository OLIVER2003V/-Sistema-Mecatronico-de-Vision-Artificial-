import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

class IAService {
  // Servidor por defecto en la nube AWS
  static const String baseUrl = 'https://sortmatic-botellas.duckdns.org/ia';
  static const String wsUrl = 'wss://sortmatic-botellas.duckdns.org/ia/ws/chat';

  /// Envía una pregunta conversacional al microservicio de IA de forma síncrona
  static Future<Map<String, dynamic>> enviarPregunta({
    required String pregunta,
    String usuario = 'Operador Móvil',
    String rol = 'OPERADOR',
    String? conversacionId,
    List<Map<String, dynamic>>? historial,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/chat'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'pregunta': pregunta,
          'usuario': usuario,
          'rol': rol,
          'conversacion_id': conversacionId,
          'historial': historial,
        }),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        return {
          'respuesta': '⚠️ Error de servidor (${response.statusCode}): No se pudo procesar la consulta de IA.',
          'accion_canvas': 'reemplazar',
          'widgets': [],
        };
      }
    } catch (e) {
      return {
        'respuesta': '⚠️ Error de conexión con el Microservicio de IA ($e).',
        'accion_canvas': 'reemplazar',
        'widgets': [],
      };
    }
  }

  /// Solicita la generación de un reporte ejecutivo en formato Markdown
  static Future<String> solicitarReporteGenerativo({String tipo = 'turno', String usuario = 'Supervisor'}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/reporte'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'tipo': tipo,
          'usuario': usuario,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['reporte_markdown'] ?? 'No se generó reporte.';
      } else {
        return 'Error al obtener reporte (${response.statusCode}).';
      }
    } catch (e) {
      return 'Error de red al conectar con el microservicio de IA: $e';
    }
  }

  /// Conecta con el WebSocket del microservicio para respuestas en vivo por streaming
  static WebSocketChannel conectarWebSocketStreaming() {
    return WebSocketChannel.connect(Uri.parse(wsUrl));
  }
}
