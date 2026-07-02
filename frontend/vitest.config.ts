import path from 'node:path'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'node',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: [
      'src/pages/Apps/components/ReportPanel/editor/**/*.test.ts',
      'src/pages/Apps/components/DeepSearchExplorer/**/*.test.ts',
      'src/pages/Apps/utils/**/*.test.ts',
    ],
  },
})
