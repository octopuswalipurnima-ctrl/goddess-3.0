"use client";

import React from "react";
import {
  LayoutDashboard,
  Radio,
  ShieldCheck,
  Bot,
  Terminal,
  Trophy,
  Boxes,
  Activity,
  Settings,
} from "lucide-react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, badge: null },
    { id: "streams", label: "Live Streams", icon: Radio, badge: "4 max" },
    { id: "moderation", label: "AI Moderation", icon: ShieldCheck, badge: null },
    { id: "cohost", label: "AI Co-Host", icon: Bot, badge: null },
    { id: "commands", label: "Commands", icon: Terminal, badge: null },
    { id: "viewers", label: "XP & VIP", icon: Trophy, badge: null },
    { id: "modules", label: "Module System", icon: Boxes, badge: null },
    { id: "diagnostics", label: "System Health", icon: Activity, badge: null },
    { id: "settings", label: "Settings", icon: Settings, badge: null },
  ];

  return (
    <aside className="w-64 border-r border-slate-800/80 bg-slate-950/40 p-4 flex flex-col justify-between shrink-0 hidden md:flex">
      <div className="space-y-1">
        <div className="px-3 py-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Management
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                isActive
                  ? "bg-blue-600/15 text-blue-300 border border-blue-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-blue-400" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Version and Local Status Footnote */}
      <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 text-[11px] space-y-1 text-slate-400">
        <div className="flex items-center justify-between">
          <span className="text-slate-300 font-medium">Local Runtime</span>
          <span className="text-emerald-400 font-mono">Ready</span>
        </div>
        <p className="text-slate-400">Milestone 0: Local Foundation</p>
      </div>
    </aside>
  );
}
