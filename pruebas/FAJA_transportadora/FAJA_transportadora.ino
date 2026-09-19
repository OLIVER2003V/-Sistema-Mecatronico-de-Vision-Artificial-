#include <Servo.h> 
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27,16,2);
Servo SERVO_1;
Servo SERVO_2;

#define PIST_G  11
#define PIST_P  10
#define MOTOR   9
#define SEN_G   8
#define SEN_M   7
#define SEN_P   6
#define START   3
#define STOP    4
#define RESET   5

bool cond_inicio = 0;
int tiempo_espera = 300;
int cant_g = 0;
int cant_m = 0;
int cant_p = 0;
char dato_lcd1[20];
char dato_lcd2[20];
char dato_lcd3[20];

// Botones fisicos ANULADOS: arranca por tecla 's' (o 'S') desde el Monitor Serie.
void inicio_s(){
  if (Serial.available()) {
    char c = Serial.read();
    if (c == 's' || c == 'S') {
      cond_inicio = 1;
      lcd.clear();
      lcd.setCursor(0,0);
      lcd.print("Iniciando");
      lcd.setCursor(0,1);
      lcd.print("Proceso"); delay(500); lcd.print("."); delay(500); lcd.print("."); delay(500); lcd.print(".");
      delay(1000);
      lcd.clear();
    }
  }
}

void datos_faja(){
  sprintf(dato_lcd1, "G:%03d ", cant_g); lcd.setCursor(0,0); lcd.print(dato_lcd1);
  sprintf(dato_lcd2, "M:%03d ", cant_m); lcd.setCursor(10,0); lcd.print(dato_lcd2);
  sprintf(dato_lcd3, "P:%03d ", cant_p); lcd.setCursor(0,1); lcd.print(dato_lcd3);
}

void setup() {
  Serial.begin(9600);
  SERVO_1.attach(PIST_G);
  SERVO_2.attach(PIST_P);
  pinMode(MOTOR, OUTPUT);
  pinMode(SEN_G, INPUT);
  pinMode(SEN_M, INPUT);
  pinMode(SEN_P, INPUT);
  // START/STOP/RESET fisicos anulados: ahora se manejan por Monitor Serie
  // (9600), no hace falta pinMode en esos pines.
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0,0);
  lcd.print("  Clasificador");
  digitalWrite(MOTOR, LOW);
  SERVO_1.write(180);
  SERVO_2.write(180);
  delay(1000);
  lcd.clear();
  Serial.println(F("Teclas: s=start x=stop r=reset"));
}

void loop() {
  lcd.setCursor(0,0);
  lcd.print("  Clasificador");
  lcd.setCursor(0,1);
  lcd.print(">>Tecla 's'<<");
  inicio_s();
  while(cond_inicio == 1){
    datos_faja();
    digitalWrite(MOTOR, HIGH);
    if(digitalRead(SEN_G) == LOW){
      delay(20);
      if(digitalRead(SEN_G) == LOW){
        cant_g++;
        delay(tiempo_espera);
        digitalWrite(MOTOR, LOW);
        SERVO_1.write(0);
        delay(2000);
        SERVO_1.write(180);
        delay(2000);
        digitalWrite(MOTOR, HIGH);
      }
      do{
        while(digitalRead(SEN_G) == LOW);
        delay(20);
      }
      while(digitalRead(SEN_G) == LOW);
    }

    if(digitalRead(SEN_M) == LOW){
      delay(20);
      if(digitalRead(SEN_M) == LOW){
        cant_m++;
        delay(tiempo_espera);
        digitalWrite(MOTOR, LOW);
        SERVO_2.write(0);
        delay(2000);
        SERVO_2.write(180);
        delay(2000);
        digitalWrite(MOTOR, HIGH);
      }
      do{
        while(digitalRead(SEN_M) == LOW);
        delay(20);
      }
      while(digitalRead(SEN_M) == LOW);
    }

    if(digitalRead(SEN_P) == LOW){
      delay(20);
      if(digitalRead(SEN_P) == LOW){
        cant_p++;
      }
      do{
        while(digitalRead(SEN_P) == LOW);
        delay(20);
      }
      while(digitalRead(SEN_P) == LOW);
    }

    // STOP/RESET fisicos anulados: tecla 'x' = stop, 'r' = reset.
    if (Serial.available()) {
      char c = Serial.read();
      if (c == 'x' || c == 'X') {
        digitalWrite(MOTOR, LOW);
        cond_inicio = 0;
        lcd.clear();
        lcd.setCursor(0,0);
        lcd.print("Stop Process");
        delay(1200);
        lcd.clear();
      } else if (c == 'r' || c == 'R') {
        digitalWrite(MOTOR, LOW);
        cant_g = 0;
        cant_m = 0;
        cant_p = 0;
      }
    }
  }
}
