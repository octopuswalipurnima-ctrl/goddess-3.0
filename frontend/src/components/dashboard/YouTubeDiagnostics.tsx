"use client";

import React from "react";
import { YouTubeDiagnosticsData } from "@/lib/types";
import { Radio, Key, Wifi, ShieldAlert, BarChart3 } from "lucide-react";

interface Props {
  data?: YouTubeDiagnosticsData;
}

export function YouTubeDiagnostics({ data }: Props) {
  const diag = data || {
    configured_keys: 0,
    available_keys: 0,
    cooldown_keys: 0,
    unavailable_keys: 0,
    active_streams: 0,
    total_requests: 0,
    successful_requests: 0,
    failed_requests: 0,
    quota_failures: 0,
    failure_rate: 0,
    status: "HEALTHY",
  };

  const statusColor =
    diag.status === "HEALTHY"
      ? "text-emerald-400 border-emerald-800/40 bg-emerald-950/60"
      : diag.status === "DEGRADED"
      ? "text-amber-400 border-amber-800/40 bg-amber-950/60"
      : diag.status === "UNAVAILABLE"
      ? "text-rose-400 border-rose-800/40 bg-rose-950/60"
      : "text-slate-400 border-slate-800/40 bg-slate-950/60";

  return (
    <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-red-400" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
            YouTube Live Engine Diagnostics
          </h2>
        </div>
        <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${statusColor}`}>
          {diag.status || "ROTATION ACTIVE"}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">ROTATED KEYS</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Key className="w-3.5 h-3.5 text-red-400" />
            <span className="text-sm font-bold text-white">
              {diag.available_keys}/{diag.configured_keys} Ready
            </span>
          </div>
          {diag.cooldown_keys > 0 && (
            <span className="text-[9px] text-amber-400 block mt-0.5">
              {diag.cooldown_keys} in cooldown
            </span>
          )}
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">ACTIVE SESSIONS</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Wifi className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-sm font-bold text-white">
              {diag.active_streams} Session(s)
            </span>
          </div>
          <span className="text-[9px] text-slate-400 block mt-0.5">Capacity: 4 Concurrent</span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">FAILOVER & QUOTA</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-sm font-bold text-white">
              {diag.quota_failures || 0} Quota Trips
            </span>
          </div>
          <span className="text-[9px] text-emerald-400 block mt-0.5">Auto-Backoff Active</span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">API REQUESTS</span>
          <div className="flex items-center gap-1 mt-0.5 text-xs font-bold">
            <span className="text-emerald-400">{diag.successful_requests || 0} ok</span>
            <span className="text-slate-600">&bull;</span>
            <span className="text-rose-400">{diag.failed_requests || 0} fail</span>
          </div>
          <span className="text-[9px] text-slate-400 block mt-0.5">
            Total: {diag.total_requests || 0}
          </span>
        </div>
      </div>
    </div>
  );
}
