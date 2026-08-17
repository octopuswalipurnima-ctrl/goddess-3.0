"use client";

import React, { useState } from "react";
import { AlertOctagon, ShieldAlert, Power, Bot, AlertTriangle, X, Check } from "lucide-react";
import { stopStream, updateCoHostConfig, updateModerationConfig } from "@/lib/api";

interface Props {
  streamId: string;
  onActionComplete: () => void;
}

export function EmergencyControls({ streamId, onActionComplete }: Props) {
  const [modalAction, setModalAction] = useState<"KILL_MOD" | "STOP_COHOST" | "STOP_STREAM" | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleExecuteEmergency = async () => {
    if (!modalAction) return;
    setIsProcessing(true);
    setFeedback(null);

    try {
      if (modalAction === "KILL_MOD") {
        await updateModerationConfig(streamId, { kill_switch: true });
        setFeedback("Emergency Moderation Kill Switch ENGAGED.");
      } else if (modalAction === "STOP_COHOST") {
        await updateCoHostConfig(streamId, { emergency_stop: true });
        setFeedback("AI Co-Host Emergency Stop ENGAGED.");
      } else if (modalAction === "STOP_STREAM") {
        await stopStream(streamId);
        setFeedback(`Stream session ${streamId} terminated.`);
      }
      onActionComplete();
    } catch (err: any) {
      setFeedback(`Failed to execute emergency action: ${err.message}`);
    } finally {
      setIsProcessing(false);
      setModalAction(null);
      setTimeout(() => setFeedback(null), 5000);
    }
  };

  return (
    <div className="p-4 rounded-2xl bg-rose-950/30 border border-rose-900/60 shadow-xl space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-rose-400" />
          <h2 className="text-sm font-bold text-rose-300 uppercase tracking-wide">
            Emergency Master Controls ({streamId})
          </h2>
        </div>
        <span className="text-[10px] font-mono text-rose-400">
          Requires Confirmation &bull; High Impact
        </span>
      </div>

      {feedback && (
        <div className="p-2 rounded-xl bg-slate-900 border border-rose-800 text-xs font-mono text-rose-200">
          {feedback}
        </div>
      )}

      {/* Emergency Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <button
          onClick={() => setModalAction("KILL_MOD")}
          className="p-3 rounded-xl bg-rose-900/40 hover:bg-rose-900/70 border border-rose-800 text-rose-200 flex items-center justify-center gap-2 font-bold text-xs transition shadow-lg shadow-rose-950/50"
        >
          <ShieldAlert className="w-4 h-4 text-rose-400" />
          <span>Moderation Kill Switch</span>
        </button>

        <button
          onClick={() => setModalAction("STOP_COHOST")}
          className="p-3 rounded-xl bg-purple-900/40 hover:bg-purple-900/70 border border-purple-800 text-purple-200 flex items-center justify-center gap-2 font-bold text-xs transition shadow-lg shadow-purple-950/50"
        >
          <Bot className="w-4 h-4 text-purple-400" />
          <span>Co-Host Emergency Stop</span>
        </button>

        <button
          onClick={() => setModalAction("STOP_STREAM")}
          className="p-3 rounded-xl bg-slate-900/80 hover:bg-slate-900 border border-slate-700 text-slate-300 flex items-center justify-center gap-2 font-bold text-xs transition"
        >
          <Power className="w-4 h-4 text-slate-400" />
          <span>Stop Stream Session</span>
        </button>
      </div>

      {/* Confirmation Modal */}
      {modalAction && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-rose-800 p-6 rounded-2xl max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <AlertTriangle className="w-6 h-6 shrink-0" />
              <h3 className="text-base font-bold text-white">Confirm Emergency Action</h3>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              {modalAction === "KILL_MOD" &&
                `Are you sure you want to ENGAGE the Moderation Kill Switch on ${streamId}? Automated actions will be immediately stopped.`}
              {modalAction === "STOP_COHOST" &&
                `Are you sure you want to ENGAGE the Co-Host Emergency Stop on ${streamId}? All public AI replies will halt immediately.`}
              {modalAction === "STOP_STREAM" &&
                `Are you sure you want to terminate the live stream session for ${streamId}? Background polling and chat readers will be cancelled.`}
            </p>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setModalAction(null)}
                disabled={isProcessing}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Cancel
              </button>

              <button
                onClick={handleExecuteEmergency}
                disabled={isProcessing}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-900/50 transition flex items-center gap-1.5"
              >
                {isProcessing ? (
                  <span>Executing...</span>
                ) : (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Confirm & Execute</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
