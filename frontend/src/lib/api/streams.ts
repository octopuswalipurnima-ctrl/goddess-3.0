/**
 * Streams API Client Layer
 */

import { StreamSessionSummary } from "../types";

const API_BASE = "http://127.0.0.1:8000/api/v1";

export async function fetchActiveStreams(): Promise<StreamSessionSummary[]> {
  const res = await fetch(`${API_BASE}/streams`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to fetch active streams: ${res.statusText}`);
  }
  return res.json();
}

export async function connectStream(streamId: string, title?: string): Promise<any> {
  const res = await fetch(`${API_BASE}/streams/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stream_id: streamId, stream_title: title || streamId }),
  });
  if (!res.ok) {
    throw new Error(`Failed to connect stream ${streamId}: ${res.statusText}`);
  }
  return res.json();
}

export async function stopStream(streamId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/streams/${streamId}/stop`, { method: "POST" });
  if (!res.ok) {
    throw new Error(`Failed to stop stream ${streamId}: ${res.statusText}`);
  }
}
