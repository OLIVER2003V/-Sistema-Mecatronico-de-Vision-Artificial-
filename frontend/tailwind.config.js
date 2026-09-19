/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      keyframes: {
        // Entrada de los avisos (esquina inferior derecha).
        entrar: {
          from: { opacity: '0', transform: 'translateY(0.75rem)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        // Barrido de los esqueletos de carga.
        brillo: {
          '100%': { transform: 'translateX(100%)' },
        },
      },
      animation: {
        entrar: 'entrar 180ms ease-out',
        brillo: 'brillo 1.4s infinite',
      },
    },
  },
  plugins: [],
}
