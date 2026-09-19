# -*- coding: utf-8 -*-
"""
Pruebas unitarias y de integracion del backend SORT-MATIC.

Viven fuera de las apps (`cuentas/`, `linea/`) a proposito: asi se leen como
la especificacion ejecutable del sistema y no se mezclan con el codigo que
verifican.

    cd backend
    python manage.py test tests --settings=sortmatic.settings_test

Ese settings usa SQLite en memoria y un channel layer en memoria: no hace
falta Docker, Postgres ni Redis.
"""
