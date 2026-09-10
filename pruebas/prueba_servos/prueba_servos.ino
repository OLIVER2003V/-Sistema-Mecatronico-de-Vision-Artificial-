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
        l  -> un empuje solo del servo L (pin 11)
        d  -> un empuje solo del servo D (pin 10)
        0-180 y Enter -> los dos servos a ese angulo (para buscar REPOSO/EMPUJE)

  Cableado:
    senal servo L -> pin 11         senal servo D -> pin 10
    V+ de los servos -> fuente EXTERNA 5-6 V / >=3 A  (NO el 5V del Arduino)
    GND fuente -> GND servos  Y  GND del Arduino  (todo unido: masa comun)

  Cuando esto funcione, volve a subir  faja_botellas/faja_botellas.ino .
  ============================================================================
*/
#include <Servo.h>

const uint8_t PIN_SERVO_L = 11;
const uint8_t PIN_SERVO_D = 10;

// Los mismos valores que en el firmware. Ajustalos aca si tu paleta necesita
// otro recorrido, y despues copialos a faja_botellas.ino.
const uint8_t SERVO_REPOSO = 20;
const uint8_t SERVO_EMPUJE = 110;

const uint16_t T_EMPUJE_MS = 450;   // cuanto queda afuera la paleta
const uint16_t T_CICLO_MS  = 2000;  // pausa entre ciclos automaticos

Servo servoL;
Servo servoD;

uint32_t tCiclo = 0;
int   numero = -1;   // acumula digitos tecleados por el Monitor Serie

void empuje(Servo &s, const __FlashStringHelper *nombre) {
  Serial.print(F("empuje ")); Serial.println(nombre);
  s.write(SERVO_EMPUJE);
  delay(T_EMPUJE_MS);
  s.write(SERVO_REPOSO);
}

void setup() {
  Serial.begin(9600);
  servoL.attach(PIN_SERVO_L);
  servoD.attach(PIN_SERVO_D);
  servoL.write(SERVO_REPOSO);
  servoD.write(SERVO_REPOSO);
  Serial.println(F("prueba_servos: ciclo cada 2s. Teclas: l  d  o un angulo 0-180 + Enter"));
  tCiclo = millis();
}

void loop() {
  // --- comandos por Serie ---
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'l' || c == 'L') empuje(servoL, F("L (pin 11)"));
    else if (c == 'd' || c == 'D') empuje(servoD, F("D (pin 10)"));
    else if (c >= '0' && c <= '9') {
      numero = (numero < 0 ? 0 : numero) * 10 + (c - '0');
    } else if (c == '\n' || c == '\r') {
      if (numero >= 0) {
        int a = constrain(numero, 0, 180);
        Serial.print(F("angulo ")); Serial.println(a);
        servoL.write(a);
        servoD.write(a);
        numero = -1;
      }
    }
  }

  // --- ciclo automatico ---
  if (millis() - tCiclo >= T_CICLO_MS) {
    Serial.println(F("ciclo: EMPUJE los dos"));
    servoL.write(SERVO_EMPUJE);
    servoD.write(SERVO_EMPUJE);
    delay(T_EMPUJE_MS);
    servoL.write(SERVO_REPOSO);
    servoD.write(SERVO_REPOSO);
    tCiclo = millis();
  }
}
