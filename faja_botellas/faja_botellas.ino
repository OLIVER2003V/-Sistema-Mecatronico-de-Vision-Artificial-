/*
  ============================================================================
  FAJA CLASIFICADORA DE BOTELLAS  ---  Firmware Arduino UNO
  ============================================================================
  Trabaja junto con el programa de vision en Python (carpeta vision/).

  PROTOCOLO SERIE  (9600 baudios, 8N1)
  -----------------------------------
    Arduino -> PC :  'B'   "hay una botella detenida frente a la camara"
    PC -> Arduino :  'A'  aceptada       -> sigue de largo
                     'D'  defectuosa     -> la expulsa el servo de la estacion D
                     'L'  nivel de agua  -> la expulsa el servo de la estacion L
                                            (botella mal llenada o vacia)
    Arduino -> PC :  lineas que empiezan con '#' son solo informativas
                     (contadores, avisos). La PC las ignora.
                     NINGUNA linea '#' contiene la letra 'B'.

  Si cambias estas letras, cambialas tambien en vision/clasificador.py.

  ESTACIONES (en orden sobre la faja)
  -----------------------------------
     [camara / sensor 8]  ->  [servo L / sensor 7]  ->  [servo D / sensor 6]  -> salida

     Estacion L = rechazo por NIVEL DE AGUA.
     Estacion D = rechazo por DEFECTO FISICO (rota / sin tapa).
     Lo aceptado no se toca y sale por el final.

  La faja funciona en modo ARRANCA-PARA: se detiene en cada estacion mientras
  trabaja. Es mas lento pero da fotos nitidas y expulsiones limpias. Cuando
  todo funcione se puede pasar a faja continua ajustando los RETARDO_*.

  PINES  (no usar 0 y 1: los ocupa el puerto serie)
  ------
     11  servo estacion L            10  servo estacion D
      9  modulo rele -> motor faja
      8  sensor barrera camara        7  sensor barrera L      6  sensor barrera D
      3  boton START                  4  boton STOP            5  boton RESET
     SDA/SCL (A4/A5)  LCD 16x2 I2C

  MEMORIA: el UNO tiene 2 KB de RAM. Nada de String dinamicos ni arreglos
  grandes. Los textos fijos van con F("...") para dejarlos en la flash.
  ============================================================================
*/

#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>
#include "tipos.h"

// ======================= AJUSTES QUE VAS A TOCAR ==========================

// Direccion I2C del LCD. Si la pantalla queda en blanco proba 0x3F.
const uint8_t LCD_ADDR = 0x27;

// Nivel que entrega el receptor de la barrera CUANDO LA BOTELLA CORTA EL HAZ.
// Comprobalo con el Monitor Serie antes de comprar los 3 pares (Fase 3).
const uint8_t SENSOR_ACTIVO = LOW;

// Muchos modulos rele azules se activan con LOW. Si el motor arranca al reves
// de lo que esperas, cambia esto a HIGH.
const uint8_t RELE_ENCENDIDO = LOW;

// Con resistencia pull-down de 10 kohm, el boton pulsado entrega HIGH.
const uint8_t BOTON_PULSADO = HIGH;

// Angulos de los servos (grados).
const uint8_t SERVO_REPOSO = 20;
const uint8_t SERVO_EMPUJE = 110;

// Tiempos en milisegundos. Ajustar en Fase 4 con botellas reales.
const uint16_t RETARDO_CAMARA_MS   = 250;  // centrar botella frente a la camara antes de parar
const uint16_t RETARDO_SERVO_L_MS  = 150;  // centrar botella frente al servo L antes de empujar
const uint16_t RETARDO_SERVO_D_MS  = 150;  // idem servo D
const uint16_t RETARDO_EMPUJE_MS   = 450;  // cuanto queda afuera la paleta
const uint16_t RETARDO_LIBERAR_MS  = 350;  // mover faja para despejar el sensor tras cada estacion
const uint16_t ANTIREBOTE_MS       = 30;   // botones
const uint32_t TIMEOUT_PC_MS       = 3000; // si la PC no contesta, la botella pasa como aceptada

// ============================= PINES =====================================
const uint8_t PIN_SERVO_L   = 11;
const uint8_t PIN_SERVO_D   = 10;
const uint8_t PIN_RELE      = 9;
const uint8_t PIN_SEN_CAM   = 8;
const uint8_t PIN_SEN_L     = 7;
const uint8_t PIN_SEN_D     = 6;
const uint8_t PIN_BTN_START = 3;
const uint8_t PIN_BTN_STOP  = 4;
const uint8_t PIN_BTN_RESET = 5;

// ============================ OBJETOS ====================================
LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);
Servo servoL;
Servo servoD;

// ====================== COLA DE VEREDICTOS ===============================
// (struct Cola y las funciones colaXxx viven en tipos.h)
Cola colaCam;  // veredictos que salen de la camara, los consume la estacion L
Cola colaD;    // veredictos que la estacion L deja pasar, los consume la estacion D

// ============================ ESTADO ====================================
bool fajaActiva = false;

// Solicitudes de parada del motor (una por estacion). El motor gira solo si
// la faja esta activa y NADIE pide parar.
bool paraCam = false, paraL = false, paraD = false;

EstCam estCam = CAM_BUSCA;
EstSrv estL = SRV_BUSCA;
EstSrv estD = SRV_BUSCA;
uint32_t tCam = 0, tL = 0, tD = 0;

uint16_t nTotal = 0, nBuena = 0, nNivel = 0, nDefec = 0;

bool lcdSucio = true;

// ======================= FUNCIONES BASE =================================
bool sensorTapado(uint8_t pin) {
  return digitalRead(pin) == SENSOR_ACTIVO;
}

void motor(bool encender) {
  if (encender) digitalWrite(PIN_RELE, RELE_ENCENDIDO);
  else          digitalWrite(PIN_RELE, RELE_ENCENDIDO == HIGH ? LOW : HIGH);
}

void refrescarLcd() {
  lcd.clear();
  if (!fajaActiva) {
    lcd.setCursor(0, 0); lcd.print(F("Faja detenida"));
    lcd.setCursor(0, 1); lcd.print(F("START = arrancar"));
  } else {
    lcd.setCursor(0, 0);
    lcd.print(F("Tot:")); lcd.print(nTotal);
    lcd.print(F(" Ok:")); lcd.print(nBuena);
    lcd.setCursor(0, 1);
    lcd.print(F("Niv:")); lcd.print(nNivel);
    lcd.print(F(" Def:")); lcd.print(nDefec);
  }
  lcdSucio = false;
}

void informar() {
  // Sin la letra 'B' en ningun lado: la PC solo reacciona a una 'B' suelta.
  Serial.print(F("#tot=")); Serial.print(nTotal);
  Serial.print(F(" ok="));  Serial.print(nBuena);
  Serial.print(F(" niv=")); Serial.print(nNivel);
  Serial.print(F(" df="));  Serial.println(nDefec);
}

void contar(char v) {
  nTotal++;
  if (v == 'L') nNivel++;
  else if (v == 'D') nDefec++;
  else nBuena++;
  lcdSucio = true;
  informar();
}

// Boton con antirrebote: devuelve true una sola vez, al presionar.
bool flancoBoton(uint8_t pin, bool &previo, uint32_t &marca) {
  bool ahora = (digitalRead(pin) == BOTON_PULSADO);
  if (ahora != previo && (millis() - marca) > ANTIREBOTE_MS) {
    marca = millis();
    previo = ahora;
    return ahora;
  }
  return false;
}

void pararTodo() {
  fajaActiva = false;
  motor(false);
  servoL.write(SERVO_REPOSO);
  servoD.write(SERVO_REPOSO);
  paraCam = paraL = paraD = false;
  estCam = CAM_BUSCA; estL = SRV_BUSCA; estD = SRV_BUSCA;
  colaVaciar(colaCam); colaVaciar(colaD);
  lcdSucio = true;
  Serial.println(F("#STOP"));
}

void resetContadores() {
  nTotal = nBuena = nNivel = nDefec = 0;
  colaVaciar(colaCam); colaVaciar(colaD);
  lcdSucio = true;
  Serial.println(F("#RESET"));
}

// ============================= SETUP ===================================
void setup() {
  Serial.begin(9600);

  pinMode(PIN_RELE, OUTPUT);
  motor(false);

  pinMode(PIN_SEN_CAM, INPUT);
  pinMode(PIN_SEN_L, INPUT);
  pinMode(PIN_SEN_D, INPUT);
  pinMode(PIN_BTN_START, INPUT);
  pinMode(PIN_BTN_STOP, INPUT);
  pinMode(PIN_BTN_RESET, INPUT);

  servoL.attach(PIN_SERVO_L);
  servoD.attach(PIN_SERVO_D);
  servoL.write(SERVO_REPOSO);
  servoD.write(SERVO_REPOSO);

  lcd.init();
  lcd.backlight();
  refrescarLcd();

  Serial.println(F("#LISTO faja botellas"));
  Serial.println(F("#PC: S=start X=stop R=reset ; contesta A/D/L cuando reciba B"));
}

// ==================== MAQUINA DE LA CAMARA =============================
void tareaCamara() {
  switch (estCam) {
    case CAM_BUSCA:
      if (sensorTapado(PIN_SEN_CAM)) { tCam = millis(); estCam = CAM_CENTRA; }
      break;

    case CAM_CENTRA:
      if (millis() - tCam >= RETARDO_CAMARA_MS) {
        paraCam = true;          // detener faja para la foto
        Serial.print('B');       // pedir veredicto a la PC
        tCam = millis();
        estCam = CAM_ESPERA;
      }
      break;

    case CAM_ESPERA: {
      char v = 0;
      while (Serial.available()) {
        char c = Serial.read();
        if (c == 'A' || c == 'D' || c == 'L') v = c;
        else if (c == 'a') v = 'A';
        else if (c == 'd') v = 'D';
        else if (c == 'l') v = 'L';
      }
      if (v == 0 && (millis() - tCam) > TIMEOUT_PC_MS) {
        v = 'A';                  // la PC no contesto: dejar pasar
        Serial.println(F("#TIMEOUT"));
      }
      if (v != 0) {
        colaPush(colaCam, v);
        contar(v);
        paraCam = false;         // reanudar
        tCam = millis();
        estCam = CAM_LIBERA;
      }
      break;
    }

    case CAM_LIBERA:
      // avanzar hasta despejar el sensor, para no re-detectar la misma botella
      if (!sensorTapado(PIN_SEN_CAM) && (millis() - tCam) > RETARDO_LIBERAR_MS)
        estCam = CAM_BUSCA;
      break;
  }
}

// ============ MAQUINA GENERICA DE UNA ESTACION DE SERVO ===============
// 'letra' es 'L' o 'D'. 'salida' puede ser nullptr (ultima estacion).
void tareaServo(EstSrv &est, uint32_t &t, uint8_t pinSensor, Servo &servo,
                bool &solicitudParar, Cola &entrada, Cola *salida,
                char letra, uint16_t retardoCentrar) {
  switch (est) {
    case SRV_BUSCA:
      if (sensorTapado(pinSensor) && colaFrente(entrada) != 0) {
        t = millis();
        est = SRV_CENTRA;
      }
      break;

    case SRV_CENTRA:
      if (millis() - t >= retardoCentrar) {
        char v = colaFrente(entrada);
        colaPop(entrada);
        if (v == letra) {
          solicitudParar = true;         // parar faja para empujar
          servo.write(SERVO_EMPUJE);
          t = millis();
          est = SRV_EMPUJA;
        } else {
          if (salida && v != 0) colaPush(*salida, v);  // que siga a la proxima
          t = millis();
          est = SRV_LIBERA;
        }
      }
      break;

    case SRV_EMPUJA:
      if (millis() - t >= RETARDO_EMPUJE_MS) {
        servo.write(SERVO_REPOSO);
        solicitudParar = false;
        t = millis();
        est = SRV_LIBERA;
      }
      break;

    case SRV_LIBERA:
      if (!sensorTapado(pinSensor) && (millis() - t) > RETARDO_LIBERAR_MS)
        est = SRV_BUSCA;
      break;
  }
}

// ============================== LOOP =================================
bool prevStart = false, prevStop = false, prevReset = false;
uint32_t mStart = 0, mStop = 0, mReset = 0;

void loop() {
  // --- Botones ---
  if (flancoBoton(PIN_BTN_START, prevStart, mStart)) {
    if (!fajaActiva) { fajaActiva = true; lcdSucio = true; Serial.println(F("#START")); }
  }
  if (flancoBoton(PIN_BTN_STOP, prevStop, mStop))   pararTodo();
  if (flancoBoton(PIN_BTN_RESET, prevReset, mReset)) resetContadores();

  // --- Comandos desde la PC (utiles en Fase 3) ---
  // Solo se leen cuando NO hay una botella esperando veredicto.
  if (estCam != CAM_ESPERA) {
    while (Serial.available()) {
      char c = Serial.read();
      if (c == 'S') { if (!fajaActiva) { fajaActiva = true; lcdSucio = true; Serial.println(F("#START")); } }
      else if (c == 'X') pararTodo();
      else if (c == 'R') resetContadores();
      // cualquier otro byte suelto se descarta
    }
  }

  // --- Estaciones ---
  if (fajaActiva) {
    tareaCamara();
    tareaServo(estL, tL, PIN_SEN_L, servoL, paraL, colaCam, &colaD,   'L', RETARDO_SERVO_L_MS);
    tareaServo(estD, tD, PIN_SEN_D, servoD, paraD, colaD,   nullptr,  'D', RETARDO_SERVO_D_MS);
  }

  // --- Motor: gira solo si la faja esta activa y nadie pide parar ---
  motor(fajaActiva && !paraCam && !paraL && !paraD);

  // --- LCD (solo cuando cambio algo: el I2C es lento) ---
  if (lcdSucio) refrescarLcd();
}
