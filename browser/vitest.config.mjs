import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    // `.tsx` too: a `.ts`-only glob silently runs none of the component suites.
    include: ['src/**/*.test.{ts,tsx}'],
    exclude: ['node_modules', 'dist'],
    setupFiles: ['./vitest.setup.ts'],
    // Don't fail on uncaught exceptions from intentional error tests
    dangerouslyIgnoreUnhandledErrors: true,
    // Pool configuration to reduce memory usage
    pool: 'threads',
    maxConcurrency: 2,
    // Vitest's 'basic' reporter is deprecated; this is its equivalent
    reporters: [
      ['default', { summary: false }]
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'json-summary', 'html', 'lcov', 'cobertura'],
      exclude: [
        'node_modules/',
        'dist/',
        'build/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/__tests__/**',
        '**/*.test.ts',
        '**/*.test.tsx',
        '**/*.spec.ts',
        '**/*.spec.tsx',
        '**/test/**',
        '**/tests/**',
        '**/examples/**',
        '**/demo/**',
        '**/index.ts',
        '**/types.ts',
        'vitest.setup.ts',
        '**/public/**',
        'scripts/**',
      ],
    },
    typecheck: {
      tsconfig: './tsconfig.test.json'
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
