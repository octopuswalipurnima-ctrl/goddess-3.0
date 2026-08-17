"use client";

import React, { useState } from "react";
import {
  Shield,
  Bot,
  Layers,
  Sparkles,
  PlayCircle,
  AlertOctagon,
  Power,
  RefreshCw,
  Sliders,
  Check,
} from "lucide-react";
import { updateModerationConfig, updateCoHostConfig, updateStreamModuleConfig, stopStream } from "@/lib/api";

interface Props {
  streamId: string;
  onRefresh: () => void;
}

export function StreamControlCenter({ streamId, onRefresh }: Props) {
  const [modEnabled, setModEnabled] = useState(true);
  const [modDryRun, setModDryRun] = useState(true);
  const [modSafeMode, setModSafeMode] = useState(false);
  const [modKillSwitch, setModKillSwitch] = useState(false);

  const [cohostEnabled, setCohostEnabled] = useState(false);
  const [cohostDryRun, setCohostDryRun] = useState(true);
  const [cohostEmergencyStop, setCohostEmergencyStop] = useState(false);

  const [commandsEnabled, setCommandsEnabled] = useState(true);
  const [welcomeEnabled, setWelcomeEnabled] = useState(false);
  const [statsEnabled, setStatsEnabled] = useState(true);
  const [viewerInteractionEnabled, setViewerInteractionEnabled] = useState(true);

  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleApplySettings = async () => {
    setIsSaving(true);
    setStatusMsg(null);
    try {
      // 1. Update Moderation
      await updateModerationConfig(streamId, {
        enabled: modEnabled,
        dry_run: modDryRun,
        safe_mode: modSafeMode,
        kill_switch: modKillSwitch,
      });

      // 2. Update Co-Host
      await updateCoHostConfig(streamId, {
        enabled: cohostEnabled,
        dry_run: cohostDryRun,
        emergency_stop: cohostEmergencyStop,
      });

      // 3. Update Stream Modules
      await Promise.all([
        updateStreamModuleConfig("commands", streamId, commandsEnabled),
        updateStreamModuleConfig("welcome", streamId, welcomeEnabled),
        updateStreamModuleConfig("stream_stats", streamId, statsEnabled),
        updateStreamModuleConfig("viewer_interaction", streamId, viewerInteractionEnabled),
      ]);

      setStatusMsg("Configuration applied successfully.");
      onRefresh();
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message || "Failed to update configuration"}`);
    } finally {
      setIsSaving(false);
      setTimeout(() => setStatusMsg(null), 4000);
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-blue-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wide">
              Stream Control Center: <span className="text-blue-400 font-mono">{streamId}</span>
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure stream-specific moderation, AI co-host, and modular extensions. State is completely isolated.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {statusMsg && (
            <span
              className={`text-xs font-mono px-2 py-1 rounded border ${
                statusMsg.startsWith("Error")
                  ? "bg-rose-950/60 text-rose-300 border-rose-800"
                  : "bg-emerald-950/60 text-emerald-300 border-emerald-800"
              }`}
            >
              {statusMsg}
            </span>
          )}

          <button
            onClick={handleApplySettings}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/40 transition disabled:opacity-50"
          >
            {isSaving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
            <span>Save & Apply</span>
          </button>
        </div>
      </div>

      {/* Control Switchboards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Moderation Controls */}
        <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800/60">
            <Shield className="w-4 h-4 text-amber-400" />
            <h3 className="text-xs font-bold text-slate-200">AI Moderation Policy</h3>
          </div>

          <div className="space-y-2.5">
            <label className="flex items-center justify-between text-xs cursor-pointer">
              <span className="text-slate-300">Auto-Moderation</span>
              <input
                type="checkbox"
                checked={modEnabled}
                onChange={(e) => setModEnabled(e.target.checked)}
                className="w-4 h-4 accent-amber-500 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between text-xs cursor-pointer">
              <span className="text-slate-300">DRY-RUN Mode</span>
              <input
                type="checkbox"
                checked={modDryRun}
                onChange={(e) => setModDryRun(e.target.checked)}
                className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between text-xs cursor-pointer">
              <span className="text-slate-300">Safe Mode (AI Only)</span>
              <input
                type="checkbox"
                checked={modSafeMode}
                onChange={(e) => setModSafeMode(e.target.checked)}
                className="w-4 h-4 accent-blue-500 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between text-xs cursor-pointer text-rose-400 font-semibold">
              <span>Emergency Kill Switch</span>
              <input
                type="checkbox"
                checked={modKillSwitch}
                onChange={(e) => setModKillSwitch(e.target.checked)}
                className="w-4 h-4 accent-rose-600 rounded cursor-pointer"
              />
            </label>
          </div>
        </div>

        {/* Co-Host Controls */}
        <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800/60">
            <Bot className="w-4 h-4 text-purple-400" />
            <h3 className="text-xs font-bold text-slate-200">Interactive AI Co-Host</h3>
          </div>

          <div className="space-y-2.5">
            <label className="flex items-center justify-between text-xs cursor-pointer">
              <span className="text-slate-300">Co-Host Public Replies</span>
              <input
                type="checkbox"
                checked={cohostEnabled}
                onChange={(e) => setCohostEnabled(e.target.checked)}
                className="w-4 h-4 accent-purple-500 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between text-xs cursor-pointer">
              <span className="text-slate-300">DRY-RUN Mode</span>
              <input
                type="checkbox"
                checked={cohostDryRun}
                onChange={(e) => setCohostDryRun(e.target.checked)}
                className="w-4 h-4 accent-cyan-500 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between text-xs cursor-pointer text-rose-400 font-semibold">
              <span>Emergency Stop</span>
              <input
                type="checkbox"
                checked={cohostEmergencyStop}
                onChange={(e) => setCohostEmergencyStop(e.target.checked)}
                className="w-4 h-4 accent-rose-600 rounded cursor-pointer"
              />
            </label>
          </div>
        </div>

        {/* Modular Extensions */}
        <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 space-y-3">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800/60">
            <Layers className="w-4 h-4 text-blue-400" />
            <h3 className="text-xs font-bold text-slate-200">Stream Extension Modules</h3>
          </div>

          <div className="space-y-2.5">
            <label className="flex items-center justify-between text-xs cursor-pointer">
              <span className="text-slate-300">Chat Commands (!help, etc.)</span>
              <input
                type="checkbox"
                checked={commandsEnabled}
                onChange={(e) => setCommandsEnabled(e.target.checked)}
                className="w-4 h-4 accent-blue-500 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between text-xs cursor-pointer">
              <span className="text-slate-300">Viewer Welcome</span>
              <input
                type="checkbox"
                checked={welcomeEnabled}
                onChange={(e) => setWelcomeEnabled(e.target.checked)}
                className="w-4 h-4 accent-blue-500 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between text-xs cursor-pointer">
              <span className="text-slate-300">Live Stream Stats</span>
              <input
                type="checkbox"
                checked={statsEnabled}
                onChange={(e) => setStatsEnabled(e.target.checked)}
                className="w-4 h-4 accent-blue-500 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between text-xs cursor-pointer">
              <span className="text-slate-300">Viewer Interaction Tracking</span>
              <input
                type="checkbox"
                checked={viewerInteractionEnabled}
                onChange={(e) => setViewerInteractionEnabled(e.target.checked)}
                className="w-4 h-4 accent-blue-500 rounded cursor-pointer"
              />
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
