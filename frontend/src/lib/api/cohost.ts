/**
 * Co-Host API Client Layer
 */

import { CoHostAuditItem, CoHostMetrics } from "../types";

const API_BASE = "http://127.0.0.1:8000/api/v1";

export async function fetchCoHostStats(): Promise<CoHostMetrics> {
  const res = await fetch(`${API_BASE}/cohost/stats`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch Co-Host stats: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCoHostAudit(streamId: string): Promise<CoHostAuditItem[]> {
  const res = await fetch(`${API_BASE}/cohost/audit/${streamId}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch Co-Host audit for ${streamId}: ${res.statusText}`);
  }
  return res.json();
}

export async function updateCoHostConfig(streamId: string, config: any): Promise<any> {
  const res = await fetch(`${API_BASE}/cohost/config/${streamId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    throw new Error(`Failed to update Co-Host config for ${streamId}: ${res.statusText}`);
  }
  return res.json();
}
