import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";
import tailwindTypography from "@tailwindcss/typography";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  plugins: [
    react(),
    tailwindcss({
      config: {
        darkMode: "class",
        content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
        theme: {
          extend: {
            colors: {
              shopifyPurple: "#5c6ac4",
            },
          },
        },
        plugins: [tailwindTypography],
      },
    }),
  ],
  server: {
    historyApiFallback: true, // SPA fallback for React Router
    port: 5173,
    open: true,
    host: "0.0.0.0",
    proxy: {
      "/chat": "http://0.0.0.0:5000",
      "/conversations": "http://0.0.0.0:5000",
      "/stream_chat": "http://0.0.0.0:5000",
      // Add new rule for all /api routes
      '/api': {
        target: 'http://0.0.0.0:5000',
        changeOrigin: true,
      }
    },
    allowedHosts: ["localhost", ".replit.dev", ".replit.app", ".repl.co"],
  },
  resolve: {
    alias: {
      "@components": path.resolve(__dirname, "src/components"),
      "@common": path.resolve(__dirname, "src/components/common"),
      "@features": path.resolve(__dirname, "src/features"),
      "@routes": path.resolve(__dirname, "src/routes"),
      "@lib": path.resolve(__dirname, "src/lib"),
    },
  },
});
