/*
  tipos.h  ---  Tipos y estructuras del firmware de la faja.

  Van en un .h aparte a proposito: si estos tipos estuvieran en el .ino, el
  generador automatico de prototipos del compilador de Arduino pondria las
  declaraciones de las funciones ANTES de estos tipos y no compilaria
  (error "does not name a type"). En un header incluido al principio, el
  compilador ya conoce los tipos cuando genera los prototipos.
*/
#ifndef TIPOS_H
#define TIPOS_H

#include <Arduino.h>

// Cola circular chica (6 lugares) de veredictos que van de la estacion 1 a la 2.
// Solo lleva 'A' y 'L'  ('D' se expulsa en la estacion 1, nunca entra a la cola).
// Sin memoria dinamica: entra entera en la RAM del UNO.
struct Cola {
  char dato[6];
  uint8_t cabeza;
  uint8_t cantidad;
};

inline void colaPush(Cola &c, char v) {
  if (c.cantidad < 6) { c.dato[(c.cabeza + c.cantidad) % 6] = v; c.cantidad++; }
}
inline char colaFrente(const Cola &c) {
  return c.cantidad ? c.dato[c.cabeza] : 0;
}
inline void colaPop(Cola &c) {
  if (c.cantidad) { c.cabeza = (c.cabeza + 1) % 6; c.cantidad--; }
}
inline void colaVaciar(Cola &c) { c.cabeza = 0; c.cantidad = 0; }

// Sub-estados de cada estacion (maquinas de estados no bloqueantes).
//   Estacion 1: busca -> centra -> espera veredicto de la PC -> (empuja si 'D') -> libera
//   Estacion 2: busca -> centra -> (empuja si 'L') -> libera
enum Est1  { E1_BUSCA, E1_CENTRA, E1_ESPERA, E1_EMPUJA, E1_LIBERA };
enum Est2  { E2_BUSCA, E2_CENTRA, E2_EMPUJA, E2_LIBERA };

#endif  // TIPOS_H
