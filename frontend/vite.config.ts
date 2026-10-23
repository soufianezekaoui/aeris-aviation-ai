/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs on :8000; proxying avoids CORS and keeps URLs relative.
const API = process.env.VITE_API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": API, "/health": API },
  },
  test: { environment: "node" },
});
