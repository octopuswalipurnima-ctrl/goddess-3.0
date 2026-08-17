"use client";

import React, { useEffect, useState } from "react";
import { ActivityEvent } from "@/lib/types";
import { dashboardWs } from "@/lib/ws";
import { Activity, Clock, Shield, Bot, Radio, Cpu, Layers } from "lucide-react";

export function ActivityTimeline() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    const unsub = dashboardWs.onActivity((newEvent) => {
      setEvents((prev) => [newEvent, ...prev.slice(0, 99)]); // Bounded to 100 events
    });
    return () => unsub();
  }, []);

  const getEventIcon = (type: string) => {
    if (type.includes("MODERATION")) return <Shield className="w-3.5 h-3.5 text-amber-400" />;
    if (type.includes("COHOST")) return <Bot className="w-3.5 h-3.5 text-purple-400" />;
    if (type.includes("STREAM") || type.includes("YOUTUBE")) return <Radio className="w-3.5 h-3.5 text-red-400" />;
    if (type.includes("AI") || type.includes("GEMINI")) return <Cpu className="w-3.5 h-3.5 text-cyan-400" />;
    if (type.includes("MODULE")) return <Layers className="w-3.5 h-3.5 text-blue-400" />;
    return <Activity className="w-3.5 h-3.5 text-slate-400" />;
  };

  const getBadgeStyle = (level: string) => {
    switch (level) {
      case "error":
        return "bg-rose-950 text-rose-300 border-rose-800";
      case "warning":
        return "bg-amber-950 text-amber-300 border-amber-800";
      case "success":
        return "bg-emerald-950 text-emerald-300 border-emerald-800";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wide">
            Real-Time Activity Timeline
          </h2>
        </div>
        <span className="text-[10px] font-mono text-slate-500">
          Showing latest {events.length}/100 events
        </span>
      </div>

      <div className="max-h-64 overflow-y-auto rounded-xl bg-slate-950/80 border border-slate-800/80 divide-y divide-slate-800/50 text-xs">
        {events.length === 0 ? (
          <div className="p-4 text-center text-slate-500 font-mono text-[11px]">
            Waiting for live stream activity events...
          </div>
        ) : (
          events.map((evt) => (
            <div key={evt.id} className="p-2.5 flex items-center justify-between gap-3 hover:bg-slate-900/40 transition">
              <div className="flex items-center gap-2.5 min-w-0">
                {getEventIcon(evt.event_type)}
                <div className="space-y-0.5 truncate">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-200 text-[11px] truncate">
                      {evt.event_type}
                    </span>
                    {evt.stream_id && (
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-blue-300">
                        {evt.stream_id}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 truncate">{evt.summary}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${getBadgeStyle(evt.level)}`}>
                  {evt.level.toUpperCase()}
                </span>
                <span className="text-[10px] font-mono text-slate-500">
                  {new Date(evt.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
