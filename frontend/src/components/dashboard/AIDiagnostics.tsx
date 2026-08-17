"use client";

import React from "react";
import { AIDiagnosticsData } from "@/lib/types";
import { Cpu, Key, Layers, CheckCircle, AlertCircle, Clock } from "lucide-react";

interface Props {
  data?: AIDiagnosticsData;
}

export function AIDiagnostics({ data }: Props) {
  const diag = data || {
    configured_keys: 0,
    available_keys: 0,
    cooldown_keys: 0,
    active_requests: 0,
    queued_requests: 0,
    total_requests: 0,
    successful_requests: 0,
    failed_requests: 0,
    primary_model: "gemini-2.5-flash",
    fallback_model: "gemini-2.5-flash-lite",
  };

  return (
    <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
            Gemini AI Diagnostics
          </h2>
        </div>
        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/40">
          Token-Bucket Limiter Active
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs font-mono">
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">CREDENTIAL POOL</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Key className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-sm font-bold text-white">
              {diag.available_keys}/{diag.configured_keys} Ready
            </span>
          </div>
          {diag.cooldown_keys > 0 && (
            <span className="text-[9px] text-amber-400 block mt-0.5">
              {diag.cooldown_keys} key(s) in cooldown
            </span>
          )}
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">QUEUE & CONCURRENCY</span>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Layers className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-sm font-bold text-white">
              {diag.active_requests} Active &bull; {diag.queued_requests} Queued
            </span>
          </div>
          <span className="text-[9px] text-slate-400 block mt-0.5">Max Concurrency: 2</span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">MODEL ROUTING</span>
          <div className="mt-0.5 space-y-0.5">
            <div className="text-xs font-bold text-cyan-300 truncate">P: {diag.primary_model}</div>
            <div className="text-[10px] text-slate-400 truncate">F: {diag.fallback_model}</div>
          </div>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-500 block">REQUEST LIFECYCLE</span>
          <div className="flex items-center gap-1 mt-0.5 text-xs font-bold">
            <span className="text-emerald-400">{diag.successful_requests} ok</span>
            <span className="text-slate-600">&bull;</span>
            <span className="text-rose-400">{diag.failed_requests} fail</span>
          </div>
          <span className="text-[9px] text-slate-400 block mt-0.5">Total: {diag.total_requests}</span>
        </div>
      </div>
    </div>
  );
}
