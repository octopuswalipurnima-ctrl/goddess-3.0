/**
 * Dashboard API Client Layer
 */

import { DashboardOverview } from "../types";
import { getAuthHeaders } from "./auth";
import { getApiBaseUrl } from "./client";

export async function fetchDashboardOverview(): Promise<DashboardOverview> {
  const res = await fetch(`${getApiBaseUrl()}/dashboard/overview`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch dashboard overview: ${res.statusText}`);
  }
  return res.json();
}
