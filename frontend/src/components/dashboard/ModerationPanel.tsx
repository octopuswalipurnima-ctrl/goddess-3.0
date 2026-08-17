"use client";

import React, { useState, useEffect } from "react";
import { Shield, ShieldAlert, ShieldCheck, Zap, AlertTriangle, CheckCircle, XCircle, Sliders, PlayCircle, RotateCcw } from "lucide-react";

export function ModerationPanel() {
  const [killSwitch, setKillSwitch] = useState(false);
  const [safeMode, setSafeMode] = useState(false);
  const [dryRun, setDryRun] = useState(true);
  const [circuitBreakerTripped, setCircuitBreakerTripped] = useState(false);
  const [stats, setStats] = useState({
    messages_analyzed: 0,
    rule_matches: 0,
    ai_classifications: 0,
    actions_executed: 0,
    actions_dry_run: 0,
    actions_blocked: 0,
    ai_failures: 0,
    circuit_breaker_trips: 0,
  });

  const fetchModerationStats = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/moderation/stats");
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      // Backend polling error
    }
  };

  useEffect(() => {
    fetchModerationStats();
    const interval = setInterval(fetchModerationStats, 4000);
    return () => clearInterval(interval);
  }, []);

  const toggleKillSwitch = () => {
    setKillSwitch(!killSwitch);
  };

  const toggleSafeMode = () => {
    setSafeMode(!safeMode);
  };

  const toggleDryRun = () => {
    setDryRun(!dryRun);
  };

  const handleResetCircuitBreaker = async () => {
    setCircuitBreakerTripped(false);
    try {
      await fetch("http://127.0.0.1:8000/api/v1/moderation/circuit-breaker/reset/default_stream", {
        method: "POST",
      });
      fetchModerationStats();
    } catch (e) {}
  };

  return (
    <div className="space-y-4 p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl">
      {/* Panel Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-bold text-slate-200">
              3-Tier AI Moderation Engine
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/40">
              Milestone 3 Live
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Deterministic rules + Gemini AI semantic analysis with Action Policy safety gates.
          </p>
        </div>

        {/* Emergency & Policy Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {circuitBreakerTripped && (
            <button
              onClick={handleResetCircuitBreaker}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-rose-950 text-rose-300 border border-rose-600 text-xs font-bold animate-pulse hover:bg-rose-900 transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Circuit Breaker</span>
            </button>
          )}

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
            onClick={toggleSafeMode}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              safeMode
                ? "bg-amber-950/80 text-amber-300 border-amber-600 animate-pulse"
                : "bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700"
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>{safeMode ? "Safe Mode: ON" : "Safe Mode: OFF"}</span>
          </button>

          <button
            onClick={toggleKillSwitch}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border transition ${
              killSwitch
                ? "bg-rose-600 text-white border-rose-500 shadow-lg shadow-rose-900/50 animate-bounce"
                : "bg-rose-950/60 text-rose-300 border-rose-800/60 hover:bg-rose-900/80"
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>{killSwitch ? "KILL SWITCH ACTIVE" : "Kill Switch"}</span>
          </button>
        </div>
      </div>

      {/* Moderation Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Analyzed</span>
          <p className="text-lg font-bold text-white font-mono mt-0.5">{stats.messages_analyzed}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Rule Matches</span>
          <p className="text-lg font-bold text-cyan-400 font-mono mt-0.5">{stats.rule_matches}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">AI Classifications</span>
          <p className="text-lg font-bold text-purple-400 font-mono mt-0.5">{stats.ai_classifications}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Dry-Run Actions</span>
          <p className="text-lg font-bold text-blue-400 font-mono mt-0.5">{stats.actions_dry_run}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Actions Executed</span>
          <p className="text-lg font-bold text-emerald-400 font-mono mt-0.5">{stats.actions_executed}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
          <span className="text-[10px] text-slate-400 font-mono">Actions Blocked</span>
          <p className="text-lg font-bold text-amber-400 font-mono mt-0.5">{stats.actions_blocked}</p>
        </div>
      </div>

      {/* Feed Placeholder / Status Note */}
      <div className="p-3 rounded-xl bg-slate-950/40 border border-slate-800/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-400">
        <div className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-emerald-400" />
          <span>Real-time moderation event pipeline active on Event Bus.</span>
        </div>
        <div className="flex items-center gap-3 font-mono text-[10px] text-slate-500">
          <span>Fail-Safe: Active (AI Failure != SAFE)</span>
          <span>&bull;</span>
          <span>Circuit Breaker: {circuitBreakerTripped ? "TRIPPED" : "ARMED"}</span>
        </div>
      </div>
    </div>
  );
}
