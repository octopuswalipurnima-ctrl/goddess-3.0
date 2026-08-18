"use client";

import React, { useState, useEffect } from "react";
import { Key, ShieldCheck, AlertCircle, RefreshCw } from "lucide-react";
import { getApiBaseUrl } from "@/lib/api/client";
import { getAuthHeaders } from "@/lib/api/auth";

export function ProviderHealthPanel() {
  const [providers, setProviders] = useState<any>(null);

  const fetchProviders = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/operations/providers`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setProviders(data);
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchProviders();
    const interval = setInterval(fetchProviders, 5000);
    return () => clearInterval(interval);
  }, []);

  const renderKeyPills = (creds?: any[]) => {
    if (!creds || creds.length === 0) {
      return (
        <span className="text-xs text-slate-500 font-mono">No keys configured</span>
      );
    }
    return creds.map((c: any, idx: number) => {
      const isAvail = c.state === "AVAILABLE";
      const isCooldown = c.state === "COOLDOWN";
      return (
        <span
          key={idx}
          className={`px-2 py-1 rounded text-[11px] font-mono font-semibold border ${
            isAvail
              ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/50"
              : isCooldown
              ? "bg-amber-950/60 text-amber-300 border-amber-800/50"
              : "bg-rose-950/60 text-rose-300 border-rose-800/50"
          }`}
        >
          {c.key_alias || `KEY-${idx + 1}`} ({c.state})
        </span>
      );
    });
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Key className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-white uppercase tracking-wider">
            Provider Credential Pool Health
          </h2>
        </div>
        <span className="text-[10px] font-mono text-slate-400">Zero Raw Secret Guarantee</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* YouTube */}
        <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/70 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-200">YouTube Data API v3</h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {providers?.youtube?.status || "HEALTHY"}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {renderKeyPills(providers?.youtube?.credentials)}
          </div>
        </div>

        {/* Gemini */}
        <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/70 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-200">Google Gemini AI API</h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-300">
              {providers?.gemini?.status || "HEALTHY"}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {renderKeyPills(providers?.gemini?.credentials)}
          </div>
        </div>
      </div>
    </div>
  );
}
