/*
  ============================================================================
  FAJA CLASIFICADORA DE BOTELLAS  ---  Firmware Arduino UNO
  ============================================================================
  Trabaja junto con el programa de vision en Python (carpeta vision/).

  FLUJO (2 estaciones, 1 sola camara)
  -----------------------------------
    1. La cinta esta en movimiento.
    2. El SENSOR 1 detecta una botella.
    3. La cinta se detiene, minimo RETARDO_PARADA_SENSOR1_MS (3 s), sin
       importar que tan rapido conteste la PC: le da tiempo de sobra al
       servo 1 para empujar si hace falta.
    4. La camara (PC) clasifica: defecto fisico / llenado bajo / OK.
    5. Si tiene defecto fisico (rota, sin tapa, falta etiqueta/tapa)  ->  el
       SERVO 1 (pin 10) la expulsa. La cinta vuelve a andar.
    6. Si NO tiene defecto fisico, sigue hasta el SENSOR 2.
    7. El SENSOR 2 la detecta.
    8. Si el llenado es < 60%  ->  la cinta se detiene (minimo
       RETARDO_PARADA_SENSOR2_MS, 3 s) y el SERVO 2 (pin 11) la expulsa. Si
       esta OK, pasa de largo sin detenerse.
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
      3  boton START                      4  boton STOP           5  boton RESET
     SDA/SCL (A4/A5)  LCD 16x2 I2C

  Los botones fisicos (3/4/5) y los comandos por Monitor Serie (S/X/R) hacen
  exactamente lo mismo y conviven: se puede arrancar desde el tablero y parar
  desde la PC, o al reves. Los botones usan resistencia pull-down de 10 kohm
  (ver BOTON_PULSADO) y antirrebote por software (ver flancoBoton()).

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

// Muchos modulos rele azules se activan con LOW, pero en esta placa el rele
// prende con HIGH (se invirtio: antes quedaba apagado al dar START).
const uint8_t RELE_ENCENDIDO = HIGH;

// Con resistencia pull-down de 10 kohm, el boton pulsado entrega HIGH.
const uint8_t BOTON_PULSADO = HIGH;

// Angulos de los servos (grados): reposo (retraido) y empuje (estirado del
// todo). CADA SERVO TIENE SU PROPIO PAR porque los horns quedaron montados
// al reves entre si -- el servo 1 (pin 10) reposa en 0 y empuja hacia 180;
// el servo 2 (pin 11) es AL REVES: reposa en 180 y empuja hacia 0. Si algun
// servo vibra, hace ruido raro o no llega del todo a su extremo (esta
// chocando con algo mecanicamente), retrocede SOLO ese extremo unos grados
// hasta que se mueva libre en todo el recorrido.
const uint8_t SERVO1_REPOSO = 180;
const uint8_t SERVO1_EMPUJE = 0;
const uint8_t SERVO2_REPOSO = 180;
const uint8_t SERVO2_EMPUJE = 0;

// "Velocidad" del despliegue en la prueba manual ('1'/'2' por Monitor Serie):
// en vez de saltar de un angulo a otro de una, avanza de a SERVO_PASO_GRADOS
// cada SERVO_PASO_MS. Mas grados o menos ms = mas rapido; menos grados o mas
// ms = mas lento y suave. Siempre termina llegando al angulo pedido.
const uint8_t  SERVO_PASO_GRADOS = 4;
const uint16_t SERVO_PASO_MS     = 15;

// Tiempos en milisegundos. Ajustar con botellas reales.
const uint16_t RETARDO_CAM_MS      = 1200;    // sensor 1, camara y servo 1 en el mismo punto: parar de una
const uint16_t RETARDO_EST2_MS     = 800;  // centrar botella frente al servo 2 antes de empujar
const uint16_t RETARDO_EMPUJE_MS   = 450;  // cuanto queda afuera la paleta
const uint16_t RETARDO_LIBERAR_MS  = 350;  // mover faja para despejar el sensor tras cada estacion
const uint16_t ANTIREBOTE_MS       = 30;   // botones
const uint32_t TIMEOUT_PC_MS       = 3000; // si la PC no contesta, la botella pasa como aceptada

// La estacion 1 queda detenida este tiempo MINIMO desde que el sensor 1
// dispara, sin importar que tan rapido conteste la PC: le da tiempo de sobra
// al servo 1 para empujar (si hace falta) antes de que la cinta arranque.
const uint32_t RETARDO_PARADA_SENSOR1_MS = 3000;

// Lo mismo para la estacion 2: si hay que expulsar por llenado bajo ('L'),
// la cinta queda parada este minimo antes de reanudar (si es 'A', la
// estacion 2 no para nunca; ver tareaEstacion2()).
const uint32_t RETARDO_PARADA_SENSOR2_MS = 3000;

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
uint32_t tParada1 = 0;   // cuando empezo la parada de la estacion 1 (para el minimo de 3 s)
bool empuja1Activo = false;   // true mientras el servo 1 esta afuera empujando
uint32_t tParada2 = 0;   // idem, estacion 2
bool empuja2Activo = false;   // true mientras el servo 2 esta afuera empujando

// Movimiento gradual NO bloqueante de los servos automaticos (para que el
// empuje llegue siempre completo, sin frenar loop() -- STOP sigue andando
// aunque un servo este a mitad de camino). objetivoN < 0 = servo N quieto.
int16_t objetivo1 = -1, objetivo2 = -1;
uint32_t tPasoServo1 = 0, tPasoServo2 = 0;

// Sub-fases de un empuje automatico: sale -> se queda afuera -> vuelve.
const uint8_t FASE_SALE = 0, FASE_AFUERA = 1, FASE_VUELVE = 2;
uint8_t fase1 = FASE_SALE, fase2 = FASE_SALE;

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
    // 16 caracteres como maximo en esta linea.
    lcd.setCursor(0, 1); lcd.print(F("START o PC: S"));
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

// Boton con antirrebote: devuelve true una sola vez, al presionar (no mientras
// se mantiene apretado, y no al soltar).
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
  servo1.write(SERVO1_REPOSO);
  servo2.write(SERVO2_REPOSO);
  para1 = para2 = false;
  empuja1Activo = false;
  empuja2Activo = false;
  objetivo1 = objetivo2 = -1;   // cancela cualquier movimiento gradual pendiente
  fase1 = fase2 = FASE_SALE;
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

// Mueve el servo grado a grado (SERVO_PASO_GRADOS cada SERVO_PASO_MS) en vez
// de saltar de una, y siempre termina exactamente en 'objetivo' (se estira o
// retrae del todo, nunca se queda a mitad de camino). Usa delay(): solo para
// la prueba manual ('1'/'2'), no corre con la faja en marcha.
void moverGradual(Servo &s, uint8_t objetivo) {
  int actual = s.read();
  int paso = (objetivo > actual) ? SERVO_PASO_GRADOS : -SERVO_PASO_GRADOS;
  while (actual != objetivo) {
    int siguiente = actual + paso;
    if ((paso > 0 && siguiente > objetivo) || (paso < 0 && siguiente < objetivo))
      siguiente = objetivo;
    s.write(siguiente);
    delay(SERVO_PASO_MS);
    actual = siguiente;
  }
}

// Prueba manual de un servo por el Monitor Serie (teclas '1' y '2').
void probarServo(Servo &s, uint8_t reposo, uint8_t empuje, const __FlashStringHelper *nombre) {
  Serial.print(F("#prueba ")); Serial.println(nombre);
  moverGradual(s, empuje);
  delay(RETARDO_EMPUJE_MS);
  moverGradual(s, reposo);
}

// Mueve el servo a un angulo fijo y lo DEJA ahi (no vuelve solo), para poder
// mirarlo con calma y decidir cual angulo de reposo es el correcto. Teclas
// '6'-'9' del Monitor Serie, todas sobre el servo 1 (ver loop()).
void probarAngulo(Servo &s, uint8_t angulo, const __FlashStringHelper *nombre) {
  Serial.print(F("#angulo ")); Serial.print(nombre);
  Serial.print(F(" -> ")); Serial.println(angulo);
  moverGradual(s, angulo);
}

// ---- Version NO bloqueante de moverGradual, para el empuje automatico ----
// moverA() solo anota el objetivo; avanzarServo() lo va acercando de a poco
// cada vez que se llama (desde loop(), sin frenar nada). Cuando llega, deja
// el objetivo en -1 -- asi el resto del codigo sabe "ya llegue" sin bloquear.
void moverA(int16_t &objetivo, uint8_t angulo) {
  objetivo = angulo;
}

void avanzarServo(Servo &s, int16_t &objetivo, uint32_t &tPaso) {
  if (objetivo < 0) return;
  int actual = s.read();
  if (actual == objetivo) { objetivo = -1; return; }
  if (millis() - tPaso < SERVO_PASO_MS) return;
  tPaso = millis();
  int paso = (objetivo > actual) ? SERVO_PASO_GRADOS : -SERVO_PASO_GRADOS;
  int siguiente = actual + paso;
  if ((paso > 0 && siguiente > objetivo) || (paso < 0 && siguiente < objetivo))
    siguiente = objetivo;
  s.write(siguiente);
}

// ============================= SETUP ===================================
void setup() {
  Serial.begin(9600);

  pinMode(PIN_RELE, OUTPUT);
  motor(false);

  pinMode(PIN_SEN_1, INPUT);
  pinMode(PIN_SEN_2, INPUT);
  // INPUT a secas (no INPUT_PULLUP): los botones llevan pull-down de 10 kohm
  // por fuera, asi que en reposo el pin ya lee LOW.
  pinMode(PIN_BTN_START, INPUT);
  pinMode(PIN_BTN_STOP, INPUT);
  pinMode(PIN_BTN_RESET, INPUT);

  servo1.attach(PIN_SERVO_1);
  servo2.attach(PIN_SERVO_2);
  servo1.write(SERVO1_REPOSO);
  servo2.write(SERVO2_REPOSO);

  lcd.init();
  lcd.backlight();
  refrescarLcd();

  Serial.println(F("#LISTO faja botellas"));
  Serial.println(F("#Botones fisicos ACTIVOS: pin3=start pin4=stop pin5=reset"));
  Serial.println(F("#PC: S=start X=stop R=reset ; responde A/D/L al pedido de foto"));
  Serial.println(F("#PRUEBA: 1=empuja servo1(pin10) 2=empuja servo2(pin11)"));
  Serial.println(F("#PRUEBA REPOSO SERVO1: 6=10 7=20 8=30 9=40 (se quedan ahi)"));
  Serial.println(F("#PRUEBA EMPUJE: 3=serv1@180 4=serv1@165 5=serv2@0 0=serv2@15 (se quedan ahi)"));
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
        tParada1 = millis();     // arranca el minimo de RETARDO_PARADA_SENSOR1_MS
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
          moverA(objetivo1, SERVO1_EMPUJE);
          empuja1Activo = true;
          fase1 = FASE_SALE;
        } else {                        // 'A' o 'L': que siga a la estacion 2
          colaPush(cola, v);
        }
        // en los 3 casos (A/D/L) la cinta sigue parada hasta cumplir el
        // minimo de RETARDO_PARADA_SENSOR1_MS (ver E1_EMPUJA).
        est1 = E1_EMPUJA;
      }
      break;
    }

    case E1_EMPUJA:
      // Si hay que empujar: sale del todo -> se queda afuera el tiempo
      // pedido -> vuelve del todo. Cada paso espera a que el servo LLEGUE
      // (objetivo1 < 0) antes de pasar al siguiente, nunca por un timer que
      // podria dispararse antes de que el servo termine de moverse.
      if (empuja1Activo) {
        switch (fase1) {
          case FASE_SALE:
            if (objetivo1 < 0) { t1 = millis(); fase1 = FASE_AFUERA; }
            break;
          case FASE_AFUERA:
            if (millis() - t1 >= RETARDO_EMPUJE_MS) {
              moverA(objetivo1, SERVO1_REPOSO);
              fase1 = FASE_VUELVE;
            }
            break;
          case FASE_VUELVE:
            if (objetivo1 < 0) empuja1Activo = false;
            break;
        }
      }
      if (!empuja1Activo && millis() - tParada1 >= RETARDO_PARADA_SENSOR1_MS) {
        para1 = false;                   // se cumplio el minimo: reanudar faja
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
          tParada2 = millis();          // arranca el minimo de RETARDO_PARADA_SENSOR2_MS
          moverA(objetivo2, SERVO2_EMPUJE);
          empuja2Activo = true;
          fase2 = FASE_SALE;
          est2 = E2_EMPUJA;
        } else {                        // 'A': pasa de largo sin detenerse
          t2 = millis();
          est2 = E2_LIBERA;
        }
      }
      break;

    case E2_EMPUJA:
      // mismo esquema que la estacion 1: espera a que el servo LLEGUE en
      // cada paso, nunca reanuda por un timer que podria ganarle al servo.
      if (empuja2Activo) {
        switch (fase2) {
          case FASE_SALE:
            if (objetivo2 < 0) { t2 = millis(); fase2 = FASE_AFUERA; }
            break;
          case FASE_AFUERA:
            if (millis() - t2 >= RETARDO_EMPUJE_MS) {
              moverA(objetivo2, SERVO2_REPOSO);
              fase2 = FASE_VUELVE;
            }
            break;
          case FASE_VUELVE:
            if (objetivo2 < 0) empuja2Activo = false;
            break;
        }
      }
      if (!empuja2Activo && millis() - tParada2 >= RETARDO_PARADA_SENSOR2_MS) {
        para2 = false;                   // se cumplio el minimo: reanudar faja
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
  // --- Botones fisicos del tablero (hacen lo mismo que S/X/R por serie) ---
  // Se leen SIEMPRE, incluso mientras la estacion 1 espera el veredicto de la
  // PC: si hay un atasco, el STOP tiene que responder en el acto y no
  // quedarse esperando a que conteste la camara.
  if (flancoBoton(PIN_BTN_START, prevStart, mStart)) {
    if (!fajaActiva) { fajaActiva = true; lcdSucio = true; Serial.println(F("#START")); }
  }
  if (flancoBoton(PIN_BTN_STOP, prevStop, mStop))    pararTodo();
  if (flancoBoton(PIN_BTN_RESET, prevReset, mReset)) resetContadores();

  // --- Comandos desde la PC ---
  // Solo se leen cuando NO hay una botella esperando veredicto.
  if (est1 != E1_ESPERA) {
    while (Serial.available()) {
      char c = Serial.read();
      if (c == 'S') { if (!fajaActiva) { fajaActiva = true; lcdSucio = true; Serial.println(F("#START")); } }
      else if (c == 'X') pararTodo();
      else if (c == 'R') resetContadores();
      else if (c == '1') probarServo(servo1, SERVO1_REPOSO, SERVO1_EMPUJE, F("SERVO 1 (pin 10)"));
      else if (c == '2') probarServo(servo2, SERVO2_REPOSO, SERVO2_EMPUJE, F("SERVO 2 (pin 11)"));
      // Prueba de reposo del servo 1 (reposo = 0 en este servo, AL REVES
      // que el servo 2): cada tecla lo manda a un angulo fijo cerca de 0 Y
      // LO DEJA AHI (no vuelve solo) para mirarlo con calma.
      else if (c == '6') probarAngulo(servo1, 10, F("SERVO 1"));
      else if (c == '7') probarAngulo(servo1, 20, F("SERVO 1"));
      else if (c == '8') probarAngulo(servo1, 30, F("SERVO 1"));
      else if (c == '9') probarAngulo(servo1, 40, F("SERVO 1"));
      // Prueba de EMPUJE (salida maxima) de los dos servos: se quedan
      // afuera, no vuelven solos. El servo 1 empuja cerca de 180 (al reves
      // que el servo 2, que empuja cerca de 0).
      else if (c == '3') probarAngulo(servo1, 180, F("SERVO 1 empuje"));
      else if (c == '4') probarAngulo(servo1, 165, F("SERVO 1 empuje"));
      else if (c == '5') probarAngulo(servo2, 0, F("SERVO 2 empuje"));
      else if (c == '0') probarAngulo(servo2, 15, F("SERVO 2 empuje"));
      // cualquier otro byte suelto se descarta
    }
  }

  // --- Estaciones ---
  if (fajaActiva) {
    tareaEstacion1();
    tareaEstacion2();
  }

  // --- Avanzar los empujes automaticos en curso (no bloquea) ---
  avanzarServo(servo1, objetivo1, tPasoServo1);
  avanzarServo(servo2, objetivo2, tPasoServo2);

  // --- Motor: gira solo si la faja esta activa y nadie pide parar ---
  motor(fajaActiva && !para1 && !para2);

  // --- LCD (solo cuando cambio algo: el I2C es lento) ---
  if (lcdSucio) refrescarLcd();
}
