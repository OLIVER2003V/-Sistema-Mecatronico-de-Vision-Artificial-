/*
  ============================================================================
  FAJA CLASIFICADORA DE BOTELLAS  ---  Firmware Arduino UNO
  ============================================================================
  Trabaja junto con el programa de vision en Python (carpeta vision/).

  FLUJO (2 estaciones, 1 sola camara)
  -----------------------------------
    1. La cinta esta en movimiento.
    2. El SENSOR 1 detecta una botella.
    3. La cinta se detiene.
    4. La camara (PC) clasifica: defecto fisico / llenado bajo / OK.
    5. Si tiene defecto fisico (rota, sin tapa, falta etiqueta/tapa)  ->  el
       SERVO 1 (pin 10) la expulsa. La cinta vuelve a andar.
    6. Si NO tiene defecto fisico, sigue hasta el SENSOR 2.
    7. El SENSOR 2 la detecta.
    8. Si el llenado es < 60%  ->  la cinta se detiene y el SERVO 2 (pin 11) la
       expulsa. Si esta OK, pasa de largo sin detenerse.
    9. La cinta vuelve a andar.

  El veredicto se calcula UNA vez en la estacion 1 y el Arduino lo recuerda
  hasta la estacion 2 (una cola de 'A'/'L'; la 'D' no llega, se expulsa antes).

  PROTOCOLO SERIE  (9600 baudios, 8N1)
  -----------------------------------
    Arduino -> PC :  'B'   "hay una botella detenida frente a la camara"
    PC -> Arduino :  'A'  aceptada        -> sigue de largo
                     'D'  defecto fisico  -> la expulsa el SERVO 1 (estacion 1)
                     'L'  llenado bajo    -> la expulsa el SERVO 2 (estacion 2)
    Arduino -> PC :  lineas que empiezan con '#' son solo informativas
                     (contadores, avisos). La PC solo reacciona a una 'B'.
                     NINGUNA linea '#' contiene la letra 'B'.

  Si cambias estas letras, cambialas tambien en vision/clasificador.py.

  ESTACIONES (en orden sobre la faja)
  -----------------------------------
     [sensor 1 / camara / servo 1 (pin 10)]  ->  [sensor 2 / servo 2 (pin 11)]  -> salida

     Servo 1 (pin 10) = expulsa DEFECTO FISICO ('D').
     Servo 2 (pin 11) = expulsa LLENADO BAJO ('L').
     Lo aceptado ('A') no se toca y sale por el final.

  Modo ARRANCA-PARA: la cinta para en la estacion 1 en cada botella (foto
  nitida) y en la estacion 2 solo si hay que expulsar. Mantener separacion
  entre botellas con las guias laterales.

  PINES  (no usar 0 y 1: los ocupa el puerto serie)
  ------
     10  servo 1 (defecto fisico)        11  servo 2 (llenado bajo)
      9  modulo rele -> motor faja
      8  sensor barrera 1 (camara)        7  sensor barrera 2
      3  boton START                      4  boton STOP        5  boton RESET
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
// Comprobalo con el Monitor Serie antes de dejarlo fijo.
const uint8_t SENSOR_ACTIVO = LOW;

// Muchos modulos rele azules se activan con LOW. Si el motor arranca al reves
// de lo que esperas, cambia esto a HIGH.
const uint8_t RELE_ENCENDIDO = LOW;

// Con resistencia pull-down de 10 kohm, el boton pulsado entrega HIGH.
const uint8_t BOTON_PULSADO = HIGH;

// Angulos de los servos (grados).
const uint8_t SERVO_REPOSO = 20;
const uint8_t SERVO_EMPUJE = 110;

// Tiempos en milisegundos. Ajustar con botellas reales.
const uint16_t RETARDO_CAM_MS      = 250;  // centrar botella frente a la camara antes de parar
const uint16_t RETARDO_EST2_MS     = 150;  // centrar botella frente al servo 2 antes de empujar
const uint16_t RETARDO_EMPUJE_MS   = 450;  // cuanto queda afuera la paleta
const uint16_t RETARDO_LIBERAR_MS  = 350;  // mover faja para despejar el sensor tras cada estacion
const uint16_t ANTIREBOTE_MS       = 30;   // botones
const uint32_t TIMEOUT_PC_MS       = 3000; // si la PC no contesta, la botella pasa como aceptada

// ============================= PINES =====================================
const uint8_t PIN_SERVO_1   = 10;   // defecto fisico
const uint8_t PIN_SERVO_2   = 11;   // llenado bajo
const uint8_t PIN_RELE      = 9;
const uint8_t PIN_SEN_1     = 8;    // estacion 1: dispara camara + servo 1
const uint8_t PIN_SEN_2     = 7;    // estacion 2
const uint8_t PIN_BTN_START = 3;
const uint8_t PIN_BTN_STOP  = 4;
const uint8_t PIN_BTN_RESET = 5;

// ============================ OBJETOS ====================================
LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);
Servo servo1;   // pin 10, expulsa 'D'
Servo servo2;   // pin 11, expulsa 'L'

// ====================== COLA DE VEREDICTOS ===============================
// (struct Cola y las funciones colaXxx viven en tipos.h)
Cola cola;   // veredictos 'A'/'L' que van de la estacion 1 a la estacion 2

// ============================ ESTADO ====================================
bool fajaActiva = false;

// Solicitudes de parada del motor (una por estacion). El motor gira solo si
// la faja esta activa y NADIE pide parar.
bool para1 = false, para2 = false;

Est1 est1 = E1_BUSCA;
Est2 est2 = E2_BUSCA;
uint32_t t1 = 0, t2 = 0;

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
  servo1.write(SERVO_REPOSO);
  servo2.write(SERVO_REPOSO);
  para1 = para2 = false;
  est1 = E1_BUSCA; est2 = E2_BUSCA;
  colaVaciar(cola);
  lcdSucio = true;
  Serial.println(F("#STOP"));
}

void resetContadores() {
  nTotal = nBuena = nNivel = nDefec = 0;
  colaVaciar(cola);
  lcdSucio = true;
  Serial.println(F("#RESET"));
}

// ============================= SETUP ===================================
void setup() {
  Serial.begin(9600);

  pinMode(PIN_RELE, OUTPUT);
  motor(false);

  pinMode(PIN_SEN_1, INPUT);
  pinMode(PIN_SEN_2, INPUT);
  pinMode(PIN_BTN_START, INPUT);
  pinMode(PIN_BTN_STOP, INPUT);
  pinMode(PIN_BTN_RESET, INPUT);

  servo1.attach(PIN_SERVO_1);
  servo2.attach(PIN_SERVO_2);
  servo1.write(SERVO_REPOSO);
  servo2.write(SERVO_REPOSO);

  lcd.init();
  lcd.backlight();
  refrescarLcd();

  Serial.println(F("#LISTO faja botellas"));
  Serial.println(F("#PC: S=start X=stop R=reset ; responde A/D/L al pedido de foto"));
}

// ================= ESTACION 1: camara + servo 1 ('D') =================
void tareaEstacion1() {
  switch (est1) {
    case E1_BUSCA:
      if (sensorTapado(PIN_SEN_1)) { t1 = millis(); est1 = E1_CENTRA; }
      break;

    case E1_CENTRA:
      if (millis() - t1 >= RETARDO_CAM_MS) {
        para1 = true;            // detener faja para la foto
        Serial.print('B');       // pedir veredicto a la PC
        t1 = millis();
        est1 = E1_ESPERA;
      }
      break;

    case E1_ESPERA: {
      char v = 0;
      while (Serial.available()) {
        char c = Serial.read();
        if      (c == 'A' || c == 'a') v = 'A';
        else if (c == 'D' || c == 'd') v = 'D';
        else if (c == 'L' || c == 'l') v = 'L';
      }
      if (v == 0 && (millis() - t1) > TIMEOUT_PC_MS) {
        v = 'A';                  // la PC no contesto: dejar pasar
        Serial.println(F("#TIMEOUT"));
      }
      if (v != 0) {
        contar(v);
        if (v == 'D') {                 // defecto fisico: expulsar aca mismo
          servo1.write(SERVO_EMPUJE);
          t1 = millis();
          est1 = E1_EMPUJA;
        } else {                        // 'A' o 'L': que siga a la estacion 2
          colaPush(cola, v);
          para1 = false;               // reanudar faja
          t1 = millis();
          est1 = E1_LIBERA;
        }
      }
      break;
    }

    case E1_EMPUJA:
      if (millis() - t1 >= RETARDO_EMPUJE_MS) {
        servo1.write(SERVO_REPOSO);
        para1 = false;                  // reanudar faja
        t1 = millis();
        est1 = E1_LIBERA;
      }
      break;

    case E1_LIBERA:
      // avanzar hasta despejar el sensor, para no re-detectar la misma botella
      if (!sensorTapado(PIN_SEN_1) && (millis() - t1) > RETARDO_LIBERAR_MS)
        est1 = E1_BUSCA;
      break;
  }
}

// ================= ESTACION 2: servo 2 ('L') =========================
void tareaEstacion2() {
  switch (est2) {
    case E2_BUSCA:
      if (sensorTapado(PIN_SEN_2) && colaFrente(cola) != 0) {
        t2 = millis();
        est2 = E2_CENTRA;
      }
      break;

    case E2_CENTRA:
      if (millis() - t2 >= RETARDO_EST2_MS) {
        char v = colaFrente(cola);
        colaPop(cola);
        if (v == 'L') {                 // llenado bajo: parar y empujar
          para2 = true;
          servo2.write(SERVO_EMPUJE);
          t2 = millis();
          est2 = E2_EMPUJA;
        } else {                        // 'A': pasa de largo sin detenerse
          t2 = millis();
          est2 = E2_LIBERA;
        }
      }
      break;

    case E2_EMPUJA:
      if (millis() - t2 >= RETARDO_EMPUJE_MS) {
        servo2.write(SERVO_REPOSO);
        para2 = false;
        t2 = millis();
        est2 = E2_LIBERA;
      }
      break;

    case E2_LIBERA:
      if (!sensorTapado(PIN_SEN_2) && (millis() - t2) > RETARDO_LIBERAR_MS)
        est2 = E2_BUSCA;
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

  // --- Comandos desde la PC ---
  // Solo se leen cuando NO hay una botella esperando veredicto.
  if (est1 != E1_ESPERA) {
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
    tareaEstacion1();
    tareaEstacion2();
  }

  // --- Motor: gira solo si la faja esta activa y nadie pide parar ---
  motor(fajaActiva && !para1 && !para2);

  // --- LCD (solo cuando cambio algo: el I2C es lento) ---
  if (lcdSucio) refrescarLcd();
}
