"use client";

import React, { useState } from "react";
import {
  Radio,
  PlayCircle,
  StopCircle,
  RefreshCw,
  Shield,
  ShieldAlert,
  Bot,
  MessageSquare,
  AlertOctagon,
  Eye,
} from "lucide-react";
import { getApiBaseUrl } from "@/lib/api/client";
import { getAuthHeaders } from "@/lib/api/auth";

interface StreamOpsProps {
  streamId: string;
  data?: any;
  onRefresh?: () => void;
}

export function StreamOperationsCard({ streamId, data, onRefresh }: StreamOpsProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const isLive = data?.status === "LIVE";
  const isEmergency = data?.safety_state === "EMERGENCY_STOP";
  const isSafeMode = data?.safe_mode || data?.safety_state === "SAFE_MODE";

  const executeControl = async (endpoint: string, method: string = "POST", body?: any) => {
    try {
      setIsProcessing(true);
      await fetch(`${getApiBaseUrl()}/operations/streams/${streamId}/${endpoint}`, {
        method,
        headers: getAuthHeaders(),
        body: body ? JSON.stringify(body) : undefined,
      });
      if (onRefresh) onRefresh();
    } catch (e) {
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-md space-y-3">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              isLive ? "bg-emerald-500 animate-pulse" : "bg-slate-600"
            }`}
          />
          <h3 className="text-xs font-bold text-white font-mono">{streamId}</h3>
        </div>

        <span
          className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${
            isLive
              ? "bg-emerald-950/60 text-emerald-400 border-emerald-800/40"
              : "bg-slate-800 text-slate-400 border-slate-700"
          }`}
        >
          {data?.status || "OFFLINE"}
        </span>
      </div>

      {/* Info Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="p-2 rounded-lg bg-slate-950/50 border border-slate-800/60">
          <span className="text-[10px] text-slate-500 font-mono">Chat Messages</span>
          <p className="font-mono font-bold text-cyan-400 mt-0.5">
            {data?.messages_received || 0} in / {data?.messages_sent || 0} out
          </p>
        </div>
        <div className="p-2 rounded-lg bg-slate-950/50 border border-slate-800/60">
          <span className="text-[10px] text-slate-500 font-mono">Co-Host / Mod</span>
          <p className="font-mono font-bold text-purple-400 mt-0.5">
            {data?.cohost_responses || 0} resp / {data?.moderation_actions || 0} mod
          </p>
        </div>
      </div>

      {/* Status Badges */}
      <div className="flex flex-wrap gap-1.5 text-[10px] font-mono">
        <span
          className={`px-1.5 py-0.5 rounded ${
            isSafeMode
              ? "bg-amber-950 text-amber-300 border border-amber-800"
              : "bg-slate-950 text-slate-400 border border-slate-800"
          }`}
        >
          SafeMode: {isSafeMode ? "ON" : "OFF"}
        </span>
        <span
          className={`px-1.5 py-0.5 rounded ${
            isEmergency
              ? "bg-rose-950 text-rose-300 border border-rose-800 font-bold"
              : "bg-slate-950 text-slate-400 border border-slate-800"
          }`}
        >
          {isEmergency ? "EMERGENCY STOP" : "Safety: Normal"}
        </span>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-1.5 pt-1">
        <button
          disabled={isProcessing}
          onClick={() => executeControl(isSafeMode ? "safe-mode/disable" : "safe-mode/enable")}
          className="flex-1 py-1 rounded text-[10px] font-bold bg-amber-950/70 text-amber-300 border border-amber-800/60 hover:bg-amber-900 transition"
        >
          {isSafeMode ? "Exit SafeMode" : "Safe Mode"}
        </button>

        <button
          disabled={isProcessing}
          onClick={() => executeControl("reconnect")}
          className="px-2 py-1 rounded text-[10px] font-semibold bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700 transition"
          title="Reconnect Stream"
        >
          <RefreshCw className={`w-3 h-3 ${isProcessing ? "animate-spin" : ""}`} />
        </button>

        <button
          disabled={isProcessing}
          onClick={() => executeControl("emergency-stop")}
          className="px-2 py-1 rounded text-[10px] font-bold bg-rose-950/80 text-rose-300 border border-rose-800 hover:bg-rose-900 transition"
          title="Stream Emergency Stop"
        >
          <AlertOctagon className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
}
