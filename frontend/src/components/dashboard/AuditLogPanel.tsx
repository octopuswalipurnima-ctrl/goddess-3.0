"use client";

import React, { useState, useEffect } from "react";
import { History, ShieldCheck, Filter, RefreshCw } from "lucide-react";
import { getApiBaseUrl } from "@/lib/api/client";
import { getAuthHeaders } from "@/lib/api/auth";

export function AuditLogPanel() {
  const [logs, setLogs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchAudit = async () => {
    try {
      setIsLoading(true);
      const res = await fetch(`${getApiBaseUrl()}/operations/audit?limit=25`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (e) {}
    finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit();
    const interval = setInterval(fetchAudit, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">
            Operational Audit Trail
          </h2>
        </div>
        <button
          onClick={fetchAudit}
          className="p-1 rounded bg-slate-800 text-slate-400 hover:text-white transition"
        >
          <RefreshCw className={`w-3 h-3 ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Audit Table */}
      <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1 font-mono text-xs">
        {logs.length === 0 ? (
          <div className="p-4 text-center text-slate-500">No recent audit records</div>
        ) : (
          logs.map((item, idx) => (
            <div
              key={idx}
              className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/70 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-[11px]"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`px-1.5 py-0.5 rounded font-bold text-[10px] ${
                    item.result === "SUCCESS"
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800/40"
                      : "bg-rose-950 text-rose-400 border border-rose-800/40"
                  }`}
                >
                  {item.action}
                </span>
                <span className="text-slate-300">
                  Target: <strong>{item.target}</strong>
                </span>
                {item.stream_id && (
                  <span className="text-cyan-400">[{item.stream_id}]</span>
                )}
              </div>

              <div className="flex items-center gap-3 text-slate-500 text-[10px]">
                <span>By: {item.actor_id} ({item.actor_role})</span>
                <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
