import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  define: {
    // Baked into bundle so you can confirm CloudFront/S3 is serving a fresh build (see AI Assistant footer).
    __CDSS_BUILD_STAMP__: JSON.stringify(new Date().toISOString()),
  },
  plugins: [react(), tailwindcss()],
  server: {
    hmr: true,
  },
  optimizeDeps: {
    force: false,
  },
})
