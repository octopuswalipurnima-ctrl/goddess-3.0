"use client";

import React from "react";
import { RefreshCw, Shield, Bot, Terminal, Trophy, Check, X } from "lucide-react";

interface QuickControlsProps {
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function QuickControls({ onRefresh, isRefreshing }: QuickControlsProps) {
  const modules = [
    { name: "AI Moderation", icon: Shield, phase: "Phase 5", enabled: false },
    { name: "AI Co-Host", icon: Bot, phase: "Phase 6", enabled: false },
    { name: "Nightbot Commands", icon: Terminal, phase: "Phase 7", enabled: false },
    { name: "Viewer XP & VIP", icon: Trophy, phase: "Phase 8", enabled: false },
  ];

  return (
    <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xs font-semibold text-slate-200">Module Switchboard Preview</h2>
          <p className="text-[11px] text-slate-400">
            Plug-and-play architecture modules (enabled per-stream or globally in subsequent phases)
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-blue-400" : ""}`} />
          <span>{isRefreshing ? "Checking..." : "Refresh Health"}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
        {modules.map((mod) => {
          const Icon = mod.icon;
          return (
            <div
              key={mod.name}
              className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex items-center justify-between"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-md bg-slate-900 flex items-center justify-center text-slate-400">
                  <Icon className="w-3.5 h-3.5" />
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-300">{mod.name}</p>
                  <p className="text-[10px] text-slate-400 font-mono">{mod.phase}</p>
                </div>
              </div>

              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 flex items-center gap-1">
                <X className="w-2.5 h-2.5 text-slate-500" />
                Standby
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
