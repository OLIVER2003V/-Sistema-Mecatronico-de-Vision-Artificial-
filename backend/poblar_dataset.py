# -*- coding: utf-8 -*-
"""
Script para poblar la base de datos con un dataset realista de 1 año de producción.

Genera:
- Lotes de producción secuenciales (LOTE-EMBOL-0001, 0002, ...)
- Inspecciones con distribución industrial real (~93.5% Aceptadas, ~3.2% Llenado bajo, ~1.8% Sin Tapa, ~1.0% Sin Etiqueta, ~0.5% Otros).
- Timestamps 100% únicos por cada botella registrada (sin duplicados en la hora/segundo exacto).
- Registros FotoDescarte asociados a las mermas/rechazos compatibles con S3 y almacenamiento local.
"""
import os
import sys
import random
from datetime import datetime, timedelta, time
from django.utils import timezone

# Configurar entorno de Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sortmatic.settings")

import django
django.setup()

from django.db import transaction
from linea.models import LoteProduccion, Inspeccion, FotoDescarte

# ==============================================================================
# LISTAS DE IMÁGENES / URLs DE EJEMPLO POR TIPO DE DEFECTO
# Puedes colocar aquí tus rutas locales o enlaces públicos de AWS S3:
# Ejemplos de S3:
#   "https://mi-bucket-s3.s3.amazonaws.com/mermas/sin_tapa_01.jpg"
# Ejemplos de rutas locales:
#   "descartes/sin_tapa_01.jpg"
# ==============================================================================
URLS_SIN_TAPA = [
    "https://sortmatic-mermas-fotos.s3.us-east-1.amazonaws.com/descartes/2026/09/21/3194c848a1074299ad14e13a8fa3dba5.jpg","https://sortmatic-mermas-fotos.s3.us-east-1.amazonaws.com/descartes/2026/09/21/a22d072cd0fb46afa307344f12c03e36.jpg",
]

URLS_SIN_ETIQUETA = [
    "https://sortmatic-mermas-fotos.s3.us-east-1.amazonaws.com/descartes/2026/09/21/05d46bf31ecd45ffb885a04b3cc2c2dd.jpg","https://sortmatic-mermas-fotos.s3.us-east-1.amazonaws.com/descartes/2026/09/21/b88b7b940ad141abafbc2efcb049536e.jpg",
]

URLS_LLENADO_BAJO = [
    "https://sortmatic-mermas-fotos.s3.us-east-1.amazonaws.com/descartes/2026/09/21/5ab463996c0f44d9bcbe657fd6414783.jpg","https://sortmatic-mermas-fotos.s3.us-east-1.amazonaws.com/descartes/2026/09/21/870a7b695fb54779bdab1976f6125314.jpg",
]

def generar_dataset():
    print("[INFO] Iniciando generacion de dataset de 1 ano de produccion...")

    # Desactivar auto_now_add temporalmente para permitir timestamps historicos en bulk_create
    Inspeccion._meta.get_field('fecha_hora').auto_now_add = False
    FotoDescarte._meta.get_field('creada_en').auto_now_add = False

    # Limpiar cualquier lote o inspección de prueba previo si se requiere
    FotoDescarte.objects.all().delete()
    Inspeccion.objects.all().delete()
    LoteProduccion.objects.all().delete()

    lote_num = 1

    # Rango de tiempo: desde hace 365 días hasta hoy
    ahora = timezone.now()
    hace_un_ano = ahora - timedelta(days=365)
    fecha_iter = hace_un_ano.date()
    fecha_fin_total = ahora.date()

    inspecciones_a_crear = []
    lotes_creados = 0
    total_botellas = 0

    # Definir 2 turnos de producción por día laboral (Lunes a Viernes)
    # Turno Mañana: 08:00 - 13:00
    # Turno Tarde: 14:00 - 19:00
    horarios_turnos = [
        (time(8, 0, 0), time(13, 0, 0)),
        (time(14, 0, 0), time(19, 0, 0)),
    ]

    print("[INFO] Generando lotes e inspecciones temporales...")

    while fecha_iter <= fecha_fin_total:
        # Trabajar de Lunes (0) a Viernes (4)
        if fecha_iter.weekday() < 5:
            for idx_turno, (hora_inicio, hora_fin) in enumerate(horarios_turnos):
                dt_inicio = timezone.make_aware(datetime.combine(fecha_iter, hora_inicio))
                dt_fin = timezone.make_aware(datetime.combine(fecha_iter, hora_fin))

                if dt_inicio > ahora:
                    continue

                # Capacidad del lote (entre 60 y 110 botellas por lote/turno)
                cant_botellas = random.randint(60, 110)
                correlativo = f"LOTE-EMBOL-{lote_num:04d}"

                es_ultimo_lote = (fecha_iter == fecha_fin_total and idx_turno == len(horarios_turnos) - 1)
                estado = LoteProduccion.ACTIVO if es_ultimo_lote else LoteProduccion.FINALIZADO

                # Si es el lote ACTIVO actual, fijar su fecha_inicio para que refleje una cadencia real de ~30-40 BPM
                if es_ultimo_lote:
                    dt_inicio = ahora - timedelta(seconds=cant_botellas * 2)

                lote = LoteProduccion.objects.create(
                    correlativo=correlativo,
                    numero=lote_num,
                    capacidad_lote=cant_botellas,
                    estado=estado,
                    fecha_inicio=dt_inicio,
                    fecha_fin=dt_fin if estado == LoteProduccion.FINALIZADO else None
                )
                lotes_creados += 1
                lote_num += 1

                # Seleccionar un perfil de falla para el lote (para alternar entre problemas de etiquetadora y tapadora)
                perfil_lote = random.choice(["ETIQUETA", "TAPA", "MIXTO"])

                # Generar botellas del lote con timestamps únicos y crecientes
                tiempo_actual = dt_inicio
                lote_primera_fecha = None
                lote_ultima_fecha = None

                for i in range(cant_botellas):
                    # Avanzar el tiempo entre 1.5 y 3.5 segundos + microsegundos aleatorios para asegurar unicidad absoluta
                    incremento_seg = random.uniform(1.5, 3.5)
                    incremento_microseg = random.randint(1000, 990000)
                    tiempo_actual += timedelta(seconds=incremento_seg, microseconds=incremento_microseg)

                    if i == 0:
                        lote_primera_fecha = tiempo_actual
                    lote_ultima_fecha = tiempo_actual

                    prob = random.random()

                    if prob < 0.930:
                        # 93.0% ACEPTADA
                        resultado = Inspeccion.ACEPTADA
                        tipo_defecto = None
                        llenado = round(random.uniform(88.0, 98.5), 1)
                        confianza = round(random.uniform(91.0, 99.8), 1)
                        estacion = None
                    elif prob < 0.960:
                        # 3.0% LLENADO BAJO
                        resultado = Inspeccion.LLENADO_BAJO
                        tipo_defecto = None
                        llenado = round(random.uniform(20.0, 58.5), 1)
                        confianza = round(random.uniform(85.0, 98.0), 1)
                        estacion = Inspeccion.ESTACION_2
                    else:
                        # 4.0% DEFECTUOSA FISICA (Distribución según perfil de lote)
                        resultado = Inspeccion.DEFECTUOSA
                        estacion = Inspeccion.ESTACION_1
                        sub_prob = random.random()

                        if perfil_lote == "ETIQUETA":
                            if sub_prob < 0.75:
                                tipo_defecto = Inspeccion.SIN_ETIQUETA
                            else:
                                tipo_defecto = Inspeccion.SIN_TAPA
                        elif perfil_lote == "TAPA":
                            if sub_prob < 0.75:
                                tipo_defecto = Inspeccion.SIN_TAPA
                            else:
                                tipo_defecto = Inspeccion.SIN_ETIQUETA
                        else:  # MIXTO
                            if sub_prob < 0.50:
                                tipo_defecto = Inspeccion.SIN_ETIQUETA
                            else:
                                tipo_defecto = Inspeccion.SIN_TAPA

                        llenado = round(random.uniform(80.0, 97.0), 1)
                        confianza = round(random.uniform(85.0, 99.0), 1)

                    insp = Inspeccion(
                        lote=lote,
                        resultado=resultado,
                        tipo_defecto=tipo_defecto,
                        nivel_llenado_detectado=llenado,
                        confianza_ia=confianza,
                        estacion_descarte=estacion,
                        fecha_hora=tiempo_actual
                    )
                    inspecciones_a_crear.append(insp)
                    total_botellas += 1

                # Actualizar las fechas de inicio y fin del lote al rango real procesado
                if lote_primera_fecha and lote_ultima_fecha:
                    lote.fecha_inicio = lote_primera_fecha
                    if estado == LoteProduccion.FINALIZADO:
                        lote.fecha_fin = lote_ultima_fecha
                    lote.save(update_fields=["fecha_inicio", "fecha_fin"])

        fecha_iter += timedelta(days=1)

    print(f"[INFO] Guardando {total_botellas} inspecciones en la base de datos...")
    with transaction.atomic():
        Inspeccion.objects.bulk_create(inspecciones_a_crear, batch_size=2000)

    print("[INFO] Creando registros de FotoDescarte para inspecciones rechazadas...")
    rechazadas = Inspeccion.objects.filter(resultado__in=[Inspeccion.DEFECTUOSA, Inspeccion.LLENADO_BAJO])
    
    fotos_batch = []
    for insp in rechazadas:
        dt = insp.fecha_hora

        if insp.resultado == Inspeccion.LLENADO_BAJO:
            plantilla = random.choice(URLS_LLENADO_BAJO) if URLS_LLENADO_BAJO else "llenado_bajo_01.jpg"
        elif insp.tipo_defecto == Inspeccion.SIN_TAPA:
            plantilla = random.choice(URLS_SIN_TAPA) if URLS_SIN_TAPA else "sin_tapa_01.jpg"
        else:
            plantilla = random.choice(URLS_SIN_ETIQUETA) if URLS_SIN_ETIQUETA else "sin_etiqueta_01.jpg"

        # Estructurar dinámicamente con la carpeta por fecha descartes/YYYY/MM/DD/filename
        from urllib.parse import urlparse
        from pathlib import Path

        if plantilla.startswith("http://") or plantilla.startswith("https://"):
            path_foto = plantilla
        else:
            from pathlib import Path
            filename = Path(plantilla).name
            path_foto = f"descartes/{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/{filename}"

        fotos_batch.append(FotoDescarte(inspeccion=insp, imagen=path_foto, creada_en=dt))

    with transaction.atomic():
        FotoDescarte.objects.bulk_create(fotos_batch, batch_size=2000)

    print("[EXITO] Dataset generado con exito!")
    print(f"Metricas del Dataset:")
    print(f"  * Total Lotes Creados: {lotes_creados}")
    print(f"  * Total Botellas Inspeccionadas: {total_botellas}")
    print(f"  * Total Mermas / Fotos de Descarte: {len(fotos_batch)}")

if __name__ == "__main__":
    generar_dataset()
