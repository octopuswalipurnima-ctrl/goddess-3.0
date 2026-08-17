/**
 * Streams API Client Layer for GODDESS AI 2.0
 */

import { StreamSessionSummary, StreamSupervisorSummary } from "../types";
import { getAuthHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export async function fetchActiveStreams(): Promise<StreamSessionSummary[]> {
  const res = await fetch(`${API_BASE}/streams`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch active streams: ${res.statusText}`);
  }
  return res.json();
}

export async function connectStream(streamId: string, title?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/streams`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ stream_id: streamId, auto_start: true }),
  });
  if (!res.ok) {
    throw new Error(`Failed to connect stream ${streamId}: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSupervisedStreams(): Promise<StreamSupervisorSummary[]> {
  const res = await fetch(`${API_BASE}/streams/supervised`, {
    cache: "no-store",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch supervised streams: ${res.statusText}`);
  }
  return res.json();
}

export async function attachSupervisedStream(streamId: string, channelId?: string): Promise<StreamSupervisorSummary> {
  const res = await fetch(`${API_BASE}/streams/attach`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ stream_id: streamId, channel_id: channelId, auto_start: true }),
  });
  if (!res.ok) {
    throw new Error(`Failed to attach stream ${streamId}: ${res.statusText}`);
  }
  return res.json();
}

export async function detachSupervisedStream(streamId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/${streamId}/detach`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to detach stream ${streamId}: ${res.statusText}`);
  }
}

export async function reconnectSupervisedStream(streamId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/${streamId}/reconnect`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to reconnect stream ${streamId}: ${res.statusText}`);
  }
}

export async function stopStream(streamId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/${streamId}/stop`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to stop stream ${streamId}: ${res.statusText}`);
  }
}

export async function triggerStreamEmergencyStop(streamId: string, reason = "Operator emergency stop"): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/${streamId}/emergency-stop`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    throw new Error(`Failed to trigger emergency stop for ${streamId}: ${res.statusText}`);
  }
}

export async function clearStreamEmergencyStop(streamId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/${streamId}/clear-emergency-stop`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to clear emergency stop for ${streamId}: ${res.statusText}`);
  }
}

export async function enableStreamSafeMode(streamId: string, reason = "Operator enabled safe mode"): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/${streamId}/safe-mode`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    throw new Error(`Failed to enable safe mode for ${streamId}: ${res.statusText}`);
  }
}

export async function disableStreamSafeMode(streamId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/${streamId}/clear-safe-mode`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to disable safe mode for ${streamId}: ${res.statusText}`);
  }
}

export async function triggerGlobalEmergencyStop(reason = "Operator global emergency stop"): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/global-emergency-stop`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    throw new Error(`Failed to trigger global emergency stop: ${res.statusText}`);
  }
}

export async function clearGlobalEmergencyStop(): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/clear-global-emergency-stop`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Failed to clear global emergency stop: ${res.statusText}`);
  }
}
