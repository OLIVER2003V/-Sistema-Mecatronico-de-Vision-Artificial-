# Faja clasificadora de botellas

Faja transportadora que inspecciona botellas con una camara y las separa en
tres grupos: **buenas**, **problema de etiqueta** y **defecto fisico**
(abollada / sin tapa / aplastada).

- **Arduino UNO** (`faja_botellas/`) mueve la faja, los 2 servos de expulsion y
  el LCD.
- **Python + OpenCV** (`vision/`) toma la foto a contraluz y decide.
- Se comunican por USB con un protocolo de una letra (ver `CLAUDE.md`).

```
PROYECTO SW2/
├── CLAUDE.md                     instrucciones del proyecto (protocolo, pines, reglas)
├── faja_botellas/
│   └── faja_botellas.ino         firmware del Arduino UNO
└── vision/
    ├── clasificador.py           logica de vision (compartida)
    ├── inspector_botellas.py     programa principal (camara + serie)
    ├── demo_sintetico.py         prueba de humo sin hardware
    ├── entrenar_modelo.py        IA, para mas adelante (esqueleto)
    ├── config.json               umbrales (se ajustan al calibrar)
    ├── requirements.txt
    └── capturas/                 fotos que se juntan con --guardar
```

## 0. Instalar lo que falta (Windows)

En esta PC **no hay Python ni arduino-cli**. Desde PowerShell:

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
python -m pip install -r requirements.txt
python demo_sintetico.py
```

Si el mosaico sale casi todo con borde verde, el pipeline esta bien instalado.

Para el firmware:

```powershell
arduino-cli core install arduino:avr
arduino-cli lib install "LiquidCrystal I2C"
arduino-cli compile --fqbn arduino:avr:uno faja_botellas
```

## 2. Banco de vision (camara + luz, sin faja)

Camara fija a 30-40 cm, contraluz detras de un difusor, caja negra por dentro.

```powershell
cd "vision"
python inspector_botellas.py --sin-arduino --calibrar
```

- Ajusta `roi` en `config.json` para encuadrar solo la botella.
- Con `--calibrar` ves las metricas en vivo; la tecla `s` guarda `config.json`.
- Pasa las 70 botellas de prueba y anota esperado vs obtenido en un Excel.

## 3. Banco electronico (sobre la mesa, sin faja)

Sube el firmware y prueba tapando los sensores y pulsando los botones a mano:

```powershell
arduino-cli upload -p COM3 --fqbn arduino:avr:uno faja_botellas
cd "vision"
python inspector_botellas.py --sin-ventana        # responde A/E/D al Arduino
```

Comandos utiles por el Monitor Serie (a 9600): `S` arranca, `X` para, `R` resetea.

## 4. Faja completa

Ajusta los `RETARDO_*` arriba del `.ino` hasta que cada botella se detenga
justo frente a la camara y frente a cada servo. Vuelve a pasar las 70 botellas.

## Para despues: IA

Corre siempre con `--guardar` para juntar fotos reales. Cuando tengas unos
cientos, `entrenar_modelo.py` (en Google Colab) entrena un clasificador que
reemplaza las heuristicas.

## Notas

- Un solo programa a la vez puede usar el COM. Cerra el Monitor Serie antes de
  correr Python o de subir codigo.
- `clasificador.py` es una **base para calibrar**, no la version final.
