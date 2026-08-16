export type HealthStatus = "HEALTHY" | "NOT_CONFIGURED" | "UNAVAILABLE" | "ERROR";

export interface ComponentStatus {
  status: HealthStatus;
  details: string;
  metadata?: Record<string, any>;
}

export interface SystemHealthData {
  application: string;
  version: string;
  environment: string;
  uptime_seconds: number;
  timestamp: string;
  components: {
    database: ComponentStatus;
    redis: ComponentStatus;
    youtube: ComponentStatus;
    gemini: ComponentStatus;
    [key: string]: ComponentStatus;
  };
}

export interface StreamSessionSummary {
  stream_id: string;
  channel_id?: string | null;
  title?: string | null;
  status: "STANDBY" | "CONNECTING" | "LIVE" | "ENDED" | "FAILED";
  live_chat_id?: string | null;
  concurrent_viewers: number;
  messages_received: number;
  reconnect_count: number;
  uptime_seconds: number;
  last_activity?: string | null;
}
