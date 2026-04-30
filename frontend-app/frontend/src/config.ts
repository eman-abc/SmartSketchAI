/**
 * API base URL for SmartSketch backend.
 * Set VITE_API_BASE_URL in .env for local dev (e.g. http://127.0.0.1:8000/api).
 */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api';
