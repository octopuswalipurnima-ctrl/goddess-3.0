/**
 * Co-Host API Client Layer
 */

import { CoHostAuditItem, CoHostMetrics } from "../types";
import { getAuthHeaders } from "./auth";
import { getApiBaseUrl } from "./client";

export async function fetchCoHostStats(): Promise<CoHostMetrics> {
  const res = await fetch(`${getApiBaseUrl()}/cohost/stats`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Co-Host stats: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCoHostAudit(streamId: string): Promise<CoHostAuditItem[]> {
  const res = await fetch(`${getApiBaseUrl()}/cohost/audit/${streamId}`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch Co-Host audit for ${streamId}: ${res.statusText}`);
  }
  return res.json();
}

export async function updateCoHostConfig(streamId: string, config: any): Promise<any> {
  const res = await fetch(`${getApiBaseUrl()}/cohost/config/${streamId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    throw new Error(`Failed to update Co-Host config for ${streamId}: ${res.statusText}`);
  }
  return res.json();
}
