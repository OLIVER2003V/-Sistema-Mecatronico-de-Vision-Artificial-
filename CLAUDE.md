# Faja clasificadora de botellas

Proyecto de curso. Dos partes que se hablan por el puerto serie:

- `faja_botellas/` — firmware del **Arduino UNO** (C++). Controla motor (por
  modulo rele), 2 servos y un LCD 16x2 I2C. Lee 3 sensores de barrera y 3 botones.
- `vision/` — **vision en Python**. Toma la foto, la pasa por un modelo
  **YOLO (Ultralytics, `best.pt`)** y le dice al Arduino que hacer.

## Modelo de vision

- El modelo va en **`vision/best.pt`** (o ruta en `config.json -> modelo.ruta`,
  o `--modelo RUTA`). No se versiona (pesa); esta en `.gitignore`.
- Clases del modelo: `Botella Etiqueta Tapa Agua` (deben estar) y
  `Rota Notapa` (defectos).
- Regla en `vision/clasificador.py` (`conf_ok = 0.80`, `conf_defecto = 0.50`):
  - **A** aceptada — Botella + Etiqueta + Tapa + Agua, las 4 con conf >= `conf_ok`, sin Rota/Notapa.
  - **D** defectuosa — hay Rota o Notapa, o falta Botella/Etiqueta/Tapa.
  - **L** nivel de agua — lo fisico OK pero Agua < `conf_ok` (mal llenada / vacia).
  - **N** sin botella — el inspector lo trata como A.

## Protocolo serie (9600 baudios)

- Arduino -> PC: `B` = "hay una botella detenida frente a la camara".
- PC -> Arduino: `A` aceptada · `D` defectuosa · `L` nivel de agua.
- Arduino -> PC: lineas que empiezan con `#` son informativas (contadores /
  avisos) y **no contienen la letra `B`**; la PC las ignora.
- **Si cambias estas letras, cambialas en los dos lados**:
  `faja_botellas/faja_botellas.ino` y `vision/clasificador.py`.

## Pines del Arduino

- Servos: **11** (estacion L = nivel de agua), **10** (estacion D = defecto fisico)
- Motor por modulo rele: **9**
- Sensores de barrera: **8** (camara), **7** (L), **6** (D)
- Botones: **3** (START), **4** (STOP), **5** (RESET)
- LCD I2C en A4/A5. **No usar 0 y 1** (puerto serie).
- `SENSOR_ACTIVO`, `RELE_ENCENDIDO`, `BOTON_PULSADO` y los `RETARDO_*` estan
  arriba del `.ino` para calibrar sin tocar la logica.

## Como funciona la faja

Modo **arranca-para**: la faja se detiene en cada estacion mientras trabaja
(foto nitida, expulsion limpia). Procesa las botellas de a una: hay que
mantener separacion entre botellas con las guias laterales. Orden de estaciones:
`camara -> servo L -> servo D -> salida`.

## Restricciones del UNO

- 2 KB de RAM: nada de `String` dinamicos ni arreglos grandes. Textos fijos
  con `F("...")`.
- La libreria del LCD es **LiquidCrystal I2C** (Frank de Brabander). `Servo`
  viene incluida.

## Comandos

```bash
# --- Firmware (necesita arduino-cli) ---
arduino-cli compile --fqbn arduino:avr:uno faja_botellas
arduino-cli upload -p COM3 --fqbn arduino:avr:uno faja_botellas
arduino-cli board list        # ver en que COM esta el Arduino

# --- Vision (necesita vision/best.pt) ---
cd vision
python -m pip install -r requirements.txt      # incluye ultralytics (arrastra torch)
python probar_modelo.py                        # corre best.pt sobre vision/muestras/
python inspector_botellas.py                   # inspeccion real, con Arduino (autodetecta COM)
python inspector_botellas.py --sin-arduino     # sin hardware: ESPACIO simula una botella
python inspector_botellas.py --calibrar        # muestra las confianzas del modelo en vivo
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
- Los umbrales del modelo (`conf_ok`, `conf_defecto`, `conf_detectar`) viven en
  `config.json -> modelo` y se ajustan con fotos reales.
