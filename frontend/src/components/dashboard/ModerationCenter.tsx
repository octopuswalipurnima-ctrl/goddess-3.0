"use client";

import React, { useEffect, useState } from "react";
import { ModerationAuditItem, ModerationMetrics } from "@/lib/types";
import { fetchModerationAudit, fetchModerationStats } from "@/lib/api";
import { Shield, ShieldAlert, CheckCircle, XCircle, AlertTriangle, PlayCircle, RefreshCw } from "lucide-react";

interface Props {
  streamId: string;
}

export function ModerationCenter({ streamId }: Props) {
  const [stats, setStats] = useState<ModerationMetrics>({
    messages_analyzed: 0,
    rule_matches: 0,
    ai_analyses: 0,
    actions_executed: 0,
    actions_blocked: 0,
    actions_failed: 0,
    dry_run_actions: 0,
  });

  const [auditLog, setAuditLog] = useState<ModerationAuditItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadData = async () => {
    try {
      const [s, a] = await Promise.all([
        fetchModerationStats().catch(() => stats),
        fetchModerationAudit(streamId).catch(() => []),
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
      case "EXECUTED":
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
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
            AI Moderation Center
          </h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800/40">
            3-Tier Pipeline
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
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Analyzed</span>
          <p className="text-base font-bold text-white font-mono">{stats.messages_analyzed}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Rule Matches</span>
          <p className="text-base font-bold text-amber-400 font-mono">{stats.rule_matches}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">AI Analyses</span>
          <p className="text-base font-bold text-cyan-400 font-mono">{stats.ai_analyses}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Executed</span>
          <p className="text-base font-bold text-emerald-400 font-mono">{stats.actions_executed}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">DRY-RUN</span>
          <p className="text-base font-bold text-blue-400 font-mono">{stats.dry_run_actions}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Blocked</span>
          <p className="text-base font-bold text-amber-400 font-mono">{stats.actions_blocked}</p>
        </div>
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Failed</span>
          <p className="text-base font-bold text-rose-400 font-mono">{stats.actions_failed}</p>
        </div>
      </div>

      {/* Live Audit Log Feed */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-slate-300">Live Decision & Audit Log Feed</h3>
        <div className="max-h-56 overflow-y-auto rounded-xl bg-slate-950/80 border border-slate-800/80 divide-y divide-slate-800/50 text-xs">
          {auditLog.length === 0 ? (
            <div className="p-4 text-center text-slate-500 font-mono text-[11px]">
              No moderation events recorded yet for this stream.
            </div>
          ) : (
            auditLog.map((item) => (
              <div key={item.audit_id} className="p-2.5 flex items-start justify-between gap-3 hover:bg-slate-900/50">
                <div className="space-y-0.5 flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-200 truncate">{item.author_name}</span>
                    <span className="text-[10px] font-mono text-slate-500">
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">
                      {item.category} ({(item.confidence * 100).toFixed(0)}%)
                    </span>
                  </div>
                  <p className="text-slate-400 text-[11px] truncate">"{item.message_text}"</p>
                  <p className="text-[10px] text-slate-500">{item.reason}</p>
                </div>

                <div className="flex flex-col items-end gap-1">
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${getStatusBadge(item.action_status)}`}>
                    {item.action_status}: {item.action}
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
