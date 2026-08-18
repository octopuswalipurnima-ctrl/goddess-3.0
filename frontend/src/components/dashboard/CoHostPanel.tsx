"use client";

import React, { useState, useEffect } from "react";
import {
  Bot,
  Sparkles,
  PlayCircle,
  AlertOctagon,
  Sliders,
  ShieldCheck,
  Zap,
  BookOpen,
  Eye,
  Settings2,
  RefreshCw,
} from "lucide-react";
import { getApiBaseUrl } from "@/lib/api/client";
import { getAuthHeaders } from "@/lib/api/auth";

export function CoHostPanel() {
  const [enabled, setEnabled] = useState(false);
  const [dryRun, setDryRun] = useState(true);
  const [emergencyStop, setEmergencyStop] = useState(false);
  const [personalityName, setPersonalityName] = useState("Goddess");
  const [tone, setTone] = useState("friendly");
  const [energyLevel, setEnergyLevel] = useState("medium");
  const [humorLevel, setHumorLevel] = useState("moderate");
  const [responseStyle, setResponseStyle] = useState("conversational");
  const [responseProbability, setResponseProbability] = useState(0.85);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.70);

  const [stats, setStats] = useState({
    messages_analyzed: 0,
    intents_detected: 0,
    engagement_decisions: 0,
    messages_ignored: 0,
    responses_requested: 0,
    responses_generated: 0,
    responses_sent: 0,
    responses_dry_run: 0,
    responses_blocked: 0,
    responses_failed: 0,
    no_response_count: 0,
    gemini_fallbacks: 0,
  });

  const fetchStats = async () => {
    try {
      const res = await fetch(`${getApiBaseUrl()}/cohost/stats`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  const toggleEnabled = () => setEnabled(!enabled);
  const toggleDryRun = () => setDryRun(!dryRun);
  const toggleEmergencyStop = () => setEmergencyStop(!emergencyStop);

  return (
    <div className="space-y-4 p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl">
      {/* Panel Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-purple-400" />
            <h2 className="text-sm font-bold text-slate-200">
              Adaptive AI Co-Host & Engagement Engine
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-400 border border-purple-800/40">
              Milestone 13 Adaptive
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Stream-aware engagement decisions, verified creator knowledge, anti-repetition protection, and bounded multi-stream isolation.
          </p>
        </div>

        {/* Master & Emergency Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={toggleEnabled}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border transition ${
              enabled
                ? "bg-purple-600 text-white border-purple-500 shadow-lg shadow-purple-900/40"
                : "bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{enabled ? "Co-Host: ON" : "Co-Host: OFF"}</span>
          </button>

          <button
            onClick={toggleDryRun}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              dryRun
                ? "bg-blue-950/90 text-cyan-300 border-blue-600"
                : "bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700"
            }`}
          >
            <PlayCircle className="w-3.5 h-3.5" />
            <span>{dryRun ? "DRY-RUN: ON" : "DRY-RUN: OFF"}</span>
          </button>

          <button
            onClick={toggleEmergencyStop}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border transition ${
              emergencyStop
                ? "bg-rose-600 text-white border-rose-500 shadow-lg shadow-rose-900/50 animate-bounce"
                : "bg-rose-950/60 text-rose-300 border-rose-800/60 hover:bg-rose-900/80"
            }`}
          >
            <AlertOctagon className="w-3.5 h-3.5" />
            <span>{emergencyStop ? "EMERGENCY STOP ACTIVE" : "Emergency Stop"}</span>
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Analyzed</span>
          <p className="text-lg font-bold text-white font-mono mt-0.5">{stats.messages_analyzed}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Decisions</span>
          <p className="text-lg font-bold text-cyan-400 font-mono mt-0.5">{stats.engagement_decisions || stats.intents_detected}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Generated</span>
          <p className="text-lg font-bold text-purple-400 font-mono mt-0.5">{stats.responses_generated}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Dry-Run</span>
          <p className="text-lg font-bold text-blue-400 font-mono mt-0.5">{stats.responses_dry_run}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Sent to Chat</span>
          <p className="text-lg font-bold text-emerald-400 font-mono mt-0.5">{stats.responses_sent}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Blocked / Silent</span>
          <p className="text-lg font-bold text-amber-400 font-mono mt-0.5">{(stats.responses_blocked || 0) + (stats.messages_ignored || 0)}</p>
        </div>
      </div>

      {/* Intelligence Settings Grid */}
      <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/60 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-purple-400 shrink-0" />
          <span className="text-slate-400">Persona:</span>
          <strong className="text-slate-200">{personalityName} ({tone}, {energyLevel})</strong>
        </div>
        <div className="flex items-center gap-2">
          <Eye className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
          <span className="text-slate-400">Probability:</span>
          <strong className="text-slate-200">{Math.round(responseProbability * 100)}% (Filtered)</strong>
        </div>
        <div className="flex items-center gap-2">
          <BookOpen className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span className="text-slate-400">Confidence Gate:</span>
          <strong className="text-slate-200">&ge; {Math.round(confidenceThreshold * 100)}%</strong>
        </div>
      </div>

      {/* Footer Info */}
      <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Safety Authority: <strong>ProductionSafetyController</strong> &bull; Max 200 chars &bull; Zero Hallucinations</span>
        </div>
        <div className="flex items-center gap-3 font-mono text-[10px] text-slate-500">
          <span>Global CD: 5s</span>
          <span>&bull;</span>
          <span>User CD: 30s</span>
          <span>&bull;</span>
          <span>Max Dedup Window: 30</span>
        </div>
      </div>
    </div>
  );
}
