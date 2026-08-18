/**
 * Modules API Client Layer
 */

import { ModuleSummaryItem } from "../types";
import { getAuthHeaders } from "./auth";
import { getApiBaseUrl } from "./client";

export async function fetchModules(): Promise<ModuleSummaryItem[]> {
  const res = await fetch(`${getApiBaseUrl()}/modules`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch modules: ${res.statusText}`);
  }
  return res.json();
}

export async function enableModule(moduleId: string): Promise<any> {
  const res = await fetch(`${getApiBaseUrl()}/modules/${moduleId}/enable`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to enable module ${moduleId}: ${res.statusText}`);
  }
  return res.json();
}

export async function disableModule(moduleId: string): Promise<any> {
  const res = await fetch(`${getApiBaseUrl()}/modules/${moduleId}/disable`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to disable module ${moduleId}: ${res.statusText}`);
  }
  return res.json();
}

export async function startModule(moduleId: string): Promise<any> {
  const res = await fetch(`${getApiBaseUrl()}/modules/${moduleId}/start`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to start module ${moduleId}: ${res.statusText}`);
  }
  return res.json();
}

export async function stopModule(moduleId: string): Promise<any> {
  const res = await fetch(`${getApiBaseUrl()}/modules/${moduleId}/stop`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to stop module ${moduleId}: ${res.statusText}`);
  }
  return res.json();
}

export async function updateModuleConfig(moduleId: string, streamId: string, config: any): Promise<any> {
  const res = await fetch(`${getApiBaseUrl()}/modules/${moduleId}/config/${streamId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    throw new Error(`Failed to update module config for ${moduleId}: ${res.statusText}`);
  }
  return res.json();
}

export const updateStreamModuleConfig = updateModuleConfig;
