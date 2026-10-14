import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['painel.makeraddon.online'],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true
      },
      // Nova rota mágica para o Agente Core:
      '/chat': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})