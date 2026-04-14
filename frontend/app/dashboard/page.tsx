"use client";

import { useState, useEffect, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import type { User, Agent, Transaction, RiskMetrics } from "@/lib/api";
import { getMe, getAgent, getTransactions, getRiskMetrics } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { Server } from "lucide-react";

import FirewallSidebar from "@/components/FirewallSidebar";
import OverviewTab from "@/components/OverviewTab";
import TransactionsTab from "@/components/TransactionsTab";
import RiskTab from "@/components/RiskTab";
import SettingsTab from "@/components/SettingsTab";
import TrustTab from "@/components/TrustTab";

const TABS = ["Overview", "Transactions", "Trust", "Risk", "Settings"] as const;
type Tab = (typeof TABS)[number];

export default function DashboardPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("Overview");
  const [user, setUser] = useState<User | null>(null);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [risk, setRisk] = useState<RiskMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const me = await getMe();
      const [a, txs] = await Promise.all([
        getAgent(me.id),
        getTransactions(me.id),
      ]);
      setUser(me);
      setAgent(a);
      setTransactions(txs);

      try {
        const r = await getRiskMetrics(me.id);
        setRisk(r);
      } catch {
        setRisk(null);
      }

      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  async function handleSignOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/");
    router.refresh();
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center">
          <div className="h-10 w-10 rounded-none bg-accent-light flex items-center justify-center animate-pulse mb-4">
            <Server className="text-accent" size={20} />
          </div>
          <div className="text-sm text-text-secondary animate-pulse">
            Loading Squid...
          </div>
        </div>
      </div>
    );
  }

  if (error || !user || !agent) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="rounded-none border border-border bg-surface p-8 text-center">
          <p className="text-sm font-medium text-danger">
            {error || "Failed to load dashboard data"}
          </p>
          <p className="mt-2 text-xs text-text-muted">
            Make sure the Flask API is running on{" "}
            {process.env.NEXT_PUBLIC_FLASK_API_URL || "http://localhost:5001"}
          </p>
          <button
            onClick={() => {
              setLoading(true);
              fetchData();
            }}
            className="mt-4 rounded-none bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <FirewallSidebar
        activeTab={tab}
        onTabChange={(t) => setTab(t as Tab)}
        agent={agent}
      />

      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Top bar */}
        <div className="h-14 border-b border-border bg-surface flex items-center justify-between px-6 z-10 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-muted">Squid</span>
            <span className="text-text-muted">/</span>
            <span className="text-sm font-medium text-text-primary">{tab}</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-text-secondary">{user.name}</span>
            <div className="w-7 h-7 rounded-none-full flex items-center justify-center text-xs font-medium text-white bg-accent">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <button
              onClick={handleSignOut}
              className="text-xs font-medium text-text-muted hover:text-text-secondary transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>

        {/* Page content */}
        <div className="overflow-y-auto flex-1 p-8 z-10 relative">
          <AnimatePresence mode="wait">
            <motion.div
              key={tab}
              initial={{ opacity: 0, scale: 0.98, filter: "blur(5px)" }}
              animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
              exit={{ opacity: 0, scale: 1.02, filter: "blur(5px)" }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="max-w-[1200px] mx-auto w-full"
            >
              {tab === "Overview" && (
                <OverviewTab
                  user={user}
                  agent={agent}
                  transactions={transactions}
                  risk={risk}
                />
              )}
              {tab === "Transactions" && (
                <TransactionsTab
                  transactions={transactions}
                  onRefresh={fetchData}
                />
              )}
              {tab === "Trust" && (
                <TrustTab user={user} agent={agent} />
              )}
              {tab === "Risk" && (
                <RiskTab risk={risk} transactions={transactions} />
              )}
              {tab === "Settings" && (
                <SettingsTab
                  user={user}
                  agent={agent}
                  transactions={transactions}
                  onRefresh={fetchData}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
