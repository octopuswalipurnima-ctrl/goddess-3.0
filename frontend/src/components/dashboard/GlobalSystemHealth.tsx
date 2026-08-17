"use client";

import React from "react";
import { SystemHealthData, ConnectionState } from "@/lib/types";
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Radio,
  Cpu,
  Shield,
  Bot,
  Layers,
  Database,
  Server,
  Wifi,
  WifiOff,
} from "lucide-react";

interface Props {
  health: SystemHealthData | null;
  connectionState: ConnectionState;
}

export function GlobalSystemHealth({ health, connectionState }: Props) {
  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "HEALTHY":
        return {
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
          bg: "bg-emerald-950/40 text-emerald-300 border-emerald-800/60",
          label: "HEALTHY",
        };
      case "DEGRADED":
        return {
          icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
          bg: "bg-amber-950/40 text-amber-300 border-amber-800/60",
          label: "DEGRADED",
        };
      case "NOT_CONFIGURED":
        return {
          icon: <HelpCircle className="w-3.5 h-3.5 text-slate-400" />,
          bg: "bg-slate-900 text-slate-400 border-slate-700",
          label: "NOT CONFIGURED",
        };
      case "UNAVAILABLE":
      case "ERROR":
      case "FAILED":
        return {
          icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
          bg: "bg-rose-950/40 text-rose-300 border-rose-800/60",
          label: status,
        };
      default:
        return {
          icon: <HelpCircle className="w-3.5 h-3.5 text-slate-500" />,
          bg: "bg-slate-900/60 text-slate-500 border-slate-800",
          label: "UNKNOWN",
        };
    }
  };

  const comps = health?.components || ({} as any);

  const subsystems = [
    { key: "youtube", label: "YouTube Engine", icon: <Radio className="w-4 h-4 text-red-400" /> },
    { key: "gemini", label: "Gemini AI Engine", icon: <Cpu className="w-4 h-4 text-cyan-400" /> },
    { key: "moderation", label: "AI Moderation", icon: <Shield className="w-4 h-4 text-amber-400" /> },
    { key: "cohost", label: "AI Co-Host", icon: <Bot className="w-4 h-4 text-purple-400" /> },
    { key: "modules", label: "Module System", icon: <Layers className="w-4 h-4 text-blue-400" /> },
    { key: "database", label: "PostgreSQL", icon: <Database className="w-4 h-4 text-slate-400" /> },
    { key: "redis", label: "Redis Cache", icon: <Server className="w-4 h-4 text-slate-400" /> },
  ];

  return (
    <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
            Global Subsystem Telemetry
          </h2>
        </div>

        {/* WebSocket Real-time Status */}
        <div className="flex items-center gap-2">
          <div
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono border ${
              connectionState === "CONNECTED"
                ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/80"
                : connectionState === "RECONNECTING"
                ? "bg-amber-950/60 text-amber-300 border-amber-800/80 animate-pulse"
                : "bg-rose-950/60 text-rose-300 border-rose-800/80"
            }`}
          >
            {connectionState === "CONNECTED" ? (
              <Wifi className="w-3 h-3 text-emerald-400" />
            ) : (
              <WifiOff className="w-3 h-3 text-rose-400" />
            )}
            <span>
              {connectionState === "CONNECTED"
                ? "LIVE WS SYNC"
                : connectionState === "RECONNECTING"
                ? "RECONNECTING WS..."
                : "WS OFFLINE (FALLBACK POLLED)"}
            </span>
          </div>

          <span className="text-[11px] font-mono text-slate-400">
            Uptime: {Math.floor((health?.uptime_seconds || 0) / 60)}m
          </span>
        </div>
      </div>

      {/* Subsystems Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
        {subsystems.map((sub) => {
          const compData = comps[sub.key];
          const badge = getStatusBadge(compData?.status);
          return (
            <div
              key={sub.key}
              className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between space-y-2 hover:border-slate-700 transition"
            >
              <div className="flex items-center gap-2">
                {sub.icon}
                <span className="text-xs font-semibold text-slate-300 truncate">{sub.label}</span>
              </div>
              <div className="flex items-center justify-between">
                <span
                  className={`inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded border ${badge.bg}`}
                >
                  {badge.icon}
                  <span>{badge.label}</span>
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
