# Correr SORT-MATIC sin Docker

Para probar el dashboard sin instalar Docker Desktop, Postgres ni Redis:
SQLite en vez de Postgres, y el channel layer en memoria en vez de Redis.
Sirve para probar en una sola PC; para produccion o varios workers, usar
Docker (ver el `docker-compose.yml` de la raiz).

## 1. Backend (PowerShell)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt

$env:DJANGO_DB_ENGINE = "sqlite"
$env:DJANGO_CHANNEL_LAYER = "memory"
.venv\Scripts\python.exe manage.py migrate

# Una cuenta por cada rol. Sin --password se generan claves aleatorias y se
# imprimen UNA sola vez.
.venv\Scripts\python.exe manage.py crear_usuarios_iniciales --password "Embol2026Faja"

.venv\Scripts\python.exe -m daphne -b 127.0.0.1 -p 8000 sortmatic.asgi:application
```

Deja esa ventana abierta (queda sirviendo en `http://127.0.0.1:8000`). Las
variables `$env:...` solo valen para esa ventana de PowerShell: si la cerras,
hay que volver a ponerlas antes de correr `daphne` de nuevo (el `migrate` y el
`crear_usuarios_iniciales` NO hace falta repetirlos).

Quedan tres cuentas, una por rol:

| Usuario      | Rol                       | Que ve                                                   |
|--------------|---------------------------|----------------------------------------------------------|
| `admin`      | Administrador de sistemas | Usuarios, bitacora y todo lo demas                       |
| `supervisor` | Supervisor de calidad     | Analiticos, lotes, parametros de inspeccion, mermas      |
| `operador`   | Operador de planta        | Contadores en vivo y marcha/paro de la faja              |

## 2. Frontend (otra ventana de PowerShell)

```powershell
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173` y entra con una de esas cuentas. En dev,
`vite.config.js` manda `/api`, `/ws` y `/media` al backend en el puerto 8000.

## 3. Vision (opcional, otra ventana)

Solo si queres ver datos reales en el dashboard. La clave del dispositivo por
defecto de `vision/config.json` coincide con la del backend en desarrollo, asi
que no hay nada que configurar:

```powershell
cd vision
python inspector_botellas.py --sin-arduino    # ESPACIO simula una botella
```

## Pruebas

```powershell
cd backend
.venv\Scripts\python.exe manage.py test tests --settings=sortmatic.settings_test

cd ..\vision
python -m unittest discover -s tests -t .
```

Las del backend usan SQLite en memoria y un channel layer en memoria (no
necesitan que nada este levantado). Las de vision corren aunque no esten
instalados opencv ni numpy.

## Para volver a Docker despues

No hace falta deshacer nada: si no seteas `DJANGO_DB_ENGINE` /
`DJANGO_CHANNEL_LAYER`, `settings.py` usa Postgres + Redis por defecto (el
comportamiento de `docker-compose.yml`). `backend/db.sqlite3` y `.venv/` estan
en `.gitignore` y no afectan al build de Docker.
