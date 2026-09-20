import 'package:flutter/material.dart';
import '../../core/auth_service.dart';
import '../asistente/chat_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController _usernameController = TextEditingController();
  final TextEditingController _passwordController = TextEditingController();

  String _rolSeleccionado = 'OPERADOR';
  bool _estaCargando = false;
  bool _ocultarPassword = true;
  String? _mensajeError;

  void _iniciarSesion({String? usuarioDirecto, String? passwordDirecto, String? rolDirecto}) async {
    final username = usuarioDirecto ?? _usernameController.text.trim();
    final password = passwordDirecto ?? _passwordController.text.trim();
    final rol = rolDirecto ?? _rolSeleccionado;

    setState(() {
      _estaCargando = true;
      _mensajeError = null;
    });

    final res = await AuthService.iniciarSesion(
      username: username,
      password: password,
      rolSeleccionado: rol,
    );

    setState(() {
      _estaCargando = false;
    });

    if (!mounted) return;

    if (res['exito'] == true) {
      final UsuarioSesion sesion = res['usuario'];
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (context) => ChatAsistenteScreen(usuarioSesion: sesion),
        ),
      );
    } else {
      setState(() {
        _mensajeError = res['mensaje'] ?? 'Error de inicio de sesión.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Logo & Encabezado Principal
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: LinearGradient(
                      colors: [Colors.cyan.shade400, Colors.blue.shade700],
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.cyan.withOpacity(0.4),
                        blurRadius: 20,
                        spreadRadius: 2,
                      )
                    ],
                  ),
                  child: const Icon(
                    Icons.precision_manufacturing_rounded,
                    size: 48,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  "SORT-MATIC",
                  style: TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 2.0,
                    color: Colors.white,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  "Portal de Control Móvil & Asistente IA",
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.cyan.shade300,
                  ),
                ),
                const SizedBox(height: 32),

                // Card de Inicio de Sesión
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.white.withOpacity(0.1)),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.3),
                        blurRadius: 15,
                        offset: const Offset(0, 8),
                      )
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const Text(
                        "Seleccionar Rol de Planta:",
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 10),

                      // Botones de Selector de Rol
                      Row(
                        children: [
                          Expanded(
                            child: GestureDetector(
                              onTap: () {
                                setState(() {
                                  _rolSeleccionado = 'OPERADOR';
                                  if (_usernameController.text.isEmpty) {
                                    _usernameController.text = 'operador';
                                  }
                                });
                              },
                              child: AnimatedContainer(
                                duration: const Duration(milliseconds: 200),
                                padding: const EdgeInsets.symmetric(vertical: 12),
                                decoration: BoxDecoration(
                                  color: _rolSeleccionado == 'OPERADOR'
                                      ? Colors.cyan.shade600
                                      : const Color(0xFF334155),
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(
                                    color: _rolSeleccionado == 'OPERADOR'
                                        ? Colors.cyan.shade300
                                        : Colors.transparent,
                                  ),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: const [
                                    Icon(Icons.engineering_rounded, size: 18, color: Colors.white),
                                    SizedBox(width: 8),
                                    Text(
                                      "OPERADOR",
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: GestureDetector(
                              onTap: () {
                                setState(() {
                                  _rolSeleccionado = 'SUPERVISOR';
                                  if (_usernameController.text.isEmpty) {
                                    _usernameController.text = 'supervisor';
                                  }
                                });
                              },
                              child: AnimatedContainer(
                                duration: const Duration(milliseconds: 200),
                                padding: const EdgeInsets.symmetric(vertical: 12),
                                decoration: BoxDecoration(
                                  color: _rolSeleccionado == 'SUPERVISOR'
                                      ? Colors.blue.shade600
                                      : const Color(0xFF334155),
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(
                                    color: _rolSeleccionado == 'SUPERVISOR'
                                        ? Colors.blue.shade300
                                        : Colors.transparent,
                                  ),
                                ),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: const [
                                    Icon(Icons.supervisor_account_rounded, size: 18, color: Colors.white),
                                    SizedBox(width: 8),
                                    Text(
                                      "SUPERVISOR",
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 20),

                      // Campo de Usuario
                      TextField(
                        controller: _usernameController,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          labelText: 'Nombre de usuario',
                          labelStyle: TextStyle(color: Colors.grey.shade400),
                          prefixIcon: const Icon(Icons.person_outline_rounded, color: Colors.cyan),
                          filled: true,
                          fillColor: const Color(0xFF0F172A),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide.none,
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Campo de Contraseña
                      TextField(
                        controller: _passwordController,
                        obscureText: _ocultarPassword,
                        style: const TextStyle(color: Colors.white),
                        decoration: InputDecoration(
                          labelText: 'Contraseña',
                          labelStyle: TextStyle(color: Colors.grey.shade400),
                          prefixIcon: const Icon(Icons.lock_outline_rounded, color: Colors.cyan),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _ocultarPassword ? Icons.visibility_off : Icons.visibility,
                              color: Colors.grey.shade400,
                            ),
                            onPressed: () {
                              setState(() {
                                _ocultarPassword = !_ocultarPassword;
                              });
                            },
                          ),
                          filled: true,
                          fillColor: const Color(0xFF0F172A),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                            borderSide: BorderSide.none,
                          ),
                        ),
                      ),

                      if (_mensajeError != null) ...[
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.red.shade900.withOpacity(0.3),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.red.shade400),
                          ),
                          child: Text(
                            "⚠️ $_mensajeError",
                            style: const TextStyle(color: Colors.white, fontSize: 12),
                          ),
                        ),
                      ],

                      const SizedBox(height: 24),

                      // Botón de Inicio de Sesión
                      ElevatedButton(
                        onPressed: _estaCargando ? null : () => _iniciarSesion(),
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          backgroundColor: Colors.cyan.shade600,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: _estaCargando
                            ? const SizedBox(
                                height: 20,
                                width: 20,
                                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                              )
                            : Text(
                                "INGRESAR COMO $_rolSeleccionado",
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.bold,
                                  letterSpacing: 1.1,
                                  color: Colors.white,
                                ),
                              ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 28),

                // Accesos Rápidos de Prueba en Planta
                const Text(
                  "ACCESOS RÁPIDOS DE PRUEBA EN PLANTA:",
                  style: TextStyle(color: Colors.white54, fontSize: 11, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _iniciarSesion(
                          usuarioDirecto: 'operador',
                          passwordDirecto: 'MiClaveSegura123',
                          rolDirecto: 'OPERADOR',
                        ),
                        icon: const Icon(Icons.flash_on_rounded, size: 16, color: Colors.cyan),
                        label: const Text("Operador (Omar)", style: TextStyle(color: Colors.white, fontSize: 11)),
                        style: OutlinedButton.styleFrom(
                          side: BorderSide(color: Colors.cyan.shade700),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: () => _iniciarSesion(
                          usuarioDirecto: 'supervisor',
                          passwordDirecto: 'MiClaveSegura123',
                          rolDirecto: 'SUPERVISOR',
                        ),
                        icon: const Icon(Icons.analytics_rounded, size: 16, color: Colors.blue),
                        label: const Text("Supervisor (Sergio)", style: TextStyle(color: Colors.white, fontSize: 11)),
                        style: OutlinedButton.styleFrom(
                          side: BorderSide(color: Colors.blue.shade700),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
