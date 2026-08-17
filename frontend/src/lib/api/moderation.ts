/**
 * Moderation API Client Layer
 */

import { ModerationAuditItem, ModerationMetrics } from "../types";
import { getAuthHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export async function fetchModerationStats(): Promise<ModerationMetrics> {
  const res = await fetch(`${API_BASE}/moderation/stats`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch moderation stats: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchModerationAudit(streamId: string): Promise<ModerationAuditItem[]> {
  const res = await fetch(`${API_BASE}/moderation/audit/${streamId}`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch moderation audit for ${streamId}: ${res.statusText}`);
  }
  return res.json();
}

export async function updateModerationConfig(streamId: string, config: any): Promise<any> {
  const res = await fetch(`${API_BASE}/moderation/config/${streamId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    throw new Error(`Failed to update moderation config for ${streamId}: ${res.statusText}`);
  }
  return res.json();
}
