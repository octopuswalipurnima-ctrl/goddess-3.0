/**
 * Moderation API Client Layer
 */

import { ModerationAuditItem, ModerationMetrics } from "../types";
import { getAuthHeaders } from "./auth";
import { getApiBaseUrl } from "./client";

export async function fetchModerationStats(): Promise<ModerationMetrics> {
  const res = await fetch(`${getApiBaseUrl()}/moderation/stats`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch moderation stats: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchModerationAudit(streamId: string): Promise<ModerationAuditItem[]> {
  const res = await fetch(`${getApiBaseUrl()}/moderation/audit/${streamId}`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch moderation audit for ${streamId}: ${res.statusText}`);
  }
  return res.json();
}

export async function updateModerationConfig(streamId: string, config: any): Promise<any> {
  const res = await fetch(`${getApiBaseUrl()}/moderation/config/${streamId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    throw new Error(`Failed to update moderation config for ${streamId}: ${res.statusText}`);
  }
  return res.json();
}
