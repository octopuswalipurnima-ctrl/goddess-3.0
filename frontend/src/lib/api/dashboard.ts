/**
 * Dashboard API Client Layer
 */

import { DashboardOverview } from "../types";

const API_BASE = "http://127.0.0.1:8000/api/v1";

export async function fetchDashboardOverview(): Promise<DashboardOverview> {
  const res = await fetch(`${API_BASE}/dashboard/overview`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch dashboard overview: ${res.statusText}`);
  }
  return res.json();
}
