import 'dart:async';
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../core/auth_service.dart';
import '../../core/ia_service.dart';
import '../asistente/asistente_burbuja.dart';
import '../auth/login_screen.dart';
import '../reportes/reporte_viewer_screen.dart';

class DashboardScreen extends StatefulWidget {
  final UsuarioSesion? usuarioSesion;

  const DashboardScreen({Key? key, this.usuarioSesion}) : super(key: key);

  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  bool _estaCargando = false;
  Timer? _timerRefresco;

  // Estado de Planta en tiempo real
  bool _enMarcha = false;
  bool _arduinoConectado = true;
  int _totalInspecciones = 0;
  double _yieldRate = 95.0;
  double _rejectRate = 5.0;
  double _cadenciaBpm = 30.0;
  double _cadenciaTeorica = 30.0;

  // Conteos de defectos
  int _sinTapa = 0;
  int _sinEtiqueta = 0;
  int _defectuosas = 0;
  int _llenadoBajo = 0;

  String get _nombreUsuario => widget.usuarioSesion?.nombreCompleto ?? 'Operador';
  String get _rolUsuario => widget.usuarioSesion?.rol ?? 'OPERADOR';

  @override
  void initState() {
    super.initState();
    _cargarMetricas();
    // Refresco periódico cada 10 segundos
    _timerRefresco = Timer.periodic(const Duration(seconds: 10), (_) => _cargarMetricas());
  }

  @override
  void dispose() {
    _timerRefresco?.cancel();
    super.dispose();
  }

  Future<void> _cargarMetricas() async {
    setState(() => _estaCargando = true);
    // Petición al microservicio de IA para obtener el contexto traducido
    final res = await IAService.enviarPregunta(
      pregunta: "Dame el estado actual de los KPIs de la planta",
      usuario: _nombreUsuario,
      rol: _rolUsuario,
    );

    if (mounted) {
      setState(() {
        _estaCargando = false;
        // Si hay datos en contexto_usado o respuesta
        final ctx = res['contexto_usado'] ?? '';
        if (ctx.contains('EN MARCHA')) _enMarcha = true;
        if (ctx.contains('DETENIDA')) _enMarcha = false;
        if (ctx.contains('DESCONECTADO')) _arduinoConectado = false;
      });
    }
  }

  void _ejecutarComando(String accion) async {
    final res = await IAService.enviarPregunta(
      pregunta: "$accion la faja",
      usuario: _nombreUsuario,
      rol: _rolUsuario,
    );

    if (!mounted) return;

    final mensaje = res['respuesta'] ?? 'Comando procesado.';
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(mensaje),
        backgroundColor: accion == 'STOP' ? Colors.redAccent : Colors.green,
        duration: const Duration(seconds: 3),
      ),
    );
    _cargarMetricas();
  }

  void _abrirAsistenteBurbuja() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => AsistenteBurbujaModal(
        usuarioSesion: widget.usuarioSesion,
        onComandoEjecutado: _cargarMetricas,
      ),
    );
  }

  void _abrirReporteEjecutivo() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => ReporteViewerScreen(
          usuarioSesion: widget.usuarioSesion,
        ),
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
              "SORT-MATIC SCADA",
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
            icon: const Icon(Icons.refresh_rounded, color: Colors.cyan),
            onPressed: _cargarMetricas,
            tooltip: 'Actualizar Datos',
          ),
          IconButton(
            icon: const Icon(Icons.description_rounded, color: Colors.amberAccent),
            onPressed: _abrirReporteEjecutivo,
            tooltip: 'Reportes Ejecutivo',
          ),
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Colors.redAccent),
            onPressed: _cerrarSesion,
            tooltip: 'Cerrar Sesión',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Tarjeta de Estado de Faja & Control Hardware
            _buildTarjeaEstadoFaja(),
            const SizedBox(height: 16),

            // 2. Tarjetas de KPIs Principales
            const Text(
              "INDICADORES CLAVE DE PRODUCCIÓN (KPIs)",
              style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.1),
            ),
            const SizedBox(height: 10),
            _buildGridKPIs(),
            const SizedBox(height: 20),

            // 3. Gráficos Visuales (Bar Chart de Defectos + Donut Chart Yield)
            const Text(
              "ANÁLISIS GRÁFICO DE CALIDAD Y MERMAS",
              style: TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.1),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(child: _buildGraficoDonutRendimiento()),
                const SizedBox(width: 12),
                Expanded(child: _buildGraficoBarrasDefectos()),
              ],
            ),
            const SizedBox(height: 20),

            // 4. Banner para Generación de Reportes Ejecutivo Generativo
            _buildBannerReporteGenerativo(),
            const SizedBox(height: 80), // Espacio para el botón flotante
          ],
        ),
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

  Widget _buildTarjeaEstadoFaja() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.1)),
      ),
      child: Row(
        children: [
          // Icono Indicador
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: _enMarcha ? Colors.green.withOpacity(0.2) : Colors.red.withOpacity(0.2),
              shape: BoxShape.circle,
            ),
            child: Icon(
              _enMarcha ? Icons.play_arrow_rounded : Icons.stop_rounded,
              color: _enMarcha ? Colors.greenAccent : Colors.redAccent,
              size: 32,
            ),
          ),
          const SizedBox(width: 16),

          // Texto de Estado
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _enMarcha ? "FAJA EN MARCHA" : "FAJA DETENIDA",
                  style: TextStyle(
                    color: _enMarcha ? Colors.greenAccent : Colors.redAccent,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  "Arduino: ${_arduinoConectado ? 'Conectado OK' : 'Sin Señal'}",
                  style: const TextStyle(color: Colors.grey, fontSize: 12),
                ),
              ],
            ),
          ),

          // Botones de Comando Directo
          ElevatedButton(
            onPressed: () => _ejecutarComando(_enMarcha ? 'STOP' : 'START'),
            style: ElevatedButton.styleFrom(
              backgroundColor: _enMarcha ? Colors.redAccent : Colors.green,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            ),
            child: Text(
              _enMarcha ? "DETENER" : "ARRANCAR",
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGridKPIs() {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      crossAxisSpacing: 12,
      mainAxisSpacing: 12,
      childAspectRatio: 1.6,
      children: [
        _buildKpiCard("TOTAL BOTELLAS", "$_totalInspecciones", Icons.inventory_2_rounded, Colors.cyan),
        _buildKpiCard("APROBACIÓN (YIELD)", "$_yieldRate%", Icons.check_circle_rounded, Colors.greenAccent),
        _buildKpiCard("RECHAZOS (MERMAS)", "$_rejectRate%", Icons.warning_amber_rounded, Colors.redAccent),
        _buildKpiCard("CADENCIA (BPM)", "$_cadenciaBpm / $_cadenciaTeorica", Icons.speed_rounded, Colors.orangeAccent),
      ],
    );
  }

  Widget _buildKpiCard(String titulo, String valor, IconData icono, Color color) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icono, size: 18, color: color),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  titulo,
                  style: TextStyle(color: Colors.grey.shade400, fontSize: 10, fontWeight: FontWeight.bold),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            valor,
            style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  Widget _buildGraficoDonutRendimiento() {
    return Container(
      height: 180,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        children: [
          const Text("Aprobadas vs Mermas", style: TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          Expanded(
            child: PieChart(
              PieChartData(
                sectionsSpace: 2,
                centerSpaceRadius: 28,
                sections: [
                  PieChartSectionData(color: Colors.greenAccent, value: _yieldRate, title: '$_yieldRate%', radius: 25, titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.black)),
                  PieChartSectionData(color: Colors.redAccent, value: _rejectRate, title: '$_rejectRate%', radius: 25, titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildGraficoBarrasDefectos() {
    return Container(
      height: 180,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        children: [
          const Text("Mermas por Estación", style: TextStyle(color: Colors.white70, fontSize: 11, fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          Expanded(
            child: BarChart(
              BarChartData(
                borderData: FlBorderData(show: false),
                titlesData: FlTitlesData(show: false),
                barGroups: [
                  BarChartGroupData(x: 0, barRods: [BarChartRodData(toY: (_sinTapa + 1).toDouble(), color: Colors.amber, width: 14)]),
                  BarChartGroupData(x: 1, barRods: [BarChartRodData(toY: (_sinEtiqueta + 1).toDouble(), color: Colors.orange, width: 14)]),
                  BarChartGroupData(x: 2, barRods: [BarChartRodData(toY: (_defectuosas + 1).toDouble(), color: Colors.redAccent, width: 14)]),
                  BarChartGroupData(x: 3, barRods: [BarChartRodData(toY: (_llenadoBajo + 1).toDouble(), color: Colors.blueAccent, width: 14)]),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBannerReporteGenerativo() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [Colors.indigo.shade900, Colors.purple.shade900]),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          const Icon(Icons.analytics_rounded, color: Colors.amberAccent, size: 36),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Text("Reportes Ejecutivos IA", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                SizedBox(height: 4),
                Text("Genera un diagnóstico completo en formato Markdown", style: TextStyle(color: Colors.white70, fontSize: 11)),
              ],
            ),
          ),
          ElevatedButton(
            onPressed: _abrirReporteEjecutivo,
            style: ElevatedButton.styleFrom(backgroundColor: Colors.amberAccent),
            child: const Text("VER REPORTE", style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 11)),
          ),
        ],
      ),
    );
  }
}
