# Faja clasificadora de botellas

Faja transportadora que inspecciona botellas con una camara y las separa en
tres grupos:

- **Aceptada** (`A`) — botella, etiqueta, tapa y llenado OK. Sale por el final.
- **Defectuosa** (`D`) — rota, sin tapa, o le falta la etiqueta. La expulsa el
  **servo 1 (pin 10)** en la estacion 1.
- **Llenado bajo** (`L`) — bien por fuera pero con menos del 60% de liquido. La
  expulsa el **servo 2 (pin 11)** en la estacion 2.

Flujo (2 estaciones, 1 sola camara):

```
cinta -> [sensor 1: para, foto, clasifica] --D--> servo 1 expulsa, sigue
                     |
                     A / L
                     v
         [sensor 2] --L--> para, servo 2 expulsa       --A--> pasa de largo
```

El veredicto se calcula una vez (estacion 1) y el Arduino lo recuerda para la
estacion 2.

Piezas:

- **Arduino UNO** (`faja_botellas/`) mueve la faja, los 2 servos de expulsion y
  el LCD. 2 sensores de barrera, 3 botones.
- **Python + YOLO** (`vision/`) toma la foto, la pasa por el modelo `best.pt`
  (Ultralytics) y decide.
- Se comunican por USB con un protocolo de una letra (ver `CLAUDE.md`).

```
PROYECTO SW2/
├── CLAUDE.md                     instrucciones del proyecto (protocolo, pines, reglas)
├── faja_botellas/
│   ├── faja_botellas.ino         firmware del Arduino UNO
│   └── tipos.h
├── pruebas/
│   └── prueba_servos/            sketch suelto para probar los 2 servos
└── vision/
    ├── clasificador.py           carga best.pt y aplica la regla A / D / L
    ├── inspector_botellas.py     programa principal (camara + serie)
    ├── probar_modelo.py          prueba el modelo sobre fotos sueltas (sin hardware)
    ├── entrenar_modelo.py        --eval mide best.pt ; abajo, como reentrenar
    ├── config.json               umbrales del modelo y de la camara
    ├── requirements.txt
    ├── best.pt                   TU modelo (no viene en el repo: copialo aca)
    ├── muestras/                 fotos para probar_modelo.py
    └── capturas/                 fotos que se juntan con --guardar
```

## 0. Instalar lo que falta (Windows)

```powershell
winget install -e --id Python.Python.3.12
winget install -e --id ArduinoSA.CLI
# cerra y volve a abrir la terminal para que tomen el PATH
```

Si `python` sigue abriendo la Microsoft Store en vez del Python real: es el
"alias de ejecucion de aplicaciones". Apagalo en Configuracion > Aplicaciones >
Configuracion avanzada de aplicaciones > Alias de ejecucion de aplicaciones
(python.exe y python3.exe), o borra los stubs de 0 bytes en
`%LOCALAPPDATA%\Microsoft\WindowsApps\python*.exe`.

Driver del Arduino clon (chip CH340): buscar "CH340 driver Windows" e instalar.

## 1. Solo software (sin comprar nada)

```powershell
cd "vision"
python -m pip install -r requirements.txt      # incluye ultralytics; descarga torch (~1 GB, tarda)
```

**Copia tu `best.pt` dentro de `vision/`** (queda `vision/best.pt`). Si lo
tenes en otro lado, pasa `--modelo C:\ruta\best.pt` o edita `config.json`.

Deja unas fotos de botellas en `vision/muestras/` y proba:

```powershell
python probar_modelo.py
```

Imprime el veredicto `A` / `D` / `L` de cada foto con las confianzas por clase
y guarda `resultado_modelo.png` con las cajas dibujadas.

Para el firmware:

```powershell
arduino-cli core install arduino:avr
arduino-cli lib install "LiquidCrystal I2C"
arduino-cli lib install Servo
arduino-cli compile --fqbn arduino:avr:uno faja_botellas
```

(En Arduino IDE: Library Manager -> instalar **LiquidCrystal I2C** de Frank de
Brabander y **Servo** de Arduino.)

## 2. Banco de vision (camara + luz, sin faja)

Camara fija a 30-40 cm, con buena luz difusa y fondo parejo.

```powershell
cd "vision"
python inspector_botellas.py --sin-arduino --calibrar
```

- Ajusta `roi` en `config.json` para encuadrar solo la botella.
- Con `--calibrar` ves las confianzas por clase y el `nivel_llenado` en vivo.
- **Nivel de llenado**: no es la confianza de "Agua", se mide por geometria
  (cuanto sube la caja de agua en la botella). Con una botella LLENA delante,
  `nivel_llenado` deberia dar ~1.0; si da otra cosa, ajusta `cuello_frac` en
  `config.json`. Despues fija `nivel_min` (0.60 = "descarta si esta a menos del
  60%").
- Si algo mas se clasifica mal, mueve `conf_ok` / `conf_defecto` (tecla `s`
  guarda). Pasa las 70 botellas de prueba y anota esperado vs obtenido.

## 3. Banco electronico (sobre la mesa, sin faja)

Primero, probar los servos solos (confirma cableado y fuente externa):

```powershell
arduino-cli compile --fqbn arduino:avr:uno pruebas/prueba_servos
arduino-cli upload -p COM3 --fqbn arduino:avr:uno pruebas/prueba_servos
# Monitor Serie 9600: hacen un ciclo cada 2s; teclas  l  d  o un angulo 0-180
```

Despues, el firmware real, simulando los sensores con un cable a GND
(**pin 8** = sensor 1: camara + servo 1 · **pin 7** = sensor 2: servo 2):

```powershell
arduino-cli upload -p COM3 --fqbn arduino:avr:uno faja_botellas
```

En el Monitor Serie (9600): `S` arranca · `X` para · `R` resetea.

- **Servo 1 (defecto, pin 10):** `S` -> pin 8 a GND -> mandar `D` ->
  el servo 1 empuja en el acto -> soltar pin 8.
- **Servo 2 (llenado, pin 11):** `S` -> pin 8 a GND -> mandar `L` ->
  soltar pin 8 -> pin 7 a GND -> el servo 2 empuja.
- **Aceptada:** mandar `A`; no se activa ningun servo.

Con la camara conectada, en vez de teclear el veredicto:

```powershell
cd "vision"
python inspector_botellas.py --sin-ventana        # responde A/D/L al Arduino
```

## 4. Faja completa

Ajusta los `RETARDO_*` arriba del `.ino`: `RETARDO_CAM_MS` para que la botella
quede centrada frente a la camara, `RETARDO_EST2_MS` para el servo 2, y
`RETARDO_EMPUJE_MS` para el recorrido de la paleta. Vuelve a pasar las 70 botellas.

## Reentrenar el modelo

Corre siempre con `--guardar` para juntar fotos reales en `capturas/`.
`python entrenar_modelo.py --eval` mide cuanto acierta `best.pt` con esas fotos.
Para reentrenar con mas datos, ver el comando de Ultralytics al final de
`entrenar_modelo.py` (se hace en Google Colab, GPU gratis).

## Notas

- Un solo programa a la vez puede usar el COM. Cerra el Monitor Serie antes de
  correr Python o de subir codigo.
- Sin `vision/best.pt` el inspector no arranca (avisa con la ruta donde lo busca).
