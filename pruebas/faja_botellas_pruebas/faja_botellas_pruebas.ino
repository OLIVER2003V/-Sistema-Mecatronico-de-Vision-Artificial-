/*
  ============================================================================
  faja_botellas_pruebas.ino  ---  PRUEBA: motor + START/STOP/RESET + servos
  ============================================================================
  Sensores y LCD no incluidos (no hacen falta para esta prueba). Sirve para
  probar aislado: el motor arranca/para con START/STOP/RESET, y los 2 servos
  se pueden mover a mano por el Monitor Serie para calibrar sus angulos.

  Botones fisicos ANULADOS: START/STOP/RESET van solo por el Monitor Serie
  (9600 baudios): s/S = start, x/X = stop, r/R = reset.

  Teclas de los servos (Monitor Serie):
    1 = servo1: empuja y vuelve a reposo (ciclo completo)
    2 = servo2: empuja y vuelve a reposo (ciclo completo)
    6/7/8/9 = servo1 a un angulo fijo cerca de REPOSO (se queda ahi)
    3/4     = servo1 a un angulo fijo cerca de EMPUJE  (se queda ahi)
    5/0     = servo2 a un angulo fijo cerca de EMPUJE  (se queda ahi)

  PINES (los mismos que en el firmware real):
     9  modulo rele -> motor de la faja
     3  boton START   4  boton STOP   5  boton RESET
    10  servo 1       11  servo 2
  ============================================================================
*/
#include <Servo.h>

// Muchos modulos rele azules se activan con LOW, pero en esta placa el rele
// prende con HIGH.
const uint8_t RELE_ENCENDIDO = HIGH;

const uint8_t PIN_RELE      = 9;
// PIN_BTN_START/STOP/RESET (3/4/5) ya no se leen: botones fisicos anulados,
// se dejan solo como referencia de cableado.
const uint8_t PIN_SERVO_1   = 10;
const uint8_t PIN_SERVO_2   = 11;

// Mismos valores de referencia que faja_botellas.ino. Si aca encontras los
// angulos correctos, copialos alla.
const uint8_t SERVO1_REPOSO = 180;
const uint8_t SERVO1_EMPUJE = 0;
const uint8_t SERVO2_REPOSO = 180;
const uint8_t SERVO2_EMPUJE = 0;

const uint16_t RETARDO_EMPUJE_MS = 450;   // cuanto queda afuera la paleta (ciclo '1'/'2')
const uint8_t  SERVO_PASO_GRADOS = 4;     // "velocidad": grados por paso...
const uint16_t SERVO_PASO_MS     = 15;    // ...y ms entre paso y paso

bool fajaActiva = false;

Servo servo1;
Servo servo2;

void motor(bool encender) {
  if (encender) digitalWrite(PIN_RELE, RELE_ENCENDIDO);
  else          digitalWrite(PIN_RELE, RELE_ENCENDIDO == HIGH ? LOW : HIGH);
}

void arrancar() {
  if (!fajaActiva) {
    fajaActiva = true;
    Serial.println(F("#START: cinta girando"));
  }
}

void pararTodo() {
  if (fajaActiva) {
    fajaActiva = false;
    Serial.println(F("#STOP: cinta detenida"));
  }
}

void resetear() {
  fajaActiva = false;
  Serial.println(F("#RESET: cinta detenida (nada que contar en esta prueba)"));
}

// Mueve el servo grado a grado (no de un salto) y siempre termina
// exactamente en 'objetivo'. Usa delay(): es solo para estas pruebas
// manuales, no corre con la faja en marcha.
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

// Tecla '1'/'2': ciclo completo (empuja, espera, vuelve).
void probarServo(Servo &s, uint8_t reposo, uint8_t empuje, const __FlashStringHelper *nombre) {
  Serial.print(F("#prueba ")); Serial.println(nombre);
  moverGradual(s, empuje);
  delay(RETARDO_EMPUJE_MS);
  moverGradual(s, reposo);
}

// Teclas de angulo fijo: mueve y DEJA el servo ahi (no vuelve solo), para
// mirarlo con calma y decidir el angulo correcto.
void probarAngulo(Servo &s, uint8_t angulo, const __FlashStringHelper *nombre) {
  Serial.print(F("#angulo ")); Serial.print(nombre);
  Serial.print(F(" -> ")); Serial.println(angulo);
  moverGradual(s, angulo);
}

void setup() {
  // Apagar el rele es lo PRIMERO que hace el sketch, antes que nada mas,
  // para minimizar la ventana en la que el pin queda flotando mientras
  // arranca el bootloader.
  pinMode(PIN_RELE, OUTPUT);
  motor(false);

  servo1.attach(PIN_SERVO_1);
  servo2.attach(PIN_SERVO_2);
  servo1.write(SERVO1_REPOSO);
  servo2.write(SERVO2_REPOSO);

  Serial.begin(9600);
  Serial.println(F("#LISTO: cinta detenida."));
  Serial.println(F("#Teclas: s=start x=stop r=reset (botones fisicos anulados)"));
  Serial.println(F("#Servos: 1=ciclo serv1 2=ciclo serv2"));
  Serial.println(F("#Servo1 fijo: 6/7/8/9=cerca reposo  3/4=cerca empuje"));
  Serial.println(F("#Servo2 fijo: 5/0=cerca empuje"));
}

void loop() {
  // --- Teclas por el Monitor Serie (unica entrada: botones fisicos anulados) ---
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 's' || c == 'S') arrancar();
    else if (c == 'x' || c == 'X') pararTodo();
    else if (c == 'r' || c == 'R') resetear();
    else if (c == '1') probarServo(servo1, SERVO1_REPOSO, SERVO1_EMPUJE, F("SERVO 1 (pin 10)"));
    else if (c == '2') probarServo(servo2, SERVO2_REPOSO, SERVO2_EMPUJE, F("SERVO 2 (pin 11)"));
    else if (c == '6') probarAngulo(servo1, 170, F("SERVO 1"));
    else if (c == '7') probarAngulo(servo1, 160, F("SERVO 1"));
    else if (c == '8') probarAngulo(servo1, 150, F("SERVO 1"));
    else if (c == '9') probarAngulo(servo1, 140, F("SERVO 1"));
    else if (c == '3') probarAngulo(servo1, 0,  F("SERVO 1 empuje"));
    else if (c == '4') probarAngulo(servo1, 15, F("SERVO 1 empuje"));
    else if (c == '5') probarAngulo(servo2, 0,  F("SERVO 2 empuje"));
    else if (c == '0') probarAngulo(servo2, 15, F("SERVO 2 empuje"));
  }

  motor(fajaActiva);
}
