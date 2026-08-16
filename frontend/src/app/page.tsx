"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";
import { BotStatusCard } from "@/components/dashboard/BotStatusCard";
import { ComponentHealthGrid } from "@/components/dashboard/ComponentHealthGrid";
import { StreamOverviewShell } from "@/components/dashboard/StreamOverviewShell";
import { QuickControls } from "@/components/dashboard/QuickControls";
import { fetchSystemHealth } from "@/lib/api";
import { SystemHealthData } from "@/lib/types";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [healthData, setHealthData] = useState<SystemHealthData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await fetchSystemHealth();
      setHealthData(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to fetch health");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
    // Auto-refresh health every 5 seconds
    const interval = setInterval(loadHealth, 5000);
    return () => clearInterval(interval);
  }, [loadHealth]);

  const isConnected = !!healthData && !error;

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-slate-100 selection:bg-blue-600 selection:text-white">
      {/* Top Navigation Bar */}
      <Navbar
        isBackendConnected={isConnected}
        version={healthData?.version || "2.0.0"}
        uptimeSeconds={healthData?.uptime_seconds || 0}
      />

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
          {/* Header Banner */}
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono text-cyan-400 font-semibold tracking-wider uppercase">
                Milestone 0 &bull; Local Foundation
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Creator Control Center
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl">
              Real-time monitoring and orchestration hub for Goddess AI 2.0. Built local-first with FastAPI,
              Next.js, multi-stream architecture, and quota-aware API rotation.
            </p>
          </div>

          {/* Core Bot Status Overview */}
          <BotStatusCard health={healthData} isLoading={isLoading} error={error} />

          {/* Subsystem Health Grid (PostgreSQL, Redis, YouTube, Gemini) */}
          <ComponentHealthGrid components={healthData?.components} />

          {/* 4 Stream Capacity Grid */}
          <StreamOverviewShell />

          {/* Module Switchboard Controls */}
          <QuickControls onRefresh={loadHealth} isRefreshing={isLoading} />
        </main>
      </div>
    </div>
  );
}
