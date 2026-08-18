"use client";

import React, { useState } from "react";
import { AlertOctagon, Shield, ShieldAlert, CheckCircle, RefreshCw } from "lucide-react";
import { getApiBaseUrl } from "@/lib/api/client";
import { getAuthHeaders } from "@/lib/api/auth";

export function SafetyControls() {
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [actionType, setActionType] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const promptAction = (action: string) => {
    setActionType(action);
    setIsConfirmOpen(true);
  };

  const executeAction = async () => {
    setIsSubmitting(true);
    try {
      let endpoint = "";
      if (actionType === "GLOBAL_EMERGENCY_STOP") endpoint = "emergency-stop";
      else if (actionType === "CLEAR_EMERGENCY_STOP") endpoint = "emergency-stop/clear";
      else if (actionType === "GLOBAL_SAFE_MODE") endpoint = "safe-mode/enable";
      else if (actionType === "CLEAR_SAFE_MODE") endpoint = "safe-mode/disable";

      const res = await fetch(`${getApiBaseUrl()}/operations/${endpoint}`, {
        method: "POST",
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        setStatusMsg(`Executed ${actionType} successfully.`);
      } else {
        setStatusMsg(`Failed to execute ${actionType}.`);
      }
    } catch (e) {
      setStatusMsg("Network error communicating with safety controller.");
    } finally {
      setIsSubmitting(false);
      setIsConfirmOpen(false);
      setTimeout(() => setStatusMsg(null), 4000);
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-400" />
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Emergency & Safety Control Center
            </h2>
            <p className="text-xs text-slate-400">
              Immediate fail-safe override switches governed by ProductionSafetyController.
            </p>
          </div>
        </div>

        {statusMsg && (
          <span className="text-xs font-mono font-semibold px-2 py-1 rounded bg-slate-800 text-cyan-400 border border-cyan-800/40">
            {statusMsg}
          </span>
        )}
      </div>

      {/* Main Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <button
          onClick={() => promptAction("GLOBAL_EMERGENCY_STOP")}
          className="p-3.5 rounded-xl bg-rose-600 text-white font-bold text-xs flex items-center justify-center gap-2 hover:bg-rose-500 shadow-lg shadow-rose-950/50 transition border border-rose-400"
        >
          <AlertOctagon className="w-4 h-4" />
          GLOBAL EMERGENCY STOP
        </button>

        <button
          onClick={() => promptAction("CLEAR_EMERGENCY_STOP")}
          className="p-3.5 rounded-xl bg-slate-800 text-slate-200 font-semibold text-xs flex items-center justify-center gap-2 hover:bg-slate-700 transition border border-slate-700"
        >
          <CheckCircle className="w-4 h-4 text-emerald-400" />
          CLEAR EMERGENCY STOP
        </button>

        <button
          onClick={() => promptAction("GLOBAL_SAFE_MODE")}
          className="p-3.5 rounded-xl bg-amber-950/80 text-amber-300 font-semibold text-xs flex items-center justify-center gap-2 hover:bg-amber-900 transition border border-amber-700/60"
        >
          <Shield className="w-4 h-4 text-amber-400" />
          ENABLE SAFE MODE
        </button>

        <button
          onClick={() => promptAction("CLEAR_SAFE_MODE")}
          className="p-3.5 rounded-xl bg-slate-800 text-slate-200 font-semibold text-xs flex items-center justify-center gap-2 hover:bg-slate-700 transition border border-slate-700"
        >
          <CheckCircle className="w-4 h-4 text-cyan-400" />
          DISABLE SAFE MODE
        </button>
      </div>

      {/* Confirmation Modal */}
      {isConfirmOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <AlertOctagon className="w-6 h-6" />
              <h3 className="text-base font-bold text-white">Confirm Safety Action</h3>
            </div>
            <p className="text-xs text-slate-300">
              Are you sure you want to execute <strong className="text-white">{actionType}</strong>?
              This action will be audited and broadcasted immediately.
            </p>
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setIsConfirmOpen(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-xs font-semibold text-slate-300 hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                disabled={isSubmitting}
                onClick={executeAction}
                className="px-4 py-2 rounded-lg bg-rose-600 text-xs font-bold text-white hover:bg-rose-500 shadow-md"
              >
                {isSubmitting ? "Executing..." : "Confirm & Execute"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
