/**
 * Health Diagnostics API Client Layer
 */

import { SystemHealthData } from "../types";
import { getApiBaseUrl } from "./client";

export async function fetchSystemHealth(): Promise<SystemHealthData> {
  const res = await fetch(`${getApiBaseUrl()}/health`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch system health: ${res.statusText}`);
  }
  return res.json();
}
