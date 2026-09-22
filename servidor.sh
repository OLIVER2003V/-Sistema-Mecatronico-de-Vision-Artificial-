#!/bin/bash
# ============================================================
# SORT-MATIC · Manual de Usuario — Servidor local
# Ejecutar desde la RAÍZ del proyecto:
#   bash docs/servidor.sh
# ============================================================

DOCS_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=8899

echo ""
echo "  ┌─────────────────────────────────────────┐"
echo "  │   SORT-MATIC · Manual de Usuario        │"
echo "  │   Servidor local en puerto $PORT          │"
echo "  └─────────────────────────────────────────┘"
echo ""
echo "  🌐 Abra en el navegador:"
echo "     http://localhost:$PORT"
echo ""
echo "  Presione Ctrl+C para detener."
echo ""

# Matar proceso anterior en el mismo puerto si existe
fuser -k ${PORT}/tcp 2>/dev/null

cd "$DOCS_DIR"
python3 -m http.server $PORT
