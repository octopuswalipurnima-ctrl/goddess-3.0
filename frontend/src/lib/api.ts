import { SystemHealthData, StreamSessionSummary } from "./types";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

/**
 * Fetch system health and component status from the Goddess AI backend.
 */
export async function fetchSystemHealth(): Promise<SystemHealthData> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/health`, {
      cache: "no-store",
      headers: {
        "Accept": "application/json",
      },
    });

    if (!res.ok) {
      throw new Error(`Backend returned status ${res.status}: ${res.statusText}`);
    }

    return await res.json();
  } catch (err: any) {
    throw new Error(err.message || "Failed to reach Goddess AI 2.0 backend");
  }
}

/**
 * Fetch active YouTube live stream sessions from the backend.
 */
export async function fetchActiveStreams(): Promise<StreamSessionSummary[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/streams`, {
      cache: "no-store",
      headers: {
        "Accept": "application/json",
      },
    });

    if (!res.ok) {
      throw new Error(`Backend returned status ${res.status}: ${res.statusText}`);
    }

    return await res.json();
  } catch (err: any) {
    return [];
  }
}

/**
 * Connect a new live stream session.
 */
export async function connectStream(streamId: string, channelId?: string): Promise<StreamSessionSummary> {
  const res = await fetch(`${BACKEND_URL}/api/v1/streams`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify({ stream_id: streamId, channel_id: channelId, auto_start: true }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to connect stream (${res.status})`);
  }

  return await res.json();
}

/**
 * Stop an active live stream session.
 */
export async function stopStream(streamId: string): Promise<void> {
  const res = await fetch(`${BACKEND_URL}/api/v1/streams/${encodeURIComponent(streamId)}/stop`, {
    method: "POST",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to stop stream (${res.status})`);
  }
}
