// Colores de los graficos, en un solo lugar para que las dos vistas de la
// misma serie no se pinten distinto.
//
// Azul/naranja en vez del verde/rojo "obvio": verde y rojo son el par que
// NO distingue el daltonismo deuterano (~8% de los hombres). Verificado con
// el validador de paletas sobre esta misma superficie:
//   aprobadas vs rechazadas -> ΔE 26.8 (protan), 32.4 (tritan). Pasa.
// Si se cambian estos valores hay que volver a validarlos.
//
// El semaforo verde/ambar/rojo se sigue usando en los contadores y las
// insignias, pero ahi el color nunca va solo: lleva icono y texto.

export const SUPERFICIE = '#16202f' // slate-800/40 sobre slate-900

export const SERIE = {
  aprobadas: '#3987e5',
  rechazadas: '#d95926',
}

export const TINTA = {
  principal: '#e2e8f0',
  secundaria: '#94a3b8',
  grilla: '#1e293b',
}

// Barras del Pareto de defectos: una sola rampa (el largo de la barra ya
// dice la magnitud; el color no tiene que repetirlo).
export const RAMPA_DEFECTO = ['#3987e5', '#2a78d6', '#256abf', '#1c5cab']
