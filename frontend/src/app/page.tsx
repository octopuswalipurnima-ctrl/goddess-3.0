"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";
import { BotStatusCard } from "@/components/dashboard/BotStatusCard";
import { ComponentHealthGrid } from "@/components/dashboard/ComponentHealthGrid";
import { StreamOverviewShell } from "@/components/dashboard/StreamOverviewShell";
import { QuickControls } from "@/components/dashboard/QuickControls";
import { fetchActiveStreams, fetchSystemHealth } from "@/lib/api";
import { StreamSessionSummary, SystemHealthData } from "@/lib/types";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [healthData, setHealthData] = useState<SystemHealthData | null>(null);
  const [activeStreams, setActiveStreams] = useState<StreamSessionSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [health, streams] = await Promise.all([
        fetchSystemHealth(),
        fetchActiveStreams(),
      ]);
      setHealthData(health);
      setActiveStreams(streams);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to fetch telemetry data");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    // Auto-refresh telemetry every 5 seconds
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData]);

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
                Milestone 1 &bull; YouTube Engine Live
              </span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Creator Control Center
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl">
              Real-time multi-stream orchestration hub for Goddess AI 2.0. Managing up to 4 concurrent
              YouTube Live streams with quota-aware key rotation, isolated chat readers, and event bus dispatching.
            </p>
          </div>

          {/* Core Bot Status Overview */}
          <BotStatusCard health={healthData} isLoading={isLoading} error={error} />

          {/* Subsystem Health Grid (PostgreSQL, Redis, YouTube, Gemini) */}
          <ComponentHealthGrid components={healthData?.components} />

          {/* 4 Stream Capacity Grid */}
          <StreamOverviewShell sessions={activeStreams} onRefresh={loadData} />

          {/* Module Switchboard Controls */}
          <QuickControls onRefresh={loadData} isRefreshing={isLoading} />
        </main>
      </div>
    </div>
  );
}
