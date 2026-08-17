"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Sidebar } from "@/components/layout/Sidebar";
import { OperationsOverview } from "@/components/dashboard/OperationsOverview";
import { FourStreamOverview } from "@/components/dashboard/FourStreamOverview";
import { StreamControlCenter } from "@/components/dashboard/StreamControlCenter";
import { ModerationCenter } from "@/components/dashboard/ModerationCenter";
import { CoHostCenter } from "@/components/dashboard/CoHostCenter";
import { ModuleCenter } from "@/components/dashboard/ModuleCenter";
import { AIOperationsPanel } from "@/components/dashboard/AIOperationsPanel";
import { ProviderHealthPanel } from "@/components/dashboard/ProviderHealthPanel";
import { AuditLogPanel } from "@/components/dashboard/AuditLogPanel";
import { SafetyControls } from "@/components/dashboard/SafetyControls";
import { ActivityTimeline } from "@/components/dashboard/ActivityTimeline";
import { fetchDashboardOverview, fetchSystemHealth } from "@/lib/api";
import { ConnectionState, DashboardOverview, SystemHealthData } from "@/lib/types";
import { dashboardWs } from "@/lib/ws";
import { Shield, Bot, Layers, Cpu, Radio, Clock, AlertOctagon } from "lucide-react";

export default function CreatorControlCenterPage() {
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedStreamId, setSelectedStreamId] = useState("stream_alpha");
  const [healthData, setHealthData] = useState<SystemHealthData | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardOverview | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>("DISCONNECTED");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [health, overview] = await Promise.all([
        fetchSystemHealth().catch(() => null),
        fetchDashboardOverview().catch(() => null),
      ]);
      if (health) setHealthData(health);
      if (overview) setDashboardData(overview);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to fetch telemetry data");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);

    // Subscribe to WebSocket Connection State
    const unsubWs = dashboardWs.onStateChange((state) => {
      setConnectionState(state);
    });

    return () => {
      clearInterval(interval);
      unsubWs();
    };
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

      {/* Main Workspace */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
          {/* Header Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-cyan-400 font-semibold tracking-wider uppercase">
                  Milestone 14 &bull; Production Creator Control Center
                </span>
              </div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                Multi-Stream Creator Control Center
              </h1>
              <p className="text-xs sm:text-sm text-slate-400 max-w-3xl">
                Unified live command hub for Goddess AI 2.0. Real-time 4-stream monitoring,
                3-tier AI moderation, interactive AI co-host, operational audit trail, and instant safety controls.
              </p>
            </div>
          </div>

          {/* 1. Global Operations Overview */}
          <OperationsOverview />

          {/* 2. Safety Controls */}
          <SafetyControls />

          {/* 3. 4-Stream Live Overview */}
          <FourStreamOverview
            streams={dashboardData?.streams || []}
            selectedStreamId={selectedStreamId}
            onSelectStream={setSelectedStreamId}
          />

          {/* 4. Selected Stream Control Center */}
          <StreamControlCenter streamId={selectedStreamId} onRefresh={loadData} />

          {/* 5. Subsystem Centers Grid (Moderation & Co-Host) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ModerationCenter streamId={selectedStreamId} />
            <CoHostCenter streamId={selectedStreamId} />
          </div>

          {/* 6. Modular Extension Center */}
          <ModuleCenter />

          {/* 7. AI & Provider Operations Diagnostics Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AIOperationsPanel />
            <ProviderHealthPanel />
          </div>

          {/* 8. Operational Audit Log & Activity Timeline */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AuditLogPanel />
            <ActivityTimeline />
          </div>
        </main>
      </div>
    </div>
  );
}
