import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'production-content-security-policy',
      apply: 'build',
      transformIndexHtml() {
        return [{
          tag: 'meta',
          attrs: {
            'http-equiv': 'Content-Security-Policy',
            content: "script-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'",
          },
          injectTo: 'head-prepend',
        }];
      },
    },
  ],
  server: {
    port: 5175,
    proxy: {
      '/api': {
        target: 'http://localhost:5009',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
});
