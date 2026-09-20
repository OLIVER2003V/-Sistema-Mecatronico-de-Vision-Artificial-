import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class UsuarioSesion {
  final String username;
  final String nombreCompleto;
  final String rol; // 'OPERADOR', 'SUPERVISOR', 'ADMINISTRADOR'
  final String? tokenAcceso;

  UsuarioSesion({
    required this.username,
    required this.nombreCompleto,
    required this.rol,
    this.tokenAcceso,
  });

  bool get esSupervisor => rol == 'SUPERVISOR' || rol == 'ADMINISTRADOR';
}

class AuthService {
  static const String backendAuthUrl = 'https://sortmatic-botellas.duckdns.org/api/auth/login/';
  static const _storage = FlutterSecureStorage();

  /// Realiza el inicio de sesión contra el Backend Django en AWS EC2.
  /// Soporta también un modo de demostración rápido offline si no hay red.
  static Future<Map<String, dynamic>> iniciarSesion({
    required String username,
    required String password,
    String? rolSeleccionado,
  }) async {
    try {
      final response = await http.post(
        Uri.parse(backendAuthUrl),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username.trim(),
          'password': password.trim(),
        }),
      ).timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final userObj = data['usuario'] ?? {};
        final String rol = data['rol'] ?? userObj['rol'] ?? rolSeleccionado ?? 'OPERADOR';
        final String access = data['access'] ?? '';
        final String nombre = "${userObj['first_name'] ?? ''} ${userObj['last_name'] ?? ''}".trim();

        final sesion = UsuarioSesion(
          username: username,
          nombreCompleto: nombre.isNotEmpty ? nombre : username,
          rol: rol,
          tokenAcceso: access,
        );

        await _guardarSesion(sesion);
        return {'exito': true, 'usuario': sesion};
      } else {
        final errData = jsonDecode(response.body);
        String msg = errData['detail'] ?? errData['detalle'] ?? 'Credenciales inválidas.';
        return {'exito': false, 'mensaje': msg};
      }
    } catch (e) {
      // Si la conexión falla (offline o sin backend), se concede acceso rápido en modo demo
      final rol = rolSeleccionado ?? (username.toLowerCase().contains('super') ? 'SUPERVISOR' : 'OPERADOR');
      final sesionDemo = UsuarioSesion(
        username: username.isEmpty ? (rol == 'SUPERVISOR' ? 'supervisor' : 'operador') : username,
        nombreCompleto: username.isEmpty ? (rol == 'SUPERVISOR' ? 'Sergio (Supervisor)' : 'Omar (Operador)') : username,
        rol: rol,
      );

      await _guardarSesion(sesionDemo);
      return {
        'exito': true,
        'usuario': sesionDemo,
        'modoDemo': true,
      };
    }
  }

  static Future<void> _guardarSesion(UsuarioSesion sesion) async {
    await _storage.write(key: 'username', value: sesion.username);
    await _storage.write(key: 'nombreCompleto', value: sesion.nombreCompleto);
    await _storage.write(key: 'rol', value: sesion.rol);
    if (sesion.tokenAcceso != null) {
      await _storage.write(key: 'tokenAcceso', value: sesion.tokenAcceso);
    }
  }

  static Future<UsuarioSesion?> obtenerSesionActual() async {
    final username = await _storage.read(key: 'username');
    final nombreCompleto = await _storage.read(key: 'nombreCompleto');
    final rol = await _storage.read(key: 'rol');

    if (username != null && rol != null) {
      return UsuarioSesion(
        username: username,
        nombreCompleto: nombreCompleto ?? username,
        rol: rol,
      );
    }
    return null;
  }

  static Future<void> cerrarSesion() async {
    await _storage.deleteAll();
  }
}
