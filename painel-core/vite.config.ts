import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    allowedHosts: ['painel.makeraddon.online', '.makeraddon.online'],
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/chat': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/agentes': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/chats': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/transcrever': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/bridge': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
