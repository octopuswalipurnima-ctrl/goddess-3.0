/**
 * Modules API Client Layer
 */

import { ModuleSummaryItem } from "../types";
import { getAuthHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export async function fetchModules(): Promise<ModuleSummaryItem[]> {
  const res = await fetch(`${API_BASE}/modules`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch modules: ${res.statusText}`);
  }
  return res.json();
}

export async function enableModule(moduleId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/modules/${moduleId}/enable`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to enable module ${moduleId}: ${res.statusText}`);
  }
  return res.json();
}

export async function disableModule(moduleId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/modules/${moduleId}/disable`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to disable module ${moduleId}: ${res.statusText}`);
  }
  return res.json();
}

export async function startModule(moduleId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/modules/${moduleId}/start`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to start module ${moduleId}: ${res.statusText}`);
  }
  return res.json();
}

export async function stopModule(moduleId: string): Promise<any> {
  const res = await fetch(`${API_BASE}/modules/${moduleId}/stop`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to stop module ${moduleId}: ${res.statusText}`);
  }
  return res.json();
}

export async function updateStreamModuleConfig(moduleId: string, streamId: string, enabled: boolean, settings: any = {}): Promise<any> {
  const res = await fetch(`${API_BASE}/modules/${moduleId}/config/${streamId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify({ enabled, settings }),
  });
  if (!res.ok) {
    throw new Error(`Failed to update config for module ${moduleId} on ${streamId}: ${res.statusText}`);
  }
  return res.json();
}
