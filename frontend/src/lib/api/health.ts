/**
 * Health Diagnostics API Client Layer
 */

import { SystemHealthData } from "../types";

const API_BASE = "http://127.0.0.1:8000/api/v1";

export async function fetchSystemHealth(): Promise<SystemHealthData> {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch system health: ${res.statusText}`);
  }
  return res.json();
}
