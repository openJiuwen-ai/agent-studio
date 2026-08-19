import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: ['export-provider.spec.ts','export-model-only.spec.ts','import-provider.spec.ts','import-model-only.spec.ts','import-conflict-cover.spec.ts','file-type-guard.spec.ts','cross-env-linkage.spec.ts','cross-ws-real.spec.ts'],
  fullyParallel: false,
  forbidOnly: false,
  retries: 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: 'http://127.0.0.1:4200/openjiuwen/',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    actionTimeout: 30_000,
    navigationTimeout: 60_000,
  },
  timeout: 180_000,
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1440, height: 900 },
        locale: 'zh-CN',
      },
    },
  ],
});
