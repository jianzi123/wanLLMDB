import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { existsSync } from 'fs'

/**
 * Determine the backend proxy target based on the runtime environment
 * Priority:
 * 1. VITE_PROXY_TARGET (explicit override)
 * 2. K8s: Use service name from env or default
 * 3. Docker Compose: Use service name 'backend'
 * 4. Local development: Use localhost
 */
function getProxyTarget(): string {
  // Explicit override (highest priority)
  if (process.env.VITE_PROXY_TARGET) {
    return process.env.VITE_PROXY_TARGET
  }

  // Kubernetes environment
  // K8s services are typically accessible via service name in the same namespace
  if (process.env.KUBERNETES_SERVICE_HOST || process.env.K8S_SERVICE_NAME) {
    const k8sService = process.env.K8S_SERVICE_NAME || 'wanllmdb-backend'
    const k8sPort = process.env.K8S_SERVICE_PORT || '8000'
    return `http://${k8sService}:${k8sPort}`
  }

  // Docker Compose environment
  // Check if running in Docker (has /.dockerenv or DOCKER env var)
  if (process.env.DOCKER || existsSync('/.dockerenv')) {
    // In Docker Compose, use service name
    const dockerService = process.env.DOCKER_SERVICE_NAME || 'backend'
    const dockerPort = process.env.DOCKER_SERVICE_PORT || '8000'
    return `http://${dockerService}:${dockerPort}`
  }

  // Local development (default)
  const localPort = process.env.BACKEND_PORT || '8000'
  return `http://localhost:${localPort}`
}

const proxyTarget = getProxyTarget()
console.log(`[Vite] Proxy target: ${proxyTarget}`)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@features': path.resolve(__dirname, './src/features'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@services': path.resolve(__dirname, './src/services'),
      '@store': path.resolve(__dirname, './src/store'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@types': path.resolve(__dirname, './src/types'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
      },
      '/ws': {
        target: proxyTarget.replace('http://', 'ws://'),
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'redux-vendor': ['@reduxjs/toolkit', 'react-redux'],
          'antd-vendor': ['antd', '@ant-design/icons'],
          'chart-vendor': ['recharts', 'plotly.js', 'react-plotly.js'],
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
})
