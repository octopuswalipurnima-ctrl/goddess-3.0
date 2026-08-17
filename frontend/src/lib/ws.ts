/**
 * Centralized Shared WebSocket Client for GODDESS AI 2.0 Dashboard.
 *
 * Implements exponential backoff auto-reconnect, single connection pooling,
 * connection state broadcasting, and typed event distribution.
 */

import { ActivityEvent, ConnectionState } from "./types";

type EventListener = (event: any) => void;
type StateListener = (state: ConnectionState) => void;

class DashboardWebSocketManager {
  private ws: WebSocket | null = null;
  private state: ConnectionState = "DISCONNECTED";
  private reconnectAttempt = 0;
  private maxReconnectDelay = 30000; // 30s
  private reconnectTimer: any = null;
  private isIntentionallyClosed = false;

  private eventListeners: Map<string, Set<EventListener>> = new Map();
  private stateListeners: Set<StateListener> = new Set();
  private activityListeners: Set<(event: ActivityEvent) => void> = new Set();

  constructor() {
    // Auto-connect if in browser environment
    if (typeof window !== "undefined") {
      this.connect();
    }
  }

  public connect(): void {
    if (typeof window === "undefined") return;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isIntentionallyClosed = false;
    this.setState(this.reconnectAttempt > 0 ? "RECONNECTING" : "DISCONNECTED");

    try {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.hostname === "localhost" ? "127.0.0.1:8000" : window.location.host;
      const wsUrl = `${protocol}//${host}/api/v1/ws`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.reconnectAttempt = 0;
        this.setState("CONNECTED");
        this.emitActivity({
          id: `ws_open_${Date.now()}`,
          timestamp: new Date().toISOString(),
          event_type: "WEBSOCKET_CONNECTED",
          source: "WebSocket",
          summary: "Real-time telemetry connection established.",
          level: "success",
        });
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.handleIncomingEvent(payload);
        } catch (err) {
          console.error("Failed to parse incoming WebSocket message", err);
        }
      };

      this.ws.onclose = () => {
        this.setState("DISCONNECTED");
        if (!this.isIntentionallyClosed) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        this.setState("DISCONNECTED");
      };
    } catch (err) {
      this.setState("DISCONNECTED");
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempt), this.maxReconnectDelay);
    this.reconnectAttempt++;
    this.setState("RECONNECTING");

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private setState(newState: ConnectionState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.stateListeners.forEach((listener) => listener(newState));
    }
  }

  public getState(): ConnectionState {
    return this.state;
  }

  public onStateChange(listener: StateListener): () => void {
    this.stateListeners.add(listener);
    listener(this.state);
    return () => this.stateListeners.delete(listener);
  }

  public onActivity(listener: (event: ActivityEvent) => void): () => void {
    this.activityListeners.add(listener);
    return () => this.activityListeners.delete(listener);
  }

  public subscribe(eventType: string, listener: EventListener): () => void {
    if (!this.eventListeners.has(eventType)) {
      this.eventListeners.set(eventType, new Set());
    }
    this.eventListeners.get(eventType)!.add(listener);

    return () => {
      const listeners = this.eventListeners.get(eventType);
      if (listeners) {
        listeners.delete(listener);
      }
    };
  }

  private handleIncomingEvent(payload: any): void {
    const eventType = payload.event_type || payload.type || "UNKNOWN";

    // Notify specific event listeners
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      listeners.forEach((listener) => listener(payload.data || payload));
    }

    // Convert to Activity Event
    this.emitActivity({
      id: `act_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      timestamp: payload.timestamp || new Date().toISOString(),
      event_type: eventType,
      source: payload.source || "EventBus",
      stream_id: payload.stream_id || payload.data?.stream_id,
      summary: payload.summary || `${eventType} received`,
      details: payload.data || payload,
      level: this.inferLevel(eventType),
    });
  }

  private emitActivity(act: ActivityEvent): void {
    this.activityListeners.forEach((listener) => listener(act));
  }

  private inferLevel(eventType: string): "info" | "warning" | "error" | "success" {
    if (eventType.includes("FAILED") || eventType.includes("ERROR")) return "error";
    if (eventType.includes("BLOCKED") || eventType.includes("FALLBACK")) return "warning";
    if (eventType.includes("SENT") || eventType.includes("EXECUTED") || eventType.includes("CONNECTED"))
      return "success";
    return "info";
  }

  public disconnect(): void {
    this.isIntentionallyClosed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setState("DISCONNECTED");
  }
}

// Global shared singleton
export const dashboardWs = new DashboardWebSocketManager();
