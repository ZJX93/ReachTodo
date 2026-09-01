import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  // 单体部署：构建产物输出到 dist/，由根 Dockerfile 拷入 server/public，
  // 最终由 FastAPI 在单端口(8000)同源托管。
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
