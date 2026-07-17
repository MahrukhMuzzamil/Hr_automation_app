import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During `vite dev` the app talks to a locally running backend on :8000.
// In production the built assets are served by Nginx, which also proxies /api.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
