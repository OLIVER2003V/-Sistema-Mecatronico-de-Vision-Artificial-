import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// En dev (npm run dev), el proxy manda /api y /ws al backend en :8000.
// En produccion (Docker), el mismo trabajo lo hace nginx.conf.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
      // Las fotos de la galeria de mermas las sirve Django (o S3 en la nube).
      '/media': 'http://localhost:8000',
    },
  },
})
