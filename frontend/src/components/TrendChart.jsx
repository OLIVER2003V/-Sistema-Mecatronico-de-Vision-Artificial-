// Aprobadas vs rechazadas por hora (barras apiladas: parte-de-un-todo).
//
// Colores: ver ui/colores.js. Azul y naranja, NO verde y rojo, porque ese par
// es indistinguible para el daltonismo mas comun. Ademas hay leyenda y una
// tabla equivalente para lectores de pantalla, asi que la identidad de la
// serie nunca depende solo del color.
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js'
import { TrendingUp } from 'lucide-react'
import { Bar } from 'react-chartjs-2'

import EstadoVacio from './ui/EstadoVacio.jsx'
import Tarjeta from './ui/Tarjeta.jsx'
import { SERIE, SUPERFICIE, TINTA } from './ui/colores.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend)

export default function TrendChart({ tendencia }) {
  const puntos = tendencia ?? []

  if (puntos.length === 0) {
    return (
      <Tarjeta titulo="Produccion por hora" icono={TrendingUp}>
        <EstadoVacio
          icono={TrendingUp}
          titulo="Todavia no hay datos suficientes"
          mensaje="La tendencia se arma con las botellas del lote en curso, agrupadas por hora."
        />
      </Tarjeta>
    )
  }

  const comun = {
    borderColor: SUPERFICIE, // separa los segmentos apilados con 2px de superficie
    borderWidth: { top: 2, right: 0, bottom: 0, left: 0 },
    borderRadius: 4,
    borderSkipped: false,
    maxBarThickness: 44,
  }

  const data = {
    labels: puntos.map((p) => p.hora),
    datasets: [
      { label: 'Aprobadas', data: puntos.map((p) => p.aceptadas), backgroundColor: SERIE.aprobadas, ...comun },
      { label: 'Rechazadas', data: puntos.map((p) => p.rechazadas), backgroundColor: SERIE.rechazadas, ...comun },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    scales: {
      x: {
        stacked: true,
        ticks: { color: TINTA.secundaria },
        grid: { display: false },
        border: { color: TINTA.grilla },
      },
      y: {
        stacked: true,
        beginAtZero: true,
        ticks: { color: TINTA.secundaria, precision: 0 },
        grid: { color: TINTA.grilla },
        border: { display: false },
      },
    },
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: TINTA.principal, usePointStyle: true, pointStyle: 'rectRounded', padding: 16 },
      },
      tooltip: {
        backgroundColor: '#0f172a',
        borderColor: '#334155',
        borderWidth: 1,
        padding: 10,
        titleColor: TINTA.principal,
        bodyColor: TINTA.principal,
        callbacks: {
          title: (items) => `Hora ${items[0].label}`,
          footer: (items) => {
            const total = items.reduce((suma, i) => suma + i.parsed.y, 0)
            return `Total: ${total} botellas`
          },
        },
      },
    },
  }

  return (
    <Tarjeta titulo="Produccion por hora" icono={TrendingUp}>
      <div className="h-64">
        <Bar data={data} options={options} aria-label="Botellas aprobadas y rechazadas por hora" />
      </div>

      {/* Mismos datos en texto: el <canvas> no lo lee un lector de pantalla. */}
      <table className="sr-only">
        <caption>Botellas aprobadas y rechazadas por hora</caption>
        <thead>
          <tr>
            <th>Hora</th>
            <th>Aprobadas</th>
            <th>Rechazadas</th>
          </tr>
        </thead>
        <tbody>
          {puntos.map((p) => (
            <tr key={p.hora}>
              <td>{p.hora}</td>
              <td>{p.aceptadas}</td>
              <td>{p.rechazadas}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Tarjeta>
  )
}
