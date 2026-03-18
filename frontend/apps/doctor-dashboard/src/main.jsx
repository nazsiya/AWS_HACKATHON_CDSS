import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { validateEnv } from './api/config'
import './index.css'
import App from './App.jsx'

validateEnv()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
