"use client";

import React from "react";
import { Cpu, Server, Clock, Zap } from "lucide-react";
import { SystemHealthData } from "@/lib/types";

interface BotStatusCardProps {
  health: SystemHealthData | null;
  isLoading: boolean;
  error: string | null;
}

export function BotStatusCard({ health, isLoading, error }: BotStatusCardProps) {
  return (
    <div className="p-5 rounded-2xl bg-gradient-to-b from-slate-900/90 to-slate-950 border border-slate-800/90 shadow-xl space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              <span>Goddess AI 2.0 Core</span>
              {health && (
                <span className="px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/40 text-[10px] font-mono font-medium">
                  {health.application}
                </span>
              )}
            </h1>
            <p className="text-xs text-slate-400">Local-First Multi-Stream Architecture</p>
          </div>
        </div>

        {/* Live Refresh Status */}
        <div className="flex items-center gap-2 text-xs">
          {isLoading && (
            <span className="text-blue-400 font-mono flex items-center gap-1.5 animate-pulse">
              <Zap className="w-3.5 h-3.5" /> Synchronizing...
            </span>
          )}
          {error && (
            <span className="text-rose-400 font-mono text-[11px]">
              Connection Error: {error}
            </span>
          )}
        </div>
      </div>

      {/* Metric Highlights */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 border-t border-slate-800/60 text-xs">
        <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/50">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
            <Server className="w-3.5 h-3.5 text-slate-400" />
            <span>Environment</span>
          </div>
          <p className="font-mono text-sm font-semibold text-slate-200 mt-1 capitalize">
            {health?.environment || "Development"}
          </p>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/50">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>Server Uptime</span>
          </div>
          <p className="font-mono text-sm font-semibold text-slate-200 mt-1">
            {health ? `${health.uptime_seconds}s` : "--"}
          </p>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/50">
          <div className="text-slate-400 text-[11px]">Backend Port</div>
          <p className="font-mono text-sm font-semibold text-slate-200 mt-1">:8000</p>
        </div>

        <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/50">
          <div className="text-slate-400 text-[11px]">Target Streams</div>
          <p className="font-mono text-sm font-semibold text-cyan-400 mt-1">4 Simultaneous</p>
        </div>
      </div>
    </div>
  );
}
