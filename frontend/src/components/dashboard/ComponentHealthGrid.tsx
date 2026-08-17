"use client";

import React from "react";
import { Database, HardDrive, Youtube, Sparkles, CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import { ComponentStatus, HealthStatus } from "@/lib/types";

interface ComponentHealthGridProps {
  components?: {
    database?: ComponentStatus;
    redis?: ComponentStatus;
    youtube?: ComponentStatus;
    gemini?: ComponentStatus;
    [key: string]: ComponentStatus | undefined;
  };
}

export function ComponentHealthGrid({ components }: ComponentHealthGridProps) {
  const getStatusBadge = (status: HealthStatus | "DEGRADED" | undefined) => {
    switch (status) {
      case "HEALTHY":
        return {
          bg: "bg-emerald-950/60 text-emerald-300 border-emerald-800/40",
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
          label: "HEALTHY",
        };
      case "DEGRADED":
        return {
          bg: "bg-amber-950/60 text-amber-300 border-amber-800/40",
          icon: <AlertCircle className="w-3.5 h-3.5 text-amber-400" />,
          label: "DEGRADED",
        };
      case "NOT_CONFIGURED":
        return {
          bg: "bg-slate-800/80 text-slate-400 border-slate-700/50",
          icon: <AlertCircle className="w-3.5 h-3.5 text-slate-400" />,
          label: "NOT CONFIGURED",
        };
      case "UNAVAILABLE":
        return {
          bg: "bg-rose-950/50 text-rose-300 border-rose-800/40",
          icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
          label: "UNAVAILABLE",
        };
      case "ERROR":
      default:
        return {
          bg: "bg-rose-950/50 text-rose-300 border-rose-800/40",
          icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
          label: "ERROR",
        };
    }
  };

  const cards = [
    {
      title: "PostgreSQL Database",
      key: "database",
      icon: Database,
      data: components?.database,
      defaultDetails: "PostgreSQL with SQLAlchemy async driver",
      renderMeta: () => null,
    },
    {
      title: "Redis Cache & Pub/Sub",
      key: "redis",
      icon: HardDrive,
      data: components?.redis,
      defaultDetails: "In-memory caching and session coordination",
      renderMeta: () => null,
    },
    {
      title: "YouTube Engine (4 Keys)",
      key: "youtube",
      icon: Youtube,
      data: components?.youtube,
      defaultDetails: "Multi-key credential rotation & Live Chat API",
      renderMeta: (meta: any) => {
        if (!meta) return null;
        return (
          <div className="grid grid-cols-2 gap-1 text-[10px] font-mono text-slate-400 mt-2 pt-2 border-t border-slate-800/50">
            <span>Keys: {meta.available_credentials ?? 0}/{meta.configured_credentials ?? 0}</span>
            <span>Streams: {meta.active_streams ?? 0}/{meta.max_streams ?? 4}</span>
          </div>
        );
      },
    },
    {
      title: "Gemini AI Engine (4 Keys)",
      key: "gemini",
      icon: Sparkles,
      data: components?.gemini,
      defaultDetails: "Flash / Flash-Lite models with priority queue & rate limiting",
      renderMeta: (meta: any) => {
        if (!meta) return null;
        return (
          <div className="space-y-1 text-[10px] font-mono text-slate-400 mt-2 pt-2 border-t border-slate-800/50">
            <div className="flex justify-between">
              <span>Keys: {meta.available_credentials ?? 0}/{meta.configured_credentials ?? 0}</span>
              <span>Reqs: {meta.active_requests ?? 0} active</span>
            </div>
            <div className="flex justify-between text-slate-500 truncate">
              <span>Model: {meta.primary_model || "gemini-2.5-flash"}</span>
            </div>
          </div>
        );
      },
    },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">Subsystem Diagnostics</h2>
        <span className="text-[11px] text-slate-400">Live Backend Component States</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {cards.map((card) => {
          const Icon = card.icon;
          const status = (card.data?.status as any) || "NOT_CONFIGURED";
          const badge = getStatusBadge(status);
          const details = card.data?.details || card.defaultDetails;
          const metadata = card.data?.metadata;

          return (
            <div
              key={card.key}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700/60 transition flex flex-col justify-between"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                    <Icon className="w-4 h-4 text-slate-300" />
                  </div>
                  <div
                    className={`flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-semibold border ${badge.bg}`}
                  >
                    {badge.icon}
                    <span>{badge.label}</span>
                  </div>
                </div>

                <div>
                  <h3 className="text-xs font-semibold text-slate-200">{card.title}</h3>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{details}</p>
                </div>

                {card.renderMeta(metadata)}
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-800/60 text-[10px] text-slate-500 font-mono flex items-center justify-between">
                <span>Phase Readiness</span>
                <span>{status === "HEALTHY" ? "Active" : "Target Ready"}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
