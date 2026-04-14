"use client";

import type { Agent } from "@/lib/api";
import { Home, CreditCard, ShieldAlert, SlidersHorizontal, HelpCircle, Fingerprint } from "lucide-react";
import TrustScoreBadge from "./TrustScoreBadge";

interface FirewallSidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  agent: Agent;
}

const NAV_ITEMS = [
  { id: "Overview", label: "Overview", icon: Home },
  { id: "Transactions", label: "Transactions", icon: CreditCard },
  { id: "Trust", label: "Trust Score", icon: Fingerprint },
  { id: "Risk", label: "Risk", icon: ShieldAlert },
  { id: "Settings", label: "Settings", icon: SlidersHorizontal },
];

export default function FirewallSidebar({ activeTab, onTabChange, agent }: FirewallSidebarProps) {
  return (
    <aside className="w-60 shrink-0 flex flex-col border-r border-border bg-surface pt-5">
      {/* Logo */}
      <div className="px-5 pb-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center text-white justify-center rounded-none bg-accent">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M13 10V3L4 14h7v7l9-11h-7z" fill="currentColor" strokeWidth={0} />
            </svg>
          </div>
          <div>
            <div className="text-sm font-semibold text-text-primary">Squid</div>
            <div className="text-xs text-text-muted">Dashboard</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto px-3 pt-5 space-y-0.5">
        <div className="text-xs font-medium text-text-muted px-3 mb-2">Navigation</div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`flex items-center gap-3 w-full rounded-none px-3 py-2 text-sm transition-all ${
                isActive
                  ? "bg-accent-light text-accent font-medium border-l-2 border-accent"
                  : "text-text-secondary hover:bg-surface-hover hover:text-text-primary"
              }`}
            >
              <Icon size={16} className={isActive ? "text-accent" : "opacity-60"} />
              {item.label}
            </button>
          );
        })}
      </div>

      {/* Agent status */}
      <div className="p-3 mt-auto">
        <div className="bg-background border border-border rounded-none p-3.5">
          <div className="flex items-center justify-between mb-3 border-b border-border pb-2">
            <span className="text-xs text-text-muted flex items-center gap-1.5">
              Agent status
              <HelpCircle size={12} className="opacity-40" />
            </span>
          </div>
          <div className="flex items-center justify-center">
            <TrustScoreBadge score={agent.trust_score} size="sm" />
          </div>
        </div>
      </div>
    </aside>
  );
}
