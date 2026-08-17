"use client";

import React from "react";
import { YouTubeDiagnosticsData } from "@/lib/types";
import { Radio, Key, Wifi, AlertTriangle } from "lucide-react";

interface Props {
  data?: YouTubeDiagnosticsData;
}

export function YouTubeDiagnostics({ data }: Props) {
  const diag = data || {
    configured_keys: 0,
    available_keys: 0,
    cooldown_keys: 0,
    active_streams: 0,
  };

  return (
    <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-red-400" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
            YouTube Live Engine Diagnostics
          </h2>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-800/40">
          Quota Rotation Active
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs font-mono">
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
              {diag.cooldown_keys} key(s) in quota cooldown
            </span>
          )}
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">ACTIVE SESSIONS</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Wifi className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-sm font-bold text-white">
              {diag.active_streams} Stream Session(s)
            </span>
          </div>
          <span className="text-[9px] text-slate-400 block mt-0.5">Capacity: 4 Concurrent</span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">FAILOVER STRATEGY</span>
          <div className="mt-0.5 text-xs font-bold text-slate-300">
            Round-Robin + Exponential Backoff
          </div>
          <span className="text-[9px] text-emerald-400 block mt-0.5">Auto-Recovery Active</span>
        </div>
      </div>
    </div>
  );
}
