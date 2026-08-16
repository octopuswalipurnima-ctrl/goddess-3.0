"use client";

import React from "react";
import { Activity, ShieldAlert, Sparkles, Radio } from "lucide-react";

interface NavbarProps {
  isBackendConnected: boolean;
  version?: string;
  uptimeSeconds?: number;
}

export function Navbar({ isBackendConnected, version = "2.0.0", uptimeSeconds = 0 }: NavbarProps) {
  const formatUptime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const hrs = Math.floor(mins / 60);
    if (hrs > 0) return `${hrs}h ${mins % 60}m`;
    return `${mins}m ${secs}s`;
  };

  return (
    <header className="h-16 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-50">
      {/* Brand Identity */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-blue-500/10">
          <Sparkles className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-base tracking-wide text-white">GODDESS AI</span>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800/40">
              v{version}
            </span>
          </div>
          <p className="text-[11px] text-slate-400">Multi-Stream Engine & AI Co-Host</p>
        </div>
      </div>

      {/* Global Status & Quick Controls */}
      <div className="flex items-center gap-4">
        {/* Backend Connection Indicator */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              isBackendConnected ? "bg-emerald-400 animate-pulse" : "bg-rose-500"
            }`}
          />
          <span className="text-slate-300 font-medium">
            {isBackendConnected ? "Backend Online" : "Backend Disconnected"}
          </span>
          {isBackendConnected && uptimeSeconds > 0 && (
            <span className="text-slate-500 border-l border-slate-800 pl-2">
              Uptime: {formatUptime(uptimeSeconds)}
            </span>
          )}
        </div>

        {/* Stream Capacity Pill */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs text-slate-300">
          <Radio className="w-3.5 h-3.5 text-cyan-400" />
          <span>4 Streams Capacity</span>
        </div>

        {/* Emergency Stop Shell */}
        <button
          disabled={!isBackendConnected}
          title="Emergency Stop Automation (Disabled until stream session is active)"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-950/40 border border-rose-800/30 text-rose-300 text-xs font-medium hover:bg-rose-900/40 transition disabled:opacity-50 cursor-not-allowed"
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Emergency Halt</span>
        </button>
      </div>
    </header>
  );
}
