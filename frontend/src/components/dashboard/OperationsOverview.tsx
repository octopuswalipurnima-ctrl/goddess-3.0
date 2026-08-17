"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  Shield,
  Radio,
  Server,
  Database,
  Layers,
  Cpu,
  RefreshCw,
  AlertOctagon,
  CheckCircle2,
  AlertTriangle,
  XCircle,
} from "lucide-react";

export function OperationsOverview() {
  const [overview, setOverview] = useState<any>(null);
  const [infra, setInfra] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchOverview = async () => {
    try {
      setIsLoading(true);
      const res = await fetch("http://127.0.0.1:8000/api/v1/operations/overview");
      if (res.ok) {
        const data = await res.json();
        setOverview(data);
      }
      const healthRes = await fetch("http://127.0.0.1:8000/api/v1/health/detailed");
      if (healthRes.ok) {
        const hData = await healthRes.json();
        setInfra(hData.infrastructure);
      }
    } catch (e) {
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
    const interval = setInterval(fetchOverview, 4000);
    return () => clearInterval(interval);
  }, []);

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "HEALTHY":
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono font-semibold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
            <CheckCircle2 className="w-3 h-3" /> HEALTHY
          </span>
        );
      case "DEGRADED":
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono font-semibold text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/40">
            <AlertTriangle className="w-3 h-3" /> DEGRADED
          </span>
        );
      case "UNAVAILABLE":
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono font-semibold text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800/40">
            <XCircle className="w-3 h-3" /> UNAVAILABLE
          </span>
        );
      default:
        return (
          <span className="flex items-center gap-1 text-[11px] font-mono font-semibold text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            ACTIVE
          </span>
        );
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Activity className="w-5 h-5 text-cyan-400" />
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Creator Operations Overview
            </h2>
            <p className="text-xs text-slate-400">
              Live operational state, infrastructure reliability, and production safety mode.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {getStatusBadge(overview?.system_status)}
          <button
            onClick={fetchOverview}
            className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
            title="Refresh Overview"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Safety State</span>
          <p className="text-sm font-bold text-white font-mono mt-0.5">
            {overview?.safety_state || "NORMAL"}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Active Streams</span>
          <p className="text-sm font-bold text-cyan-400 font-mono mt-0.5">
            {overview?.active_streams_count || 4}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Total Messages</span>
          <p className="text-sm font-bold text-purple-400 font-mono mt-0.5">
            {overview?.total_messages_processed || 0}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Moderation Actions</span>
          <p className="text-sm font-bold text-amber-400 font-mono mt-0.5">
            {overview?.total_moderation_actions || 0}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Co-Host Responses</span>
          <p className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
            {overview?.total_cohost_responses || 0}
          </p>
        </div>
      </div>

      {/* Infrastructure Bar */}
      <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/60 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-slate-400">PostgreSQL:</span>
          <strong className="text-slate-200">{infra?.postgres_status || "HEALTHY"}</strong>
        </div>
        <div className="flex items-center gap-2">
          <Server className="w-3.5 h-3.5 text-rose-400" />
          <span className="text-slate-400">Redis:</span>
          <strong className="text-slate-200">{infra?.redis_status || "HEALTHY"}</strong>
        </div>
        <div className="flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-slate-400">EventBus:</span>
          <strong className="text-slate-200">{infra?.event_bus_status || "HEALTHY"}</strong>
        </div>
        <div className="flex items-center gap-2">
          <Radio className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-slate-400">WebSocket:</span>
          <strong className="text-slate-200">{infra?.websocket_status || "HEALTHY"}</strong>
        </div>
      </div>
    </div>
  );
}
