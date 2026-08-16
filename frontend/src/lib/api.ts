import { SystemHealthData } from "./types";

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
    // If backend is completely offline or unreachable
    throw new Error(err.message || "Failed to reach Goddess AI 2.0 backend");
  }
}
