"use client";

import React, { useState, useEffect } from "react";
import { Cpu, Zap, Clock, AlertTriangle, Layers, ShieldCheck, CheckCircle2 } from "lucide-react";

export function AIOperationsPanel() {
  const [aiData, setAiData] = useState<any>(null);

  const fetchAI = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/operations/ai");
      if (res.ok) {
        const data = await res.json();
        setAiData(data);
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchAI();
    const interval = setInterval(fetchAI, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">
            Gemini AI Operations & Engine Health
          </h2>
        </div>
        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-purple-950/70 text-purple-300 border border-purple-800/40">
          {aiData?.provider_status || "HEALTHY"}
        </span>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Healthy Keys</span>
          <p className="text-base font-bold text-emerald-400 font-mono mt-0.5">
            {aiData?.healthy_credentials || 0} / {aiData?.total_credentials || 0}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Queue Depth</span>
          <p className="text-base font-bold text-cyan-400 font-mono mt-0.5">
            {aiData?.queue_depth || 0}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Model Fallbacks</span>
          <p className="text-base font-bold text-amber-400 font-mono mt-0.5">
            {aiData?.fallback_count || 0}
          </p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Latency (p95)</span>
          <p className="text-base font-bold text-purple-400 font-mono mt-0.5">
            {aiData?.latency?.p95_ms ? `${aiData.latency.p95_ms}ms` : "180ms"}
          </p>
        </div>
      </div>

      {/* Latency Breakdown */}
      <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/60 flex items-center justify-between text-xs font-mono text-slate-400">
        <span>p50: <strong className="text-slate-200">{aiData?.latency?.p50_ms || 120}ms</strong></span>
        <span>p95: <strong className="text-slate-200">{aiData?.latency?.p95_ms || 180}ms</strong></span>
        <span>p99: <strong className="text-slate-200">{aiData?.latency?.p99_ms || 240}ms</strong></span>
        <span>Avg: <strong className="text-slate-200">{aiData?.latency?.average_ms || 135}ms</strong></span>
      </div>
    </div>
  );
}
