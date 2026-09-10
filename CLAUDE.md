# Faja clasificadora de botellas

Proyecto de curso. Dos partes que se hablan por el puerto serie:

- `faja_botellas/` — firmware del **Arduino UNO** (C++). Controla motor (por
  modulo rele), 2 servos y un LCD 16x2 I2C. Lee 2 sensores de barrera y 3 botones.
- `vision/` — **vision en Python**. Toma la foto, la pasa por un modelo
  **YOLO (Ultralytics, `best.pt`)** y le dice al Arduino que hacer.

## Flujo de la faja (2 estaciones, 1 camara)

1. Cinta en movimiento. El **sensor 1** detecta una botella -> la cinta para.
2. La camara clasifica UNA vez (defecto fisico / llenado bajo / OK).
3. Si hay **defecto fisico** ('D') -> el **servo 1 (pin 10)** la expulsa ahi mismo
   y la cinta sigue.
4. Si no, la botella sigue hasta el **sensor 2**.
5. Si el **llenado < 60%** ('L') -> la cinta para y el **servo 2 (pin 11)** la
   expulsa. Si esta OK ('A') pasa de largo sin detenerse.

El Arduino calcula el veredicto en la estacion 1 y lo recuerda hasta la 2
(cola de 'A'/'L'; la 'D' se expulsa antes y no entra a la cola).

## Modelo de vision

- El modelo va en **`vision/best.pt`** (o ruta en `config.json -> modelo.ruta`,
  o `--modelo RUTA`). No se versiona (pesa); esta en `.gitignore`.
- Clases del modelo: `Botella Etiqueta Tapa Agua` (deben estar) y
  `Rota Notapa` (defectos).
- El **nivel de llenado** NO es la confianza de "Agua": se estima por geometria
  (cuanto sube la caja `Agua` dentro de la caja `Botella`, ver `_nivel_llenado`).
  0 = vacia, ~1 = llena hasta el hombro.
- Regla en `vision/clasificador.py` (`conf_ok = 0.80` Etiqueta/Tapa,
  `conf_defecto = 0.50` Rota/Notapa, `nivel_min = 0.60` llenado):
  - **A** aceptada — hay Botella/Etiqueta/Tapa, sin Rota/Notapa, y llenado >= `nivel_min`.
  - **D** defectuosa — hay Rota o Notapa, o falta Botella/Etiqueta/Tapa. Servo 1 (pin 10).
  - **L** nivel de agua — lo fisico OK pero llenado < `nivel_min`. Servo 2 (pin 11).
  - **N** sin botella — el inspector lo trata como A.
- Calibrar el llenado: con `--calibrar`, una botella LLENA deberia marcar
  `nivel_llenado` ~1.0; si no, ajusta `cuello_frac`. Despues fija `nivel_min`.

## Protocolo serie (9600 baudios)

- Arduino -> PC: `B` = "hay una botella detenida frente a la camara".
- PC -> Arduino: `A` aceptada · `D` defecto fisico · `L` llenado bajo.
- Arduino -> PC: lineas que empiezan con `#` son informativas (contadores /
  avisos) y **no contienen la letra `B`**; la PC las ignora.
- **Si cambias estas letras, cambialas en los dos lados**:
  `faja_botellas/faja_botellas.ino` y `vision/clasificador.py`.

## Pines del Arduino

- Servos: **10** = servo 1 (defecto fisico, estacion 1), **11** = servo 2 (llenado, estacion 2)
- Motor por modulo rele: **9**
- Sensores de barrera: **8** = sensor 1 (camara + servo 1), **7** = sensor 2
- Botones: **3** (START), **4** (STOP), **5** (RESET)
- LCD I2C en A4/A5. **No usar 0 y 1** (puerto serie). Pin 6 libre.
- `SENSOR_ACTIVO`, `RELE_ENCENDIDO`, `BOTON_PULSADO` y los `RETARDO_*` estan
  arriba del `.ino` para calibrar sin tocar la logica.

## Como funciona la faja

Modo **arranca-para**: para en la estacion 1 con cada botella (foto nitida) y
en la estacion 2 solo si hay que expulsar. Procesa las botellas de a una: hay
que mantener separacion con las guias laterales. Ver "Flujo de la faja" arriba.
Estados en `tipos.h`: `Est1` (5) y `Est2` (4).

## Restricciones del UNO

- 2 KB de RAM: nada de `String` dinamicos ni arreglos grandes. Textos fijos
  con `F("...")`.
- Librerias: **LiquidCrystal I2C** (Frank de Brabander) y **Servo** (Arduino).
  Instalar ambas desde el Library Manager o con `arduino-cli lib install`.

## Comandos

```bash
# --- Firmware (necesita arduino-cli) ---
arduino-cli compile --fqbn arduino:avr:uno faja_botellas
arduino-cli upload -p COM3 --fqbn arduino:avr:uno faja_botellas
arduino-cli board list        # ver en que COM esta el Arduino
arduino-cli compile --fqbn arduino:avr:uno pruebas/prueba_servos   # test de servos (Fase 3)

# --- Vision (necesita vision/best.pt) ---
cd vision
python -m pip install -r requirements.txt      # incluye ultralytics (arrastra torch)
python probar_modelo.py                        # corre best.pt sobre vision/muestras/
python inspector_botellas.py --listar-camaras  # lista las camaras conectadas y sale
python inspector_botellas.py                   # inspeccion real, con Arduino (autodetecta COM)
python inspector_botellas.py --sin-arduino     # sin hardware: ESPACIO simula una botella
python inspector_botellas.py --sin-arduino --calibrar --camara 1   # deteccion en vivo, camara 1
python inspector_botellas.py --guardar         # junta capturas en capturas/ para reentrenar
python entrenar_modelo.py --eval               # mide best.pt contra capturas/
```

## Reglas para trabajar en este repo

- Todo comentario y mensaje de usuario en **español** (el codigo usa ASCII sin
  tildes para evitar problemas de encoding en el compilador de Arduino).
- Un solo programa a la vez puede abrir el COM: cerra el Monitor Serie del
  Arduino IDE antes de correr Python o de subir codigo. Error tipico:
  "Access denied" / "port busy".
- Despues de tocar el `.ino`, compila con `arduino-cli` y arregla los errores
  antes de dar el cambio por hecho.
- Cambios al protocolo o a los pines: actualiza tambien este archivo.
- Los umbrales del modelo (`conf_ok`, `conf_defecto`, `conf_detectar`,
  `nivel_min`, `cuello_frac`) viven en `config.json -> modelo` y se ajustan con
  fotos reales.
