"use client";

import React, { useEffect, useState } from "react";
import { ModuleSummaryItem } from "@/lib/types";
import { disableModule, enableModule, fetchModules, startModule, stopModule } from "@/lib/api";
import { Layers, CheckCircle2, AlertTriangle, XCircle, Play, Square, Power, RefreshCw } from "lucide-react";

export function ModuleCenter() {
  const [modules, setModules] = useState<ModuleSummaryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadModules = async () => {
    try {
      setIsLoading(true);
      const data = await fetchModules();
      setModules(data);
    } catch (err) {} finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadModules();
    const interval = setInterval(loadModules, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleEnable = async (mod: ModuleSummaryItem) => {
    try {
      if (mod.status === "ENABLED" || mod.status === "RUNNING") {
        await disableModule(mod.id);
        setActionMsg(`Disabled module ${mod.name}`);
      } else {
        await enableModule(mod.id);
        setActionMsg(`Enabled module ${mod.name}`);
      }
      loadModules();
    } catch (err: any) {
      setActionMsg(`Error: ${err.message}`);
    } finally {
      setTimeout(() => setActionMsg(null), 3000);
    }
  };

  const handleToggleRun = async (mod: ModuleSummaryItem) => {
    try {
      if (mod.status === "RUNNING") {
        await stopModule(mod.id);
        setActionMsg(`Stopped module ${mod.name}`);
      } else {
        await startModule(mod.id);
        setActionMsg(`Started module ${mod.name}`);
      }
      loadModules();
    } catch (err: any) {
      setActionMsg(`Error: ${err.message}`);
    } finally {
      setTimeout(() => setActionMsg(null), 3000);
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-400" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
            Modular Extension System Center
          </h2>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800/40">
            {modules.filter((m) => m.status === "RUNNING").length}/{modules.length} Running
          </span>
        </div>

        <div className="flex items-center gap-2">
          {actionMsg && (
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
              {actionMsg}
            </span>
          )}
          <button
            onClick={loadModules}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1 font-mono transition"
          >
            <RefreshCw className={`w-3 h-3 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {modules.map((mod) => (
          <div
            key={mod.id}
            className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col justify-between space-y-3"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-white">{mod.name}</h3>
                  <span className="text-[10px] font-mono text-slate-500">v{mod.version}</span>
                </div>
                <span className="text-[10px] font-mono text-slate-400">{mod.id}</span>
              </div>

              <div className="flex items-center gap-1.5">
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                    mod.health === "HEALTHY"
                      ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                      : "bg-rose-950 text-rose-300 border-rose-800"
                  }`}
                >
                  {mod.health}
                </span>
                <span
                  className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                    mod.status === "RUNNING"
                      ? "bg-blue-950 text-blue-300 border-blue-800"
                      : "bg-slate-800 text-slate-400 border-slate-700"
                  }`}
                >
                  {mod.status}
                </span>
              </div>
            </div>

            {/* Capabilities */}
            <div className="flex flex-wrap gap-1">
              {mod.capabilities.map((cap) => (
                <span
                  key={cap}
                  className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800"
                >
                  {cap}
                </span>
              ))}
            </div>

            {/* Controls */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
              <span className="text-[10px] text-slate-400">
                Active on {mod.active_streams.length} stream(s)
              </span>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleToggleEnable(mod)}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold border transition ${
                    mod.status === "ENABLED" || mod.status === "RUNNING"
                      ? "bg-amber-950/60 text-amber-300 border-amber-800 hover:bg-amber-900/60"
                      : "bg-emerald-950/60 text-emerald-300 border-emerald-800 hover:bg-emerald-900/60"
                  }`}
                >
                  <Power className="w-3 h-3" />
                  <span>{mod.status === "ENABLED" || mod.status === "RUNNING" ? "Disable" : "Enable"}</span>
                </button>

                <button
                  onClick={() => handleToggleRun(mod)}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold border transition ${
                    mod.status === "RUNNING"
                      ? "bg-rose-950/60 text-rose-300 border-rose-800 hover:bg-rose-900/60"
                      : "bg-blue-950/60 text-blue-300 border-blue-800 hover:bg-blue-900/60"
                  }`}
                >
                  {mod.status === "RUNNING" ? <Square className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                  <span>{mod.status === "RUNNING" ? "Stop" : "Start"}</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
