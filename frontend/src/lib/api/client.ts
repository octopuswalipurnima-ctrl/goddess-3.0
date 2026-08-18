/**
 * Dynamic Backend URL and API Client Configuration for GODDESS AI 2.0.
 * Automatically connects to the live backend domain on Railway or local environment.
 */

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.trim()) {
    return process.env.NEXT_PUBLIC_API_URL.trim().replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    // If Next.js dev server on port 3000, talk to FastAPI on 8000
    if (window.location.hostname === "localhost" && window.location.port === "3000") {
      return "http://127.0.0.1:8000/api/v1";
    }
    // In production on Railway / Cloud: talk directly to current origin
    return `${window.location.origin}/api/v1`;
  }
  return "http://127.0.0.1:8000/api/v1";
}

export function getWsUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL && process.env.NEXT_PUBLIC_WS_URL.trim()) {
    return process.env.NEXT_PUBLIC_WS_URL.trim();
  }
  if (typeof window !== "undefined") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = (window.location.hostname === "localhost" && window.location.port === "3000")
      ? "127.0.0.1:8000"
      : window.location.host;
    return `${protocol}//${host}/api/v1/ws`;
  }
  return "ws://127.0.0.1:8000/api/v1/ws";
}
