"use client";

import React, { useEffect, useState } from "react";
import { CoHostAuditItem, CoHostMetrics } from "@/lib/types";
import { fetchCoHostAudit, fetchCoHostStats } from "@/lib/api";
import { Bot, Sparkles, RefreshCw, MessageSquare, ArrowRight } from "lucide-react";

interface Props {
  streamId: string;
}

export function CoHostCenter({ streamId }: Props) {
  const [stats, setStats] = useState<CoHostMetrics>({
    messages_analyzed: 0,
    intents_detected: 0,
    responses_requested: 0,
    responses_generated: 0,
    responses_sent: 0,
    responses_dry_run: 0,
    responses_blocked: 0,
    responses_failed: 0,
  });

  const [auditLog, setAuditLog] = useState<CoHostAuditItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadData = async () => {
    try {
      const [s, a] = await Promise.all([
        fetchCoHostStats().catch(() => stats),
        fetchCoHostAudit(streamId).catch(() => []),
      ]);
      setStats(s);
      setAuditLog(a);
    } catch (err) {}
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 4000);
    return () => clearInterval(interval);
  }, [streamId]);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "SENT":
        return "bg-emerald-950 text-emerald-300 border-emerald-800";
      case "DRY_RUN":
        return "bg-cyan-950 text-cyan-300 border-cyan-800";
      case "BLOCKED":
        return "bg-amber-950 text-amber-300 border-amber-800";
      case "FAILED":
        return "bg-rose-950 text-rose-300 border-rose-800";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
            AI Co-Host Interaction Center
          </h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-400 border border-purple-800/40">
            NORMAL Priority &bull; Max 200 Chars
          </span>
        </div>

        <button
          onClick={loadData}
          className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono transition"
        >
          <RefreshCw className={`w-3 h-3 ${isLoading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Analyzed</span>
          <p className="text-base font-bold text-white font-mono">{stats.messages_analyzed}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Intents</span>
          <p className="text-base font-bold text-cyan-400 font-mono">{stats.intents_detected}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Generated</span>
          <p className="text-base font-bold text-purple-400 font-mono">{stats.responses_generated}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">DRY-RUN</span>
          <p className="text-base font-bold text-blue-400 font-mono">{stats.responses_dry_run}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Sent to Chat</span>
          <p className="text-base font-bold text-emerald-400 font-mono">{stats.responses_sent}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Blocked/Filtered</span>
          <p className="text-base font-bold text-amber-400 font-mono">{stats.responses_blocked}</p>
        </div>
      </div>

      {/* Live Interaction Feed */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-slate-300">Live Co-Host Conversations Feed</h3>
        <div className="max-h-56 overflow-y-auto rounded-xl bg-slate-950/80 border border-slate-800/80 divide-y divide-slate-800/50 text-xs">
          {auditLog.length === 0 ? (
            <div className="p-4 text-center text-slate-500 font-mono text-[11px]">
              No conversational interactions recorded yet for this stream.
            </div>
          ) : (
            auditLog.map((item) => (
              <div key={item.audit_id} className="p-2.5 flex items-start justify-between gap-3 hover:bg-slate-900/50">
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-purple-300 truncate">{item.author_name}</span>
                    <span className="text-[10px] font-mono text-slate-500">
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-purple-400">
                      {item.intent_type} ({(item.intent_confidence * 100).toFixed(0)}%)
                    </span>
                  </div>

                  <p className="text-slate-400 text-[11px] truncate">Viewer: "{item.viewer_message}"</p>
                  {item.generated_response && (
                    <p className="text-slate-200 text-[11px] font-semibold bg-purple-950/40 p-1.5 rounded border border-purple-900/30">
                      Goddess: "{item.generated_response}"
                    </p>
                  )}
                  <p className="text-[10px] text-slate-500">{item.reason}</p>
                </div>

                <div className="flex flex-col items-end gap-1">
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${getStatusBadge(item.status)}`}>
                    {item.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
