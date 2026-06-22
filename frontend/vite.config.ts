import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  cacheDir: 'D:/tmp/knowbase-vite-cache-v4',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // SSE 流式响应：禁用代理缓冲
        configure: (proxy) => {
          proxy.on('proxyReq', (_proxyReq, _req, res) => {
            // 禁用 Nagle 算式，立即发送每个 chunk
            res.socket?.setNoDelay(true)
          })
          proxy.on('proxyRes', (proxyRes, _req, res) => {
            // 关闭代理层缓冲，立即转发数据
            res.socket?.setNoDelay(true)
            // 移除可能导致缓冲的 header
            delete proxyRes.headers['content-length']
            proxyRes.headers['x-accel-buffering'] = 'no'
          })
        },
      },
    },
  },
})
