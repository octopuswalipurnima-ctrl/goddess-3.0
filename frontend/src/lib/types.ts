export type HealthStatus = "HEALTHY" | "NOT_CONFIGURED" | "UNAVAILABLE" | "ERROR";

export interface ComponentStatus {
  status: HealthStatus;
  details: string;
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

export interface StreamSlotPreview {
  id: string;
  name: string;
  status: "IDLE" | "MONITORING" | "LIVE" | "FAILED";
  channelName?: string;
  viewerCount?: number;
  messageRatePerMin?: number;
}
