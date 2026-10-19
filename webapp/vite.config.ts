import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В разработке запросы /api идут на backend (python -m app.main, порт 8000).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000", "/media": "http://localhost:8000" } },
});
