import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

class ReporteExporter {
  /// Exporta el contenido Markdown del Reporte de IA a formato PDF estilizado profesionalmente
  static Future<void> exportarPDF({
    required BuildContext context,
    required String contenidoMarkdown,
    String titulo = "Reporte Ejecutivo de Producción y Calidad",
    String usuario = "Supervisor",
  }) async {
    final pdf = pw.Document();

    final lineas = contenidoMarkdown.split('\n');

    pdf.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(32),
        header: (pw.Context context) {
          return pw.Container(
            alignment: pw.Alignment.centerRight,
            margin: const pw.EdgeInsets.only(bottom: 16.0),
            padding: const pw.EdgeInsets.only(bottom: 8.0),
            decoration: const pw.BoxDecoration(
              border: pw.Border(bottom: pw.BorderSide(width: 1.5, color: PdfColors.cyan700)),
            ),
            child: pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              children: [
                pw.Text(
                  "SORT-MATIC Industrial AI System",
                  style: pw.TextStyle(fontWeight: pw.FontWeight.bold, color: PdfColors.cyan900, fontSize: 13),
                ),
                pw.Text(
                  DateTime.now().toString().substring(0, 16),
                  style: const pw.TextStyle(color: PdfColors.grey700, fontSize: 10),
                ),
              ],
            ),
          );
        },
        footer: (pw.Context context) {
          return pw.Container(
            alignment: pw.Alignment.center,
            margin: const pw.EdgeInsets.only(top: 16.0),
            padding: const pw.EdgeInsets.only(top: 8.0),
            decoration: const pw.BoxDecoration(
              border: pw.Border(top: pw.BorderSide(width: 0.5, color: PdfColors.grey400)),
            ),
            child: pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              children: [
                pw.Text("Generado por: $usuario", style: const pw.TextStyle(fontSize: 9, color: PdfColors.grey600)),
                pw.Text("Página ${context.pageNumber} de ${context.pagesCount}", style: const pw.TextStyle(fontSize: 9, color: PdfColors.grey600)),
              ],
            ),
          );
        },
        build: (pw.Context context) => [
          pw.Container(
            padding: const pw.EdgeInsets.all(12),
            decoration: pw.BoxDecoration(
              color: PdfColors.blueGrey50,
              borderRadius: pw.BorderRadius.circular(6),
              border: pw.Border.all(color: PdfColors.cyan700, width: 1),
            ),
            child: pw.Row(
              children: [
                pw.Container(
                  width: 8,
                  height: 36,
                  color: PdfColors.cyan700,
                ),
                pw.SizedBox(width: 10),
                pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.start,
                  children: [
                    pw.Text(
                      titulo,
                      style: pw.TextStyle(fontSize: 16, fontWeight: pw.FontWeight.bold, color: PdfColors.blueGrey900),
                    ),
                    pw.SizedBox(height: 2),
                    pw.Text(
                      "Sistema de Visión Artificial y Control de Calidad | Operador: $usuario",
                      style: const pw.TextStyle(fontSize: 9, color: PdfColors.blueGrey700),
                    ),
                  ],
                ),
              ],
            ),
          ),
          pw.SizedBox(height: 16),
          ...lineas.map((linea) {
            final l = linea.trim();
            if (l.isEmpty) return pw.SizedBox(height: 6);

            if (l.startsWith('# ')) {
              return pw.Padding(
                padding: const pw.EdgeInsets.only(top: 10, bottom: 6),
                child: pw.Text(
                  l.substring(2).replaceAll('*', ''),
                  style: pw.TextStyle(fontSize: 15, fontWeight: pw.FontWeight.bold, color: PdfColors.cyan900),
                ),
              );
            }
            if (l.startsWith('## ')) {
              return pw.Padding(
                padding: const pw.EdgeInsets.only(top: 8, bottom: 4),
                child: pw.Text(
                  l.substring(3).replaceAll('*', ''),
                  style: pw.TextStyle(fontSize: 13, fontWeight: pw.FontWeight.bold, color: PdfColors.blueGrey800),
                ),
              );
            }
            if (l.startsWith('### ')) {
              return pw.Padding(
                padding: const pw.EdgeInsets.only(top: 6, bottom: 4),
                child: pw.Text(
                  l.substring(4).replaceAll('*', ''),
                  style: pw.TextStyle(fontSize: 11, fontWeight: pw.FontWeight.bold, color: PdfColors.blue800),
                ),
              );
            }
            if (l.startsWith('* ') || l.startsWith('- ')) {
              return pw.Padding(
                padding: const pw.EdgeInsets.only(left: 10, top: 2, bottom: 2),
                child: pw.Row(
                  crossAxisAlignment: pw.CrossAxisAlignment.start,
                  children: [
                    pw.Text("• ", style: pw.TextStyle(fontWeight: pw.FontWeight.bold, color: PdfColors.cyan700)),
                    pw.Expanded(
                      child: pw.Text(
                        l.substring(2).replaceAll('*', ''),
                        style: const pw.TextStyle(fontSize: 10, color: PdfColors.blueGrey900),
                      ),
                    ),
                  ],
                ),
              );
            }
            return pw.Padding(
              padding: const pw.EdgeInsets.symmetric(vertical: 2),
              child: pw.Text(
                l.replaceAll('*', ''),
                style: const pw.TextStyle(fontSize: 10, color: PdfColors.blueGrey900),
              ),
            );
          }).toList(),
        ],
      ),
    );

    final bytes = await pdf.save();
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    await Printing.sharePdf(
      bytes: bytes,
      filename: 'Reporte_IA_SORTMATIC_$timestamp.pdf',
    );
  }

  /// Exporta el contenido Markdown del Reporte de IA a formato Excel / CSV (.csv compatible con Microsoft Excel)
  static Future<void> exportarExcel({
    required BuildContext context,
    required String contenidoMarkdown,
    String titulo = "Reporte Ejecutivo de Produccion",
    String usuario = "Supervisor",
  }) async {
    final StringBuffer csvBuffer = StringBuffer();

    // Agregar marca de orden de bytes BOM para que Excel abra UTF-8 directamente sin caracteres raros
    csvBuffer.write('\uFEFF');

    csvBuffer.writeln('SORT-MATIC - REPORTE DE PRODUCCIÓN Y IA GENERATIVA');
    csvBuffer.writeln('Fecha de Generación,${DateTime.now().toString().substring(0, 19)}');
    csvBuffer.writeln('Generado Por,$usuario');
    csvBuffer.writeln('');
    csvBuffer.writeln('Sección / Categoría,Métrica / Detalle,Valor / Estado');

    final lineas = contenidoMarkdown.split('\n');
    String seccionActual = "Resumen General";

    for (var linea in lineas) {
      final l = linea.trim();
      if (l.isEmpty) continue;

      if (l.startsWith('#')) {
        seccionActual = l.replaceAll('#', '').replaceAll('*', '').trim();
        csvBuffer.writeln('"${_escaparCsv(seccionActual)}","---","---"');
      } else if (l.startsWith('*') || l.startsWith('-')) {
        final contenido = l.substring(1).replaceAll('*', '').trim();
        final partes = contenido.split(':');
        if (partes.length >= 2) {
          final clave = partes[0].trim();
          final valor = partes.sublist(1).join(':').trim();
          csvBuffer.writeln('"${_escaparCsv(seccionActual)}","${_escaparCsv(clave)}","${_escaparCsv(valor)}"');
        } else {
          csvBuffer.writeln('"${_escaparCsv(seccionActual)}","${_escaparCsv(contenido)}","OK"');
        }
      } else {
        final partes = l.split(':');
        if (partes.length >= 2) {
          final clave = partes[0].replaceAll('*', '').trim();
          final valor = partes.sublist(1).join(':').replaceAll('*', '').trim();
          csvBuffer.writeln('"${_escaparCsv(seccionActual)}","${_escaparCsv(clave)}","${_escaparCsv(valor)}"');
        } else {
          csvBuffer.writeln('"${_escaparCsv(seccionActual)}","${_escaparCsv(l.replaceAll('*', ''))}","Información"');
        }
      }
    }

    final bytes = utf8.encode(csvBuffer.toString());
    final timestamp = DateTime.now().millisecondsSinceEpoch;

    await Printing.sharePdf(
      bytes: bytes,
      filename: 'Reporte_IA_SORTMATIC_$timestamp.csv',
    );
  }

  static String _escaparCsv(String texto) {
    return texto.replaceAll('"', '""');
  }

  /// Muestra un menú de diálogo inferior (Modal Bottom Sheet) con opciones de exportación PDF / EXCEL
  static void mostrarOpcionesExportacion({
    required BuildContext context,
    required String contenidoMarkdown,
    String usuario = "Supervisor",
  }) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (BuildContext ctx) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade600,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(height: 16),
                const Text(
                  "Exportar Reporte Generativo IA",
                  style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  "Selecciona el formato en el que deseas guardar o compartir:",
                  style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
                ),
                const SizedBox(height: 20),
                ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.redAccent.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.picture_as_pdf, color: Colors.redAccent, size: 28),
                  ),
                  title: const Text("Exportar como PDF (.pdf)", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                  subtitle: const Text("Documento formal imprimible con encabezado y formato ejecutivo.", style: TextStyle(color: Colors.grey, fontSize: 11)),
                  onTap: () {
                    Navigator.pop(ctx);
                    exportarPDF(context: context, contenidoMarkdown: contenidoMarkdown, usuario: usuario);
                  },
                ),
                const Divider(color: Colors.white12),
                ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.greenAccent.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.table_chart, color: Colors.greenAccent, size: 28),
                  ),
                  title: const Text("Exportar como EXCEL (.csv / .xlsx)", style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                  subtitle: const Text("Hoja de cálculo con tablas de métricas y datos estructurados.", style: TextStyle(color: Colors.grey, fontSize: 11)),
                  onTap: () {
                    Navigator.pop(ctx);
                    exportarExcel(context: context, contenidoMarkdown: contenidoMarkdown, usuario: usuario);
                  },
                ),
                const SizedBox(height: 12),
              ],
            ),
          ),
        );
      },
    );
  }
}
