/*
  ============================================================================
  prueba_servos.ino  ---  Prueba SOLO los 2 servos de la faja (banco, Fase 3)
  ============================================================================
  Sube ESTE sketch (no el firmware) para confirmar cableado y alimentacion
  antes de probar la logica completa.

  Que hace:
    - Al arrancar, los dos servos van a REPOSO (20 grados).
    - Cada ~2 s hacen un ciclo REPOSO -> EMPUJE (110) -> REPOSO.
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

// Los mismos valores que en el firmware. Ajustalos aca si tu paleta necesita
// otro recorrido, y despues copialos a faja_botellas.ino.
const uint8_t SERVO_REPOSO = 20;
const uint8_t SERVO_EMPUJE = 110;

const uint16_t T_EMPUJE_MS = 450;   // cuanto queda afuera la paleta
const uint16_t T_CICLO_MS  = 2000;  // pausa entre ciclos automaticos

Servo servo1;
Servo servo2;

uint32_t tCiclo = 0;
int numero = -1;   // acumula digitos tecleados por el Monitor Serie

void empuje(Servo &s, const __FlashStringHelper *nombre) {
  Serial.print(F("empuje ")); Serial.println(nombre);
  s.write(SERVO_EMPUJE);
  delay(T_EMPUJE_MS);
  s.write(SERVO_REPOSO);
}

void setup() {
  Serial.begin(9600);
  servo1.attach(PIN_SERVO_1);
  servo2.attach(PIN_SERVO_2);
  servo1.write(SERVO_REPOSO);
  servo2.write(SERVO_REPOSO);
  Serial.println(F("prueba_servos: ciclo cada 2s. Teclas: d  l  o un angulo 0-180 + Enter"));
  tCiclo = millis();
}

void loop() {
  // --- comandos por Serie ---
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'd' || c == 'D') empuje(servo1, F("SERVO 1 (pin 10)"));
    else if (c == 'l' || c == 'L') empuje(servo2, F("SERVO 2 (pin 11)"));
    else if (c >= '0' && c <= '9') {
      numero = (numero < 0 ? 0 : numero) * 10 + (c - '0');
    } else if (c == '\n' || c == '\r') {
      if (numero >= 0) {
        int a = constrain(numero, 0, 180);
        Serial.print(F("angulo ")); Serial.println(a);
        servo1.write(a);
        servo2.write(a);
        numero = -1;
      }
    }
  }

  // --- ciclo automatico ---
  if (millis() - tCiclo >= T_CICLO_MS) {
    Serial.println(F("ciclo: EMPUJE los dos"));
    servo1.write(SERVO_EMPUJE);
    servo2.write(SERVO_EMPUJE);
    delay(T_EMPUJE_MS);
    servo1.write(SERVO_REPOSO);
    servo2.write(SERVO_REPOSO);
    tCiclo = millis();
  }
}
