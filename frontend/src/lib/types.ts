/**
 * Unified Type Definitions for GODDESS AI 2.0 Creator Control Center
 */

export type ConnectionState = "CONNECTED" | "RECONNECTING" | "DISCONNECTED";
export type HealthStatus = "HEALTHY" | "DEGRADED" | "UNAVAILABLE" | "ERROR" | "NOT_CONFIGURED" | "UNKNOWN";

export interface ComponentStatus {
  status: HealthStatus;
  details: string;
  metadata: Record<string, any>;
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
    moderation: ComponentStatus;
    cohost: ComponentStatus;
    modules: ComponentStatus;
    [key: string]: ComponentStatus;
  };
}

export interface StreamSessionSummary {
  stream_id: string;
  title: string;
  status?: string;
  is_active: boolean;
  is_live: boolean;
  viewer_count: number;
  concurrent_viewers?: number;
  messages_read: number;
  messages_posted: number;
  messages_processed?: number;
  messages_received?: number;
  start_time: string | null;
  uptime_seconds?: number;
  error_count: number;
}

export interface ModerationMetrics {
  messages_analyzed: number;
  rule_matches: number;
  ai_analyses: number;
  actions_executed: number;
  actions_blocked: number;
  actions_failed: number;
  dry_run_actions: number;
}

export interface ModerationAuditItem {
  audit_id: string;
  timestamp: string;
  stream_id: string;
  message_id: string;
  author_id: string;
  author_name: string;
  message_text: string;
  category: string;
  confidence: number;
  severity: string;
  reason: string;
  action: string;
  action_status: "EXECUTED" | "BLOCKED" | "FAILED" | "DRY_RUN";
}

export interface CoHostMetrics {
  messages_analyzed: number;
  intents_detected: number;
  responses_requested: number;
  responses_generated: number;
  responses_sent: number;
  responses_dry_run: number;
  responses_blocked: number;
  responses_failed: number;
}

export interface CoHostAuditItem {
  audit_id: string;
  timestamp: string;
  stream_id: string;
  message_id: string;
  author_name: string;
  viewer_message: string;
  intent_type: string;
  intent_confidence: number;
  generated_response: string | null;
  status: "SENT" | "DRY_RUN" | "BLOCKED" | "FAILED";
  reason: string;
}

export interface ModuleSummaryItem {
  id: string;
  name: string;
  version: string;
  status: "DISCOVERED" | "REGISTERED" | "LOADED" | "ENABLED" | "RUNNING" | "STOPPED" | "DISABLED" | "FAILED";
  health: "HEALTHY" | "DEGRADED" | "UNAVAILABLE" | "ERROR" | "DISABLED";
  capabilities: string[];
  active_streams: string[];
}

export interface ModulesSummary {
  registered_count: number;
  enabled_count: number;
  running_count: number;
  failed_count: number;
  modules: ModuleSummaryItem[];
}

export interface AIDiagnosticsData {
  configured_keys: number;
  available_keys: number;
  cooldown_keys: number;
  active_requests: number;
  queued_requests: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  primary_model: string;
  fallback_model: string;
}

export interface YouTubeDiagnosticsData {
  configured_keys: number;
  available_keys: number;
  cooldown_keys: number;
  active_streams: number;
}

export interface PersistenceHealthData {
  database: {
    status: string;
    details: string;
    latency_ms: number | null;
  };
  redis: {
    status: string;
    details: string;
    mode: string;
    latency_ms: number | null;
  };
  migration: {
    status: string;
    current_revision: string | null;
  };
}

export interface DashboardOverview {
  timestamp: string;
  version: string;
  uptime_seconds: number;
  streams: StreamSessionSummary[];
  moderation_metrics: ModerationMetrics;
  cohost_metrics: CoHostMetrics;
  modules_summary: ModulesSummary;
  ai_diagnostics: AIDiagnosticsData;
  youtube_diagnostics: YouTubeDiagnosticsData;
  persistence_health?: PersistenceHealthData;
}

export interface ActivityEvent {
  id: string;
  timestamp: string;
  event_type: string;
  source: string;
  stream_id?: string;
  summary: string;
  details?: Record<string, any>;
  level: "info" | "warning" | "error" | "success";
}
