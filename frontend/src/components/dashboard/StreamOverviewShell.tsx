"use client";

import React from "react";
import { Radio, Users, MessageSquare, AlertCircle } from "lucide-react";

export function StreamOverviewShell() {
  const streams = [
    { id: "A", name: "Stream Session A", status: "STANDBY", note: "Ready for channel assignment" },
    { id: "B", name: "Stream Session B", status: "STANDBY", note: "Ready for channel assignment" },
    { id: "C", name: "Stream Session C", status: "STANDBY", note: "Ready for channel assignment" },
    { id: "D", name: "Stream Session D", status: "STANDBY", note: "Ready for channel assignment" },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-200">Multi-Stream Overview (4 Slots)</h2>
          <p className="text-[11px] text-slate-400">
            Independent stream session architecture for up to 4 concurrent YouTube Live sessions
          </p>
        </div>
        <div className="flex items-center gap-1 text-[11px] font-medium text-blue-400 bg-blue-950/40 border border-blue-800/30 px-2 py-0.5 rounded">
          <AlertCircle className="w-3 h-3" />
          <span>Awaiting Phase 3 (YouTube Engine)</span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {streams.map((stream) => (
          <div
            key={stream.id}
            className="p-4 rounded-xl bg-slate-900/40 border border-dashed border-slate-800 flex flex-col justify-between space-y-3"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Radio className="w-3.5 h-3.5 text-slate-500" />
                  {stream.name}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/50">
                  {stream.status}
                </span>
              </div>
              <p className="text-[11px] text-slate-400">{stream.note}</p>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/40 text-[10px] font-mono text-slate-400">
              <div className="flex items-center gap-1">
                <Users className="w-3 h-3 text-slate-500" />
                <span>0 Viewers</span>
              </div>
              <div className="flex items-center gap-1">
                <MessageSquare className="w-3 h-3 text-slate-500" />
                <span>0 msg/min</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
