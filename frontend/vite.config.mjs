import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  plugins: [
    react(),
    tailwindcss({
      theme: {
        extend: {
          colors: {
            shopifyPurple: '#5c6ac4',
          },
        },
      },
      // You can add more Tailwind options here if needed
    }),
  ],
  server: {
    historyApiFallback: true, // SPA fallback for React Router
    port: 5173,
    open: true,
    host: '0.0.0.0',
    allowedHosts: [
      'localhost',
      '*.replit.dev',
      '*.replit.app',
      '*.repl.co'
    ],
    proxy: {
      '/chat': 'http://localhost:5000',
      '/conversations': 'http://localhost:5000',
    },
  },
  resolve: {
    alias: {
      '@components': path.resolve(__dirname, 'src/components'),
      '@common': path.resolve(__dirname, 'src/components/common'),
      '@features': path.resolve(__dirname, 'src/features'),
      '@routes': path.resolve(__dirname, 'src/routes'),
      '@lib': path.resolve(__dirname, 'src/lib'),
    },
  },
});
