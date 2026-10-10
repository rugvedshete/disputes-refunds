import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In dev, /api/* is proxied to the FastAPI container/process. In Docker, nginx does the same.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:8000", rewrite: (p) => p.replace(/^\/api/, "") } },
  },
});
