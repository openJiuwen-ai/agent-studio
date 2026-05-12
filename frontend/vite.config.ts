import { defineConfig, loadEnv, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import svgr from 'vite-plugin-svgr'
import path from 'path'
import fs from 'fs'

/**
 * date-fns-tz@1.x ESM files deep-import date-fns v2 paths.
 * npm hoists date-fns@3 which breaks resolution, and the CJS copies of date-fns@2
 * don't provide proper ES default exports that the browser can consume.
 * Redirect all date-fns imports coming from inside date-fns-tz to a date-fns@2 ESM build.
 * Prefer the copy bundled with @douyinfe/semi-foundation, but fall back to top-level
 * date-fns when npm dedupes nested dependencies.
 */
function dateFns2ForDateFnsTz(): Plugin {
  const candidateDateFnsEsmRoots = [
    path.resolve(__dirname, 'node_modules/@douyinfe/semi-foundation/node_modules/date-fns/esm'),
    path.resolve(__dirname, 'node_modules/date-fns/esm'),
  ]

  const dateFnsEsmRoot = candidateDateFnsEsmRoots.find(root => fs.existsSync(root))
  return {
    name: 'datefns2-for-datefns-tz',
    enforce: 'pre',
    resolveId(source, importer) {
      if (!dateFnsEsmRoot) {
        return null
      }
      if (!importer || !importer.includes(`${path.sep}date-fns-tz${path.sep}`)) {
        return null
      }
      if (source === 'date-fns') {
        const main = path.join(dateFnsEsmRoot, 'index.js')
        return fs.existsSync(main) ? main : null
      }
      if (source.startsWith('date-fns/')) {
        const rel = source.slice('date-fns/'.length)
        const resolved = path.join(dateFnsEsmRoot, rel)
        return fs.existsSync(resolved) ? resolved : null
      }
      return null
    },
  }
}

export default defineConfig(({ command, mode }) => {
  const envDir = path.resolve(__dirname, '..')

  const env = loadEnv(mode, envDir, '')
  return {
    envDir: envDir,
    plugins: [dateFns2ForDateFnsTz(), react(), svgr()],
    optimizeDeps: {
      // date-fns-tz@1.x deep-imports date-fns internals; pre-bundling with hoisted date-fns@3 breaks.
      exclude: ['date-fns-tz'],
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@test-agentstudio/workflow-canvas': path.resolve(__dirname, './packages/workflow-canvas/src'),
        '@test-agentstudio/api-client': path.resolve(__dirname, './packages/api-client/src'),
        '@test-agentstudio/base-ui': path.resolve(__dirname, './packages/base-ui/src'),
        // Force ESM entry for date-fns-tz: its package.json "exports" maps "." to the CJS
        // index.js (overriding the "module" field), so named ESM imports fail in the browser.
        'date-fns-tz': path.resolve(__dirname, 'node_modules/date-fns-tz/esm/index.js'),
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
