"use client";

import React, { useState } from "react";
import { Radio, Users, MessageSquare, Plus, StopCircle, CheckCircle2, AlertCircle } from "lucide-react";
import { StreamSessionSummary } from "@/lib/types";
import { connectStream, stopStream } from "@/lib/api";

interface StreamOverviewShellProps {
  sessions: StreamSessionSummary[];
  onRefresh: () => void;
}

export function StreamOverviewShell({ sessions, onRefresh }: StreamOverviewShellProps) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [streamInput, setStreamInput] = useState("");
  const [showInput, setShowInput] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Maximum 4 slots
  const MAX_SLOTS = 4;
  const slots = [];

  for (let i = 0; i < MAX_SLOTS; i++) {
    const session = sessions[i];
    slots.push({
      slotNumber: i + 1,
      session: session || null,
    });
  }

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!streamInput.trim()) return;

    try {
      setIsConnecting(true);
      setActionError(null);
      await connectStream(streamInput.trim());
      setStreamInput("");
      setShowInput(false);
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || "Failed to connect stream");
    } finally {
      setIsConnecting(false);
    }
  };

  const handleStop = async (streamId: string) => {
    try {
      setActionError(null);
      await stopStream(streamId);
      onRefresh();
    } catch (err: any) {
      setActionError(err.message || "Failed to stop stream");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-slate-200">
              Multi-Stream Orchestration ({sessions.length}/4 Active)
            </h2>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-400 border border-blue-800/40">
              Milestone 1 Engine
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Isolated stream sessions with independent live chat workers and error boundaries.
          </p>
        </div>

        {/* Connect Action Button */}
        <div className="flex items-center gap-2">
          {sessions.length < MAX_SLOTS && (
            <button
              onClick={() => setShowInput(!showInput)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Connect Stream</span>
            </button>
          )}
        </div>
      </div>

      {/* Connect Stream Quick Input */}
      {showInput && (
        <form
          onSubmit={handleConnect}
          className="p-3 rounded-xl bg-slate-900 border border-blue-500/30 flex flex-col sm:flex-row items-center gap-3"
        >
          <input
            type="text"
            value={streamInput}
            onChange={(e) => setStreamInput(e.target.value)}
            placeholder="Enter YouTube Video / Live Stream ID..."
            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 w-full"
            disabled={isConnecting}
          />
          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <button
              type="submit"
              disabled={isConnecting || !streamInput.trim()}
              className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition disabled:opacity-50"
            >
              {isConnecting ? "Connecting..." : "Launch Session"}
            </button>
            <button
              type="button"
              onClick={() => setShowInput(false)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {actionError && (
        <div className="p-2.5 rounded-lg bg-rose-950/60 border border-rose-800/50 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
          <span>{actionError}</span>
        </div>
      )}

      {/* 4 Stream Capacity Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {slots.map((slot) => {
          const session = slot.session;

          if (session) {
            return (
              <div
                key={session.stream_id}
                className="p-4 rounded-xl bg-slate-900/90 border border-blue-500/30 shadow-lg flex flex-col justify-between space-y-3"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5 truncate">
                      <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse shrink-0" />
                      <span className="truncate">{session.title || session.stream_id}</span>
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/40 shrink-0">
                      {session.status}
                    </span>
                  </div>

                  <p className="text-[10px] font-mono text-slate-400 truncate">
                    ID: {session.stream_id}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-[10px] font-mono text-slate-300">
                  <div className="flex items-center gap-1">
                    <Users className="w-3 h-3 text-cyan-400" />
                    <span>{session.concurrent_viewers} viewers</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <MessageSquare className="w-3 h-3 text-cyan-400" />
                    <span>{session.messages_received} msgs</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between">
                  <span className="text-[10px] text-slate-500 font-mono">
                    Uptime: {Math.round(session.uptime_seconds || 0)}s
                  </span>
                  <button
                    onClick={() => handleStop(session.stream_id)}
                    className="flex items-center gap-1 text-[11px] font-medium text-rose-400 hover:text-rose-300 transition"
                  >
                    <StopCircle className="w-3 h-3" />
                    <span>Stop</span>
                  </button>
                </div>
              </div>
            );
          }

          // Empty Standby Slot
          return (
            <div
              key={slot.slotNumber}
              className="p-4 rounded-xl bg-slate-900/30 border border-dashed border-slate-800 flex flex-col justify-between space-y-3"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                    <Radio className="w-3.5 h-3.5 text-slate-600" />
                    Slot #{slot.slotNumber}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-500 border border-slate-700/40">
                    STANDBY
                  </span>
                </div>
                <p className="text-[11px] text-slate-500">Available for live stream session</p>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/40 text-[10px] font-mono text-slate-600">
                <div className="flex items-center gap-1">
                  <Users className="w-3 h-3 text-slate-600" />
                  <span>0 viewers</span>
                </div>
                <div className="flex items-center gap-1">
                  <MessageSquare className="w-3 h-3 text-slate-600" />
                  <span>0 msgs</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
