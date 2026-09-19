/*
  ============================================================================
  prueba_servos.ino  ---  Prueba SOLO los 2 servos de la faja (banco, Fase 3)
  ============================================================================
  Sube ESTE sketch (no el firmware) para confirmar cableado y alimentacion
  antes de probar la logica completa.

  Que hace:
    - Al arrancar, los dos servos van a REPOSO (180 grados, completamente
      retraidos en este montaje; ver nota de SERVO1_REPOSO mas abajo).
    - Cada ~2 s hacen un ciclo REPOSO -> EMPUJE (0) -> REPOSO, moviendose
      grado a grado (no de un salto) para poder controlar la velocidad.
    - Por el Monitor Serie (9600) podes mandar:
        d  -> un empuje del SERVO 1 (pin 10, expulsa defectos 'D')
        l  -> un empuje del SERVO 2 (pin 11, expulsa llenado bajo 'L')
        0-180 y Enter -> los dos servos a ese angulo (para buscar REPOSO/EMPUJE)

  Cableado:
    senal servo 1 -> pin 10        senal servo 2 -> pin 11
    V+ de los servos -> fuente EXTERNA 5-6 V / >=3 A  (NO el 5V del Arduino)
    GND fuente -> GND servos  Y  GND del Arduino  (todo unido: masa comun)

  Cuando esto funcione, volve a subir  faja_botellas/faja_botellas.ino .
  ============================================================================
*/
#include <Servo.h>

const uint8_t PIN_SERVO_1 = 10;   // defecto fisico  (estacion 1)
const uint8_t PIN_SERVO_2 = 11;   // llenado bajo    (estacion 2)

// Los mismos valores que en el firmware, un par por servo: en este montaje
// REPOSO=180 es el retraido y EMPUJE=0 el estirado del todo. Si al mandar
// "empuje" alguno se retrae en vez de estirarse, es que su horn quedo
// montado al reves -- invertile SOLO a ese servo REPOSO y EMPUJE. Usa las
// teclas 0-180+Enter (mandan el mismo angulo a los dos) para ir probando,
// y despues copia los valores finales a faja_botellas.ino.
const uint8_t SERVO1_REPOSO = 180;
const uint8_t SERVO1_EMPUJE = 0;
const uint8_t SERVO2_REPOSO = 180;
const uint8_t SERVO2_EMPUJE = 0;

// "Velocidad" del movimiento: en vez de saltar de un angulo a otro de una,
// avanza de a SERVO_PASO_GRADOS cada SERVO_PASO_MS. Mas grados o menos ms =
// mas rapido; menos grados o mas ms = mas lento y suave.
const uint8_t  SERVO_PASO_GRADOS = 4;
const uint16_t SERVO_PASO_MS     = 15;

const uint16_t T_EMPUJE_MS = 450;   // cuanto queda afuera la paleta
const uint16_t T_CICLO_MS  = 2000;  // pausa entre ciclos automaticos

Servo servo1;
Servo servo2;

uint32_t tCiclo = 0;
int numero = -1;   // acumula digitos tecleados por el Monitor Serie

// Mueve el servo grado a grado (no de un salto) y siempre termina
// exactamente en 'objetivo': se estira o retrae del todo.
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

void empuje(Servo &s, uint8_t reposo, uint8_t empuje_ang, const __FlashStringHelper *nombre) {
  Serial.print(F("empuje ")); Serial.println(nombre);
  moverGradual(s, empuje_ang);
  delay(T_EMPUJE_MS);
  moverGradual(s, reposo);
}

void setup() {
  Serial.begin(9600);
  servo1.attach(PIN_SERVO_1);
  servo2.attach(PIN_SERVO_2);
  servo1.write(SERVO1_REPOSO);
  servo2.write(SERVO2_REPOSO);
  Serial.println(F("prueba_servos: ciclo cada 2s. Teclas: d  l  o un angulo 0-180 + Enter"));
  tCiclo = millis();
}

void loop() {
  // --- comandos por Serie ---
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'd' || c == 'D') empuje(servo1, SERVO1_REPOSO, SERVO1_EMPUJE, F("SERVO 1 (pin 10)"));
    else if (c == 'l' || c == 'L') empuje(servo2, SERVO2_REPOSO, SERVO2_EMPUJE, F("SERVO 2 (pin 11)"));
    else if (c >= '0' && c <= '9') {
      numero = (numero < 0 ? 0 : numero) * 10 + (c - '0');
    } else if (c == '\n' || c == '\r') {
      if (numero >= 0) {
        int a = constrain(numero, 0, 180);
        Serial.print(F("angulo ")); Serial.println(a);
        moverGradual(servo1, a);
        moverGradual(servo2, a);
        numero = -1;
      }
    }
  }

  // --- ciclo automatico ---
  if (millis() - tCiclo >= T_CICLO_MS) {
    Serial.println(F("ciclo: EMPUJE los dos"));
    moverGradual(servo1, SERVO1_EMPUJE);
    moverGradual(servo2, SERVO2_EMPUJE);
    delay(T_EMPUJE_MS);
    moverGradual(servo1, SERVO1_REPOSO);
    moverGradual(servo2, SERVO2_REPOSO);
    tCiclo = millis();
  }
}
