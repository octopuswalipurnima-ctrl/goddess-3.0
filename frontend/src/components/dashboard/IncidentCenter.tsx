"use client";

import React, { useState, useEffect } from "react";
import { AlertTriangle, AlertOctagon, CheckCircle2, RefreshCw, ShieldAlert, Activity } from "lucide-react";
import { getApiBaseUrl } from "@/lib/api/client";
import { getAuthHeaders } from "@/lib/api/auth";

interface IncidentItem {
  id: string;
  timestamp: string;
  severity: "CRITICAL" | "WARNING" | "INFO";
  stream_id?: string;
  component: string;
  description: string;
  correlation_id?: string;
}

export function IncidentCenter() {
  const [incidents, setIncidents] = useState<IncidentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchIncidents = async () => {
    try {
      setIsLoading(true);
      const res = await fetch(`${getApiBaseUrl()}/operations/events?limit=20`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const events = await res.json();
        const formatted: IncidentItem[] = events
          .filter((e: any) =>
            [
              "EMERGENCY_STOP",
              "SAFE_MODE_CHANGED",
              "PROVIDER_HEALTH_CHANGED",
              "SYSTEM_HEALTH_CHANGED",
              "STREAM_STATUS_CHANGED",
            ].includes(e.event_type)
          )
          .map((e: any) => ({
            id: e.event_id,
            timestamp: e.timestamp,
            severity:
              e.event_type === "EMERGENCY_STOP"
                ? "CRITICAL"
                : e.event_type === "SAFE_MODE_CHANGED"
                ? "WARNING"
                : "INFO",
            stream_id: e.stream_id,
            component: e.event_type.replace("_", " "),
            description: e.payload?.reason || e.payload?.status || "State changed",
            correlation_id: e.event_id,
          }));
        setIncidents(formatted);
      }
    } catch (e) {
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-400" />
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Production Incident & Recovery Center
            </h2>
            <p className="text-xs text-slate-400">
              Live operational incident tracking, provider failovers, and autonomous recovery events.
            </p>
          </div>
        </div>

        <button
          onClick={fetchIncidents}
          className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition"
          title="Refresh Incidents"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Incidents Feed */}
      <div className="max-h-64 overflow-y-auto space-y-2 pr-1 font-mono text-xs">
        {incidents.length === 0 ? (
          <div className="p-4 text-center text-slate-500 rounded-xl bg-slate-950/40 border border-slate-800/60">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 mx-auto mb-1 opacity-80" />
            <span>Zero active incidents. All systems operational.</span>
          </div>
        ) : (
          incidents.map((inc) => (
            <div
              key={inc.id}
              className={`p-3 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
                inc.severity === "CRITICAL"
                  ? "bg-rose-950/40 border-rose-800/60 text-rose-300"
                  : inc.severity === "WARNING"
                  ? "bg-amber-950/40 border-amber-800/60 text-amber-300"
                  : "bg-slate-950/50 border-slate-800/70 text-slate-300"
              }`}
            >
              <div className="flex items-center gap-2.5">
                {inc.severity === "CRITICAL" ? (
                  <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[11px] uppercase tracking-wide">
                      {inc.component}
                    </span>
                    {inc.stream_id && (
                      <span className="text-cyan-400 text-[10px]">[{inc.stream_id}]</span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-300 font-sans mt-0.5">{inc.description}</p>
                </div>
              </div>

              <div className="flex sm:flex-col sm:items-end text-[10px] text-slate-400 font-mono">
                <span>{new Date(inc.timestamp).toLocaleTimeString()}</span>
                {inc.correlation_id && (
                  <span className="text-[9px] text-slate-500">{inc.correlation_id}</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
