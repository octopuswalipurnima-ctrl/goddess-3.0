"use client";

import React from "react";
import { StreamSessionSummary } from "@/lib/types";
import { Radio, Users, MessageSquare, Shield, Bot, Layers, ArrowRight } from "lucide-react";

interface Props {
  streams: StreamSessionSummary[];
  selectedStreamId: string;
  onSelectStream: (streamId: string) => void;
}

const DEFAULT_STREAMS = [
  { id: "stream_alpha", name: "Stream Alpha (Primary)" },
  { id: "stream_beta", name: "Stream Beta (Secondary)" },
  { id: "stream_gamma", name: "Stream Gamma (Co-Stream)" },
  { id: "stream_delta", name: "Stream Delta (Multicast)" },
];

export function FourStreamOverview({ streams, selectedStreamId, onSelectStream }: Props) {
  // Map active streams or fallback to default slots
  const slots = DEFAULT_STREAMS.map((def) => {
    const active = streams.find((s) => s.stream_id === def.id);
    return {
      id: def.id,
      name: active?.title || def.name,
      isActive: !!active?.is_active,
      isLive: !!active?.is_live,
      viewers: active?.viewer_count || 0,
      messagesRead: active?.messages_read || 0,
      messagesPosted: active?.messages_posted || 0,
      errorCount: active?.error_count || 0,
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
          const isSelected = selectedStreamId === slot.id;
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
                  className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                    slot.isLive
                      ? "bg-red-950 text-red-400 border-red-800 animate-pulse"
                      : slot.isActive
                      ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                      : "bg-slate-800 text-slate-400 border-slate-700"
                  }`}
                >
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${
                      slot.isLive ? "bg-red-400" : slot.isActive ? "bg-emerald-400" : "bg-slate-500"
                    }`}
                  />
                  <span>{slot.isLive ? "LIVE" : slot.isActive ? "ATTACHED" : "OFFLINE"}</span>
                </span>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-2 p-2 rounded-xl bg-slate-950/60 border border-slate-800/80 text-center font-mono">
                <div>
                  <span className="text-[9px] text-slate-500 block">VIEWERS</span>
                  <span className="text-xs font-bold text-white">{slot.viewers}</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-500 block">MSGS READ</span>
                  <span className="text-xs font-bold text-cyan-400">{slot.messagesRead}</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-500 block">POSTED</span>
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
