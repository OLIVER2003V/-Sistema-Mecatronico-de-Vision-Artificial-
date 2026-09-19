import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App.jsx'
import { ProveedorAvisos } from './hooks/useAvisos.jsx'
import { ProveedorSesion } from './hooks/useSesion.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      {/* Los avisos van por fuera de la sesion: el login tambien los usa. */}
      <ProveedorAvisos>
        <ProveedorSesion>
          <App />
        </ProveedorSesion>
      </ProveedorAvisos>
    </BrowserRouter>
  </React.StrictMode>,
)
