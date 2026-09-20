import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

enum TipoComponenteDinamico {
  kpiCard,
  graficoBarras,
  graficoPie,
  tablaDatos,
  alertaStatus,
  metricaConteo,
  graficoBarrasMermas,
  graficoDonutYield,
  estadoFaja,
  reporteMarkdown,
}

class ComponenteDinamicoData {
  final String id;
  final String titulo;
  final TipoComponenteDinamico tipo;
  final Map<String, dynamic> datos;
  final DateTime creadoEn;

  ComponenteDinamicoData({
    required this.id,
    required this.titulo,
    required this.tipo,
    required this.datos,
    DateTime? creadoEn,
  }) : creadoEn = creadoEn ?? DateTime.now();

  factory ComponenteDinamicoData.fromJson(Map<String, dynamic> json) {
    final tipoStr = (json['tipo'] ?? '').toString();
    TipoComponenteDinamico tipo;
    switch (tipoStr) {
      case 'kpi_card':
        tipo = TipoComponenteDinamico.kpiCard;
        break;
      case 'grafico_barras':
        tipo = TipoComponenteDinamico.graficoBarras;
        break;
      case 'grafico_pie':
        tipo = TipoComponenteDinamico.graficoPie;
        break;
      case 'tabla_datos':
        tipo = TipoComponenteDinamico.tablaDatos;
        break;
      case 'alerta_status':
        tipo = TipoComponenteDinamico.alertaStatus;
        break;
      case 'estado_faja':
        tipo = TipoComponenteDinamico.estadoFaja;
        break;
      case 'reporte_markdown':
        tipo = TipoComponenteDinamico.reporteMarkdown;
        break;
      default:
        tipo = TipoComponenteDinamico.metricaConteo;
    }

    return ComponenteDinamicoData(
      id: json['id'] ?? 'widget_${DateTime.now().microsecondsSinceEpoch}',
      titulo: (json['titulo'] ?? json['title'] ?? 'COMPONENTE DINÁMICO').toString(),
      tipo: tipo,
      datos: Map<String, dynamic>.from(json),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'titulo': titulo,
      'tipo': tipo.name,
      'datos': datos,
      'creadoEn': creadoEn.toIso8601String(),
    };
  }
}

class ComponenteDinamicoWidget extends StatelessWidget {
  final ComponenteDinamicoData data;
  final VoidCallback onEliminar;
  final Function(String comando)? onEjecutarComando;

  const ComponenteDinamicoWidget({
    Key? key,
    required this.data,
    required this.onEliminar,
    this.onEjecutarComando,
  }) : super(key: key);

  static double _toDouble(dynamic valor) => double.tryParse(valor?.toString() ?? '0') ?? 0.0;
  static int _toInt(dynamic valor) => int.tryParse(valor?.toString() ?? '0') ?? 0;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.cyan.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.3),
            blurRadius: 10,
            offset: const Offset(0, 4),
          )
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header de la tarjeta
          Row(
            children: [
              _obtenerIconoTipo(data.tipo),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  data.titulo.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 13,
                    letterSpacing: 1.1,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close_rounded, color: Colors.grey, size: 20),
                onPressed: onEliminar,
                tooltip: 'Quitar del tapiz',
              ),
            ],
          ),
          const Divider(color: Colors.white12, height: 16),

          // Cuerpo según el tipo
          _buildCuerpoComponente(context),
        ],
      ),
    );
  }

  Widget _obtenerIconoTipo(TipoComponenteDinamico tipo) {
    switch (tipo) {
      case TipoComponenteDinamico.kpiCard:
        return const Icon(Icons.analytics_rounded, color: Colors.cyanAccent, size: 20);
      case TipoComponenteDinamico.graficoBarras:
      case TipoComponenteDinamico.graficoBarrasMermas:
        return const Icon(Icons.bar_chart_rounded, color: Colors.orangeAccent, size: 20);
      case TipoComponenteDinamico.graficoPie:
      case TipoComponenteDinamico.graficoDonutYield:
        return const Icon(Icons.pie_chart_rounded, color: Colors.greenAccent, size: 20);
      case TipoComponenteDinamico.tablaDatos:
        return const Icon(Icons.table_chart_rounded, color: Colors.blueAccent, size: 20);
      case TipoComponenteDinamico.alertaStatus:
        return const Icon(Icons.warning_amber_rounded, color: Colors.amberAccent, size: 20);
      case TipoComponenteDinamico.estadoFaja:
        return const Icon(Icons.speed_rounded, color: Colors.redAccent, size: 20);
      case TipoComponenteDinamico.reporteMarkdown:
      default:
        return const Icon(Icons.description_rounded, color: Colors.amberAccent, size: 20);
    }
  }

  Widget _buildCuerpoComponente(BuildContext context) {
    switch (data.tipo) {
      case TipoComponenteDinamico.kpiCard:
        final valorNum = _toDouble(data.datos['valor']);
        final valStr = data.datos['valor']?.toString() ?? '$valorNum';
        final subtitulo = data.datos['subtitulo']?.toString() ?? '';
        final colorStr = data.datos['color']?.toString() ?? 'cyan';
        Color col = _parseColor(colorStr);

        return Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(valStr, style: TextStyle(color: col, fontSize: 26, fontWeight: FontWeight.bold)),
                if (subtitulo.isNotEmpty)
                  Text(subtitulo, style: const TextStyle(color: Colors.grey, fontSize: 11)),
              ],
            ),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: col.withOpacity(0.15), shape: BoxShape.circle),
              child: Icon(Icons.trending_up_rounded, color: col, size: 24),
            ),
          ],
        );

      case TipoComponenteDinamico.graficoBarras:
        final List rawDatos = data.datos['datos'] is List ? data.datos['datos'] : [];
        if (rawDatos.isEmpty) {
          return const Text("Sin datos de gráfico", style: TextStyle(color: Colors.grey));
        }

        List<BarChartGroupData> rodGroups = [];
        List<String> leyendas = [];
        for (int i = 0; i < rawDatos.length; i++) {
          final item = rawDatos[i];
          final val = _toDouble(item['valor']);
          final et = item['etiqueta']?.toString() ?? 'E$i';
          leyendas.add(et);
          rodGroups.add(
            BarChartGroupData(
              x: i,
              barRods: [
                BarChartRodData(
                  toY: val,
                  color: _obtenerColorPalette(i),
                  width: 18,
                  borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                )
              ],
            ),
          );
        }

        return Column(
          children: [
            SizedBox(
              height: 160,
              child: BarChart(
                BarChartData(
                  borderData: FlBorderData(show: false),
                  titlesData: FlTitlesData(
                    show: true,
                    topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          int idx = value.toInt();
                          if (idx >= 0 && idx < leyendas.length) {
                            return Padding(
                              padding: const EdgeInsets.only(top: 4.0),
                              child: Text(
                                leyendas[idx],
                                style: const TextStyle(color: Colors.white70, fontSize: 10),
                              ),
                            );
                          }
                          return const SizedBox();
                        },
                      ),
                    ),
                  ),
                  barGroups: rodGroups,
                ),
              ),
            ),
          ],
        );

      case TipoComponenteDinamico.graficoPie:
        final List rawDatos = data.datos['datos'] is List ? data.datos['datos'] : [];
        if (rawDatos.isEmpty) {
          return const Text("Sin datos de pastel", style: TextStyle(color: Colors.grey));
        }

        List<PieChartSectionData> secciones = [];
        for (int i = 0; i < rawDatos.length; i++) {
          final item = rawDatos[i];
          final val = _toDouble(item['valor']);
          final et = item['etiqueta']?.toString() ?? '';
          final colStr = item['color']?.toString() ?? '';
          Color col = colStr.isNotEmpty ? _parseColor(colStr) : _obtenerColorPalette(i);

          secciones.add(
            PieChartSectionData(
              color: col,
              value: val > 0 ? val : 1.0,
              title: et.isNotEmpty ? '$et\n${val.toStringAsFixed(0)}' : '${val.toStringAsFixed(0)}',
              radius: 36,
              titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.black87),
            ),
          );
        }

        return SizedBox(
          height: 160,
          child: PieChart(
            PieChartData(
              sectionsSpace: 3,
              centerSpaceRadius: 28,
              sections: secciones,
            ),
          ),
        );

      case TipoComponenteDinamico.tablaDatos:
        final List colsRaw = data.datos['columnas'] is List ? data.datos['columnas'] : [];
        final List filasRaw = data.datos['filas'] is List ? data.datos['filas'] : [];

        if (colsRaw.isEmpty || filasRaw.isEmpty) {
          return const Text("Tabla vacía", style: TextStyle(color: Colors.grey));
        }

        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            headingRowHeight: 36,
            dataRowHeight: 36,
            horizontalMargin: 8,
            columnSpacing: 16,
            columns: colsRaw.map((c) => DataColumn(label: Text(c.toString(), style: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold, fontSize: 11)))).toList(),
            rows: filasRaw.map((f) {
              final List cel = f is List ? f : [f.toString()];
              return DataRow(
                cells: cel.map((cell) => DataCell(Text(cell.toString(), style: const TextStyle(color: Colors.white70, fontSize: 11)))).toList(),
              );
            }).toList(),
          ),
        );

      case TipoComponenteDinamico.alertaStatus:
        final msg = data.datos['mensaje']?.toString() ?? '';
        final nivel = data.datos['nivel']?.toString() ?? 'info';
        Color bgCol = Colors.blueAccent;
        IconData ico = Icons.info_outline;

        if (nivel == 'exito' || nivel == 'success') {
          bgCol = Colors.green;
          ico = Icons.check_circle_outline;
        } else if (nivel == 'advertencia' || nivel == 'warning') {
          bgCol = Colors.orangeAccent;
          ico = Icons.warning_amber_rounded;
        } else if (nivel == 'peligro' || nivel == 'error') {
          bgCol = Colors.redAccent;
          ico = Icons.error_outline;
        }

        return Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: bgCol.withOpacity(0.15), borderRadius: BorderRadius.circular(10), border: Border.all(color: bgCol.withOpacity(0.4))),
          child: Row(
            children: [
              Icon(ico, color: bgCol, size: 24),
              const SizedBox(width: 10),
              Expanded(child: Text(msg, style: const TextStyle(color: Colors.white, fontSize: 12))),
            ],
          ),
        );

      case TipoComponenteDinamico.metricaConteo:
        final total = _toInt(data.datos['total']);
        final aceptadas = _toInt(data.datos['aceptadas']);
        final rechazadas = _toInt(data.datos['rechazadas']);

        return Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildSubStat("Total Botellas", "$total", Colors.cyanAccent),
            _buildSubStat("Aceptadas", "$aceptadas", Colors.greenAccent),
            _buildSubStat("Rechazadas", "$rechazadas", Colors.redAccent),
          ],
        );

      case TipoComponenteDinamico.graficoBarrasMermas:
        final sinTapa = _toDouble(data.datos['sin_tapa']);
        final sinEtiqueta = _toDouble(data.datos['sin_etiqueta']);
        final defectuosa = _toDouble(data.datos['defectuosa']);
        final llenadoBajo = _toDouble(data.datos['llenado_bajo']);

        return SizedBox(
          height: 160,
          child: BarChart(
            BarChartData(
              borderData: FlBorderData(show: false),
              titlesData: FlTitlesData(show: false),
              barGroups: [
                BarChartGroupData(x: 0, barRods: [BarChartRodData(toY: sinTapa, color: Colors.amber, width: 16)]),
                BarChartGroupData(x: 1, barRods: [BarChartRodData(toY: sinEtiqueta, color: Colors.orange, width: 16)]),
                BarChartGroupData(x: 2, barRods: [BarChartRodData(toY: defectuosa, color: Colors.redAccent, width: 16)]),
                BarChartGroupData(x: 3, barRods: [BarChartRodData(toY: llenadoBajo, color: Colors.blueAccent, width: 16)]),
              ],
            ),
          ),
        );

      case TipoComponenteDinamico.graficoDonutYield:
        final yieldRate = _toDouble(data.datos['yield_rate']);
        final rejectRate = _toDouble(data.datos['reject_rate']);

        return SizedBox(
          height: 150,
          child: PieChart(
            PieChartData(
              sectionsSpace: 2,
              centerSpaceRadius: 30,
              sections: [
                PieChartSectionData(color: Colors.greenAccent, value: yieldRate, title: '${yieldRate.toStringAsFixed(1)}%', radius: 24, titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.black)),
                PieChartSectionData(color: Colors.redAccent, value: rejectRate, title: '${rejectRate.toStringAsFixed(1)}%', radius: 24, titleStyle: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.white)),
              ],
            ),
          ),
        );

      case TipoComponenteDinamico.estadoFaja:
        final enMarcha = data.datos['en_marcha'] == true;
        final arduino = data.datos['arduino'] != false;

        return Row(
          children: [
            Icon(
              enMarcha ? Icons.play_circle_fill : Icons.stop_circle,
              color: enMarcha ? Colors.greenAccent : Colors.redAccent,
              size: 36,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(enMarcha ? "FAJA EN MARCHA" : "FAJA DETENIDA", style: TextStyle(color: enMarcha ? Colors.greenAccent : Colors.redAccent, fontWeight: FontWeight.bold)),
                  Text("Hardware Arduino: ${arduino ? 'Conectado' : 'Sin Señal'}", style: const TextStyle(color: Colors.grey, fontSize: 11)),
                ],
              ),
            ),
            ElevatedButton(
              onPressed: () => onEjecutarComando?.call(enMarcha ? 'STOP' : 'START'),
              style: ElevatedButton.styleFrom(backgroundColor: enMarcha ? Colors.redAccent : Colors.green),
              child: Text(enMarcha ? "PARAR" : "ARRANCAR", style: const TextStyle(color: Colors.white, fontSize: 11)),
            ),
          ],
        );

      case TipoComponenteDinamico.reporteMarkdown:
        final texto = data.datos['reporte']?.toString() ?? data.datos['texto']?.toString() ?? '';
        return MarkdownBody(
          data: texto,
          styleSheet: MarkdownStyleSheet(
            p: const TextStyle(color: Colors.white70, fontSize: 13),
            strong: const TextStyle(color: Colors.cyanAccent, fontWeight: FontWeight.bold),
          ),
        );
    }
  }

  Widget _buildSubStat(String titulo, String valor, Color color) {
    return Column(
      children: [
        Text(titulo, style: const TextStyle(color: Colors.grey, fontSize: 10)),
        const SizedBox(height: 4),
        Text(valor, style: TextStyle(color: color, fontSize: 20, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Color _parseColor(String c) {
    switch (c.toLowerCase()) {
      case 'cyan': return Colors.cyanAccent;
      case 'green': return Colors.greenAccent;
      case 'amber':
      case 'yellow': return Colors.amberAccent;
      case 'red': return Colors.redAccent;
      case 'blue': return Colors.blueAccent;
      case 'orange': return Colors.orangeAccent;
      case 'purple': return Colors.purpleAccent;
      default: return Colors.cyanAccent;
    }
  }

  Color _obtenerColorPalette(int i) {
    final list = [Colors.cyanAccent, Colors.greenAccent, Colors.amberAccent, Colors.redAccent, Colors.blueAccent, Colors.orangeAccent, Colors.purpleAccent];
    return list[i % list.length];
  }
}

