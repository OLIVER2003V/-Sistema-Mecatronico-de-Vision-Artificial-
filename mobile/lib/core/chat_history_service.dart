import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class MensajeHistorial {
  final String id;
  final String texto;
  final bool esUsuario;
  final DateTime fecha;
  final List<Map<String, dynamic>>? widgets;
  final String? accionCanvas;

  MensajeHistorial({
    required this.id,
    required this.texto,
    required this.esUsuario,
    required this.fecha,
    this.widgets,
    this.accionCanvas,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'texto': texto,
        'esUsuario': esUsuario,
        'fecha': fecha.toIso8601String(),
        'widgets': widgets,
        'accionCanvas': accionCanvas,
      };

  factory MensajeHistorial.fromJson(Map<String, dynamic> json) => MensajeHistorial(
        id: json['id'] ?? DateTime.now().millisecondsSinceEpoch.toString(),
        texto: json['texto'] ?? '',
        esUsuario: json['esUsuario'] ?? false,
        fecha: json['fecha'] != null ? DateTime.parse(json['fecha']) : DateTime.now(),
        widgets: json['widgets'] != null ? List<Map<String, dynamic>>.from(json['widgets'].map((x) => Map<String, dynamic>.from(x))) : null,
        accionCanvas: json['accionCanvas'],
      );
}

class ChatHistoryService {
  static const _storage = FlutterSecureStorage();

  static String _claveUsuario(String username) => 'chat_history_$username';

  /// Carga el historial de conversación guardado para un usuario específico
  static Future<List<MensajeHistorial>> cargarHistorial(String username) async {
    try {
      final jsonStr = await _storage.read(key: _claveUsuario(username));
      if (jsonStr == null || jsonStr.isEmpty) return [];

      final List<dynamic> list = jsonDecode(jsonStr);
      return list.map((item) => MensajeHistorial.fromJson(item)).toList();
    } catch (e) {
      print("Error cargando historial de $username: $e");
      return [];
    }
  }

  /// Guarda la lista completa de mensajes del usuario
  static Future<void> guardarHistorial(String username, List<MensajeHistorial> mensajes) async {
    try {
      final List<Map<String, dynamic>> jsonList = mensajes.map((m) => m.toJson()).toList();
      await _storage.write(key: _claveUsuario(username), value: jsonEncode(jsonList));
    } catch (e) {
      print("Error guardando historial de $username: $e");
    }
  }

  /// Agrega un nuevo mensaje al historial persistente
  static Future<void> agregarMensaje(String username, MensajeHistorial mensaje) async {
    final historial = await cargarHistorial(username);
    historial.add(mensaje);
    await guardarHistorial(username, historial);
  }

  /// Limpia el historial del usuario
  static Future<void> borrarHistorial(String username) async {
    await _storage.delete(key: _claveUsuario(username));
  }
}
