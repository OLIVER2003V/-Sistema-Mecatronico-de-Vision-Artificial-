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

// Cola circular chica (6 lugares) de veredictos 'A' / 'E' / 'D'.
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
enum EstCam { CAM_BUSCA, CAM_CENTRA, CAM_ESPERA, CAM_LIBERA };
enum EstSrv { SRV_BUSCA, SRV_CENTRA, SRV_EMPUJA, SRV_LIBERA };

#endif  // TIPOS_H
