import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import svgr from 'vite-plugin-svgr'
import path from 'path'

export default defineConfig(({ command, mode }) => {
  const envDir = path.resolve(__dirname, '..')

  const env = loadEnv(mode, envDir, '')
  return {
    envDir: envDir,
    plugins: [react(), svgr()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@test-agentstudio/workflow-canvas': path.resolve(__dirname, './packages/workflow-canvas/src'),
        '@test-agentstudio/api-client': path.resolve(__dirname, './packages/api-client/src'),
        '@test-agentstudio/base-ui': path.resolve(__dirname, './packages/base-ui/src'),
      },
    },
    server: {
      port: parseInt(env.FRONTEND_PORT) || 3000,
      host: env.HOST || '0.0.0.0',
      proxy: {
        '/api': {
          target: env.VITE_API_PROXY_TARGET || (process.env.DOCKER_ENV === 'true' ? 'http://jiuwen-backend:8000' : 'http://localhost:8000'),
          changeOrigin: true,
          rewrite: path => path.replace(/^\/api/, '/api'),
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      chunkSizeWarningLimit: 5000,
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: mode === 'production',
          drop_debugger: mode === 'production',
        },
      },
      rollupOptions: {
        output: {
          manualChunks(id) {
            // Group all workflow-canvas form-materials modules into the same chunk
            // to avoid circular dependency warnings from re-exports
            if (id.includes('/packages/workflow-canvas/src/form-materials/')) {
              return 'workflow-canvas-form-materials'
            }
          },
        },
      },
    },
    define: {
      __APP_VERSION__: JSON.stringify(env.npm_package_version || '1.0.0'),
      __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
    },
  }
})
