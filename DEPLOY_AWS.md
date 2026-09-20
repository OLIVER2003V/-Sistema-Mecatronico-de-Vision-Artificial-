# Guía Completa de Despliegue en la Nube AWS (EC2 + S3 + Docker)

Esta guía explica paso a paso cómo desplegar el proyecto **SORT-MATIC** en la nube de **Amazon Web Services (AWS)** utilizando Docker para alojar el Frontend, Backend, Redis y PostgreSQL en una instancia **EC2**, manteniendo las fotografías de descarte en **Amazon S3**.

---

## 🏗️ Arquitectura General

* **Instancia EC2 (Ubuntu 24.04 LTS):** Aloja los 4 contenedores de Docker (`frontend`, `backend`, `db` PostgreSQL y `redis`).
* **Amazon S3:** Almacena de forma persistente las fotografías de mermas y descartes capturadas por la cámara.
* **PC de Planta / Local (Visión + Arduino):** Ejecuta `inspector_botellas.py` localmente y transmite los eventos hacia la IP/Dominio de la EC2 en AWS.

---

## 📋 Paso 1: Crear la Instancia EC2 en AWS

1. Entra a la consola de AWS y ve al servicio **EC2** > **Launch Instance (Lanzar Instancia)**.
2. Configura los datos de la instancia:
   * **Nombre:** `SORT-MATIC-Server`
   * **Imagen (AMI):** Ubuntu Server 24.04 LTS (64-bit).
   * **Tipo de instancia:** `t2.micro` o `t3.micro` (Elegible para la capa gratuita / Free Tier).
   * **Par de claves (Key pair):** Crea o selecciona tu llave SSH (`sortmatic-key.pem`) para conectarte a la VM.
3. **Configuración de Red / Grupo de Seguridad (Security Group):**
   Crea un nuevo Grupo de Seguridad con las siguientes reglas de entrada (Inbound Rules):

   | Tipo | Protocolo | Puerto | Origen | Descripción |
   | :--- | :--- | :--- | :--- | :--- |
   | **SSH** | TCP | 22 | Mi IP (o Cualquier lugar `0.0.0.0/0`) | Acceso por terminal |
   | **HTTP** | TCP | 80 | Cualquier lugar (`0.0.0.0/0`) | Acceso al Dashboard Web |
   | **Custom TCP** | TCP | 8000 | Cualquier lugar (`0.0.0.0/0`) | API REST y WebSockets |
   | **HTTPS** | TCP | 443 | Cualquier lugar (`0.0.0.0/0`) | Tráfico cifrado SSL (Opcional) |

4. En **Almacenamiento (EBS)**: Selecciona al menos **20 GB** de disco (General Purpose SSD gp3).
5. Haz clic en **Launch Instance**.

---

## 🪣 Paso 2: Configuración de Amazon S3 e IAM (Estándar de Seguridad AWS)

Para cumplir con los más altos estándares de seguridad en la nube (AWS Well-Architected Framework), utilizaremos **IAM Roles con el Principio de Mínimo Privilegio (Least Privilege)**:
* **Cero claves en código:** No usaremos `AWS_ACCESS_KEY_ID` ni `AWS_SECRET_ACCESS_KEY` en ningún archivo.
* **Permisos acotados:** La EC2 solo tendrá acceso al bucket específico del proyecto.

### 1. Crear el Bucket en Amazon S3
1. En la consola de AWS, ve a **S3** > **Create Bucket**.
2. **Nombre del Bucket:** `sortmatic-mermas-fotos` (o el nombre único que elijas).
3. **Región:** `us-east-1` (misma región de tu EC2).
4. Deja activado "Block *all* public access" (el acceso seguro será gestionado por el Backend con firmas temporales o URLs firmadas).

### 2. Crear la Política de Seguridad IAM (Mínimo Privilegio)
1. En la consola de AWS, ve a **IAM** > **Policies** > **Create Policy**.
2. Selecciona la pestaña **JSON** y pega la siguiente política estrictamente delimitada:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PermisoSortmaticS3",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::sortmatic-mermas-fotos",
                "arn:aws:s3:::sortmatic-mermas-fotos/*"
            ]
        }
    ]
}
```
3. Nombra la política `SortmaticS3Policy` y guarda.

### 3. Crear el Rol de IAM y asignarlo a la EC2
1. En **IAM** > **Roles** > **Create Role**.
2. Selecciona **AWS service** -> Caso de uso: **EC2**.
3. En la búsqueda de políticas, selecciona `SortmaticS3Policy`.
4. Nombra el rol `SortmaticEC2Role` y haz clic en **Create Role**.
5. Ve a tu instancia en **EC2** > Selecciona tu VM > **Acciones** > **Seguridad** > **Modificar rol IAM**.
6. Elige `SortmaticEC2Role` y guarda.

> ✅ **Resultado:** Tu servidor EC2 ahora tiene acceso seguro a S3 mediante tokens temporales que AWS rota automáticamente cada pocas horas.



---

## 🖥️ Paso 3: Instalar Docker en la Instancia EC2

Conéctate a tu EC2 por SSH desde tu terminal local (PowerShell / Git Bash):

```bash
ssh -i "sortmatic-key.pem" ubuntu@IP_PUBLICA_DE_TU_EC2
```

Dentro del servidor Ubuntu, instala Docker y Docker Compose ejecutando:

```bash
# Actualizar sistema e instalar dependencias
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ca-certificates

# Instalar Docker oficial
sudo curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Instalar Docker Compose V2
sudo apt install -y docker-compose-v2

# Reiniciar sesión para aplicar permisos de docker
exit
```

Vuelve a conectarte por SSH para verificar la instalación:

```bash
docker --version
docker compose version
```

---

## 🚀 Paso 4: Clonar el Repositorio y Configurar `.env`

En la terminal de la EC2:

```bash
# 1. Clonar el código del proyecto
git clone https://github.com/TU_USUARIO/TU_REPOSICION.git project
cd project

# 2. Crear el archivo de entorno desde la plantilla de producción
cp .env.production.example .env

# 3. Editar el archivo .env con tus claves
nano .env
```

En el editor `nano`:
* Ajusta `POSTGRES_PASSWORD` a una contraseña segura.
* Ajusta `VISION_API_KEY` a la clave secreta que usará tu módulo de visión en planta.
* Reemplaza `DJANGO_ALLOWED_HOSTS=*` o coloca la IP pública de tu EC2.
* Para guardar en `nano`: Presiona `Ctrl + O`, luego `Enter`, y sal con `Ctrl + X`.

---

## ⚙️ Paso 5: Desplegar los Contenedores en AWS

Ejecuta el siguiente comando para compilar e iniciar los contenedores en segundo plano:

```bash
docker compose up -d --build
```

Verifica que los 4 contenedores estén corriendo correctamente:

```bash
docker compose ps
```

Deberías ver:
* `project-db-1` (PostgreSQL) - Healthy
* `project-redis-1` (Redis) - Healthy
* `project-backend-1` (Django/Daphne) - Running
* `project-frontend-1` (Nginx/React) - Running

---

## 🔑 Paso 6: Inicializar la Base de Datos en AWS

Ejecuta el comando para crear los usuarios y roles iniciales dentro de la base de datos PostgreSQL de Docker:

```bash
docker compose exec backend python manage.py crear_usuarios_iniciales --password "Embol2026Faja"
```

---

## 🖥️ Paso 7: Conectar el Módulo de Visión de Planta a AWS

Ahora que el servidor está en la Nube de AWS, configura tu PC local de la planta para enviar la telemetría a la IP de la EC2:

En tu PC de la planta (local), edita `vision/config.json` o establece las variables de entorno en PowerShell:

### Opción A (Mediante variables de entorno sin modificar archivos):
```powershell
$env:SORTMATIC_API_KEY = "ClaveVisionSeguraProducion2026_AWS_EMBOL!"
cd vision
.\.venv\Scripts\python.exe inspector_botellas.py --puerto COM3
```

### Opción B (Editando `vision/config.json`):
En la sección `"backend"` de `vision/config.json`:
```json
"backend": {
  "url": "http://IP_PUBLICA_DE_TU_EC2:8000/api/telemetria/",
  "api_key": "ClaveVisionSeguraProducion2026_AWS_EMBOL!",
  ...
}
```

---

## 🔒 Paso 8: Configurar Dominio Gratuito (DuckDNS) y SSL/TLS (Certbot Let's Encrypt)

Para tener tu dominio propio con candado de seguridad HTTPS (🔒) de forma **100% gratuita y automática**, sigue estos pasos:

### 1. Registrar tu Dominio en DuckDNS
1. Ve a [duckdns.org](https://www.duckdns.org/) e inicia sesión (Google, GitHub, etc.).
2. En la sección **sub-domain**, elige un nombre para tu proyecto (ejemplo: `sortmatic-botellas`).
3. En el campo **IP**, coloca la IP pública de tu EC2 (`54.225.179.205`).
4. Haz clic en **add domain**. Tu dominio será: `sortmatic-botellas.duckdns.org`.

### 2. Instalar Nginx Host y Certbot en tu EC2
En la terminal SSH de tu EC2:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
```

### 3. Crear el Proxy Inverso en Nginx
Crea el archivo de configuración en Nginx:

```bash
sudo nano /etc/nginx/sites-available/sortmatic
```

Pega el siguiente contenido (reemplazando `sortmatic-botellas.duckdns.org` por tu subdominio):

```nginx
server {
    server_name sortmatic-botellas.duckdns.org;
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activa el sitio y recarga Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/sortmatic /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Obtener el Certificado SSL Gratuito (HTTPS 🔒)
Ejecuta Certbot:

```bash
sudo certbot --nginx -d sortmatic-botellas.duckdns.org
```
* Ingresa tu correo electrónico cuando lo solicite y acepta los términos (`Y`).
* Certbot configurará el certificado SSL/TLS de forma automática y renovará el candado cada 90 días automáticamente.

### 5. Activar HTTPS en tu `.env`
Edita el archivo `.env` en tu EC2:

```bash
nano .env
```

Ajusta estas líneas:
```env
DJANGO_DEBUG=false
DJANGO_FORZAR_HTTPS=true
DJANGO_ALLOWED_HOSTS=sortmatic-botellas.duckdns.org,54.225.179.205
```

Reinicia el backend:
```bash
docker compose restart backend
```

¡Listo! Ya puedes entrar a **`https://sortmatic-botellas.duckdns.org`** con conexión cifrada TLS y candado verde 🔒.


