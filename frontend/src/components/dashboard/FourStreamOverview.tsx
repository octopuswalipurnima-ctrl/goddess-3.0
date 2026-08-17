"use client";

import React from "react";
import { StreamSessionSummary, StreamSupervisorSummary } from "@/lib/types";
import { Radio, Users, MessageSquare, Shield, Bot, Layers, ArrowRight, AlertOctagon, ShieldAlert } from "lucide-react";

interface Props {
  streams: StreamSessionSummary[];
  supervisorStreams?: StreamSupervisorSummary[];
  selectedStreamId: string;
  onSelectStream: (streamId: string) => void;
}

const DEFAULT_STREAMS = [
  { id: "STREAM_A", name: "Stream A (Primary)" },
  { id: "STREAM_B", name: "Stream B (Secondary)" },
  { id: "STREAM_C", name: "Stream C (Co-Stream)" },
  { id: "STREAM_D", name: "Stream D (Multicast)" },
];

export function FourStreamOverview({
  streams,
  supervisorStreams = [],
  selectedStreamId,
  onSelectStream,
}: Props) {
  // Map active streams or fallback to default slots
  const slots = DEFAULT_STREAMS.map((def) => {
    const sup = supervisorStreams.find((s) => s.stream_id.toUpperCase() === def.id.toUpperCase() || s.video_id === def.id);
    const active = streams.find((s) => s.stream_id.toUpperCase() === def.id.toUpperCase());

    const isLive = sup ? sup.state === "LIVE" : !!active?.is_live;
    const isReconnecting = sup?.state === "RECONNECTING";
    const isDegraded = sup?.state === "DEGRADED";
    const isSafeMode = sup?.safe_mode || sup?.state === "SAFE_MODE";
    const isEmergency = sup?.emergency_stop;
    const isActive = sup ? sup.state !== "ENDED" && sup.state !== "FAILED" : !!active?.is_active;

    let statusLabel = "OFFLINE";
    let statusClass = "bg-slate-800 text-slate-400 border-slate-700";

    if (isEmergency) {
      statusLabel = "EMERGENCY STOP";
      statusClass = "bg-rose-950 text-rose-300 border-rose-700 animate-pulse";
    } else if (isSafeMode) {
      statusLabel = "SAFE MODE";
      statusClass = "bg-indigo-950 text-indigo-300 border-indigo-700";
    } else if (isReconnecting) {
      statusLabel = "RECONNECTING";
      statusClass = "bg-amber-950 text-amber-300 border-amber-700 animate-pulse";
    } else if (isDegraded) {
      statusLabel = "DEGRADED";
      statusClass = "bg-amber-950 text-amber-300 border-amber-800";
    } else if (isLive) {
      statusLabel = "LIVE";
      statusClass = "bg-red-950 text-red-400 border-red-800 animate-pulse";
    } else if (isActive) {
      statusLabel = "ATTACHED";
      statusClass = "bg-emerald-950 text-emerald-400 border-emerald-800";
    }

    return {
      id: def.id,
      name: sup?.title || active?.title || def.name,
      isActive,
      isLive,
      isEmergency,
      isSafeMode,
      statusLabel,
      statusClass,
      viewers: sup?.concurrent_viewers || active?.viewer_count || 0,
      messagesRead: sup?.messages_received || active?.messages_read || 0,
      messagesPosted: sup?.messages_sent || active?.messages_posted || 0,
      reconnects: sup?.reconnect_attempts || 0,
    };
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-red-400 animate-pulse" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
            4-Stream Live Overview
          </h2>
        </div>
        <span className="text-[11px] font-mono text-slate-400">
          Max Capacity: 4 Concurrent YouTube Streams
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {slots.map((slot) => {
          const isSelected = selectedStreamId.toUpperCase() === slot.id.toUpperCase();
          return (
            <div
              key={slot.id}
              onClick={() => onSelectStream(slot.id)}
              className={`p-4 rounded-2xl cursor-pointer border transition duration-200 flex flex-col justify-between space-y-3 ${
                isSelected
                  ? "bg-slate-900 border-blue-500 shadow-lg shadow-blue-950/50 ring-1 ring-blue-500/50"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90"
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="text-sm font-bold text-white truncate">{slot.name}</h3>
                  <span className="text-[10px] font-mono text-slate-400 uppercase">{slot.id}</span>
                </div>
                <span
                  className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${slot.statusClass}`}
                >
                  <span>{slot.statusLabel}</span>
                </span>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-2 p-2 rounded-xl bg-slate-950/60 border border-slate-800/80 text-center font-mono">
                <div>
                  <span className="text-[9px] text-slate-500 block">VIEWERS</span>
                  <span className="text-xs font-bold text-white">{slot.viewers}</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-500 block">IN</span>
                  <span className="text-xs font-bold text-cyan-400">{slot.messagesRead}</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-500 block">OUT</span>
                  <span className="text-xs font-bold text-purple-400">{slot.messagesPosted}</span>
                </div>
              </div>

              {/* Action Link */}
              <div className="flex items-center justify-between text-xs font-semibold pt-1 border-t border-slate-800/60">
                <span className="text-[11px] text-slate-400">
                  {isSelected ? "Currently Selected" : "Click to manage"}
                </span>
                <ArrowRight
                  className={`w-3.5 h-3.5 transition-transform ${
                    isSelected ? "text-blue-400 translate-x-1" : "text-slate-500"
                  }`}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
