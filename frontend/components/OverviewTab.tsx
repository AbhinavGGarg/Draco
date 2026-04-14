"use client";

import type { User, Agent, Transaction, RiskMetrics } from "@/lib/api";
import { ArrowRight, SearchX } from "lucide-react";
import SpendingChart from "./SpendingChart";
import TrustScoreBadge from "./TrustScoreBadge";

const statusStyles: Record<string, string> = {
  pending: "bg-warning-light text-warning",
  completed: "bg-success-light text-success",
  failed: "bg-danger-light text-danger",
  returned: "bg-surface text-text-secondary",
  disputed: "bg-orange-light text-orange",
  flagged: "bg-purple-light text-purple",
};

const riskStatusStyles: Record<string, { bg: string; text: string }> = {
  normal:     { bg: "bg-success-light", text: "text-success" },
  elevated:   { bg: "bg-warning-light", text: "text-warning" },
  restricted: { bg: "bg-orange-light",  text: "text-orange" },
  frozen:     { bg: "bg-danger-light",  text: "text-danger" },
};

interface OverviewTabProps {
  user: User;
  agent: Agent;
  transactions: Transaction[];
  risk: RiskMetrics | null;
}

export default function OverviewTab({ user, agent, transactions, risk }: OverviewTabProps) {
  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

  const completedTxs = transactions.filter((t) => t.status === "completed");
  const spentThisWeek = completedTxs
    .filter((t) => new Date(t.created_at) >= weekAgo)
    .reduce((sum, t) => sum + t.amount, 0);
  const spentThisMonth = completedTxs
    .filter((t) => new Date(t.created_at) >= monthAgo)
    .reduce((sum, t) => sum + t.amount, 0);

  const recentTxs = [...transactions]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  const riskStatus = risk?.status || "normal";
  const riskStyle = riskStatusStyles[riskStatus];

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between mb-8 pb-4 border-b border-border">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Overview</h1>
          <p className="text-sm text-text-muted mt-1">Your agent activity at a glance</p>
        </div>
      </div>

      {/* Spending Chart */}
      <SpendingChart transactions={transactions} />

      {/* Metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-surface border border-border rounded-none p-5 flex flex-col justify-between">
          <div className="text-sm text-text-secondary mb-3">Available balance</div>
          <div className="text-3xl font-semibold tabular-nums text-text-primary">${user.balance.toFixed(2)}</div>
          <div className="text-xs text-text-muted mt-3 pt-2 border-t border-border">Spending limit</div>
        </div>

        <div className="bg-surface border border-border rounded-none p-5 flex flex-col justify-between">
          <div className="text-sm text-text-secondary mb-3">Total spent</div>
          <div className="text-3xl font-semibold tabular-nums text-text-primary mt-auto">${spentThisMonth.toFixed(2)}</div>
          <div className="text-xs text-accent mt-3 pt-2 border-t border-border flex gap-1 items-center">
            <ArrowRight size={10} className="-rotate-45" /> {spentThisMonth > 0 ? "30-day total" : "No activity"}
          </div>
        </div>

        <div className="bg-surface border border-border rounded-none p-5 flex flex-col justify-between">
          <div className="text-sm text-text-secondary mb-3">This week</div>
          <div className="text-3xl font-semibold tabular-nums text-text-primary mt-auto">${spentThisWeek.toFixed(2)}</div>
          <div className="text-xs text-text-muted mt-3 pt-2 border-t border-border">7-day rolling</div>
        </div>

        <div className="bg-surface border border-border rounded-none p-5 flex flex-col justify-between">
          <div className="text-sm text-text-secondary mb-3">Trust score</div>
          <div className="mt-auto">
            <TrustScoreBadge score={agent.trust_score} size="md" />
          </div>
          <div className="text-xs text-text-muted mt-3 pt-2 border-t border-border">
            {risk && (
              <span className={`inline-flex items-center gap-1.5 rounded-none-full px-2 py-0.5 text-xs font-medium ${riskStyle.bg} ${riskStyle.text}`}>
                <span className={`h-1.5 w-1.5 rounded-none-full ${riskStyle.text.replace("text-", "bg-")}`} />
                {riskStatus.charAt(0).toUpperCase() + riskStatus.slice(1)}
              </span>
            )}
            {!risk && "Behavior metric"}
          </div>
        </div>
      </div>

      {/* Recent activity table */}
      <div className="bg-surface border border-border rounded-none overflow-hidden">
        <div className="p-5 border-b border-border flex justify-between items-center">
          <div>
            <h2 className="text-sm font-semibold text-text-primary">Recent activity</h2>
            <p className="text-xs text-text-muted mt-1">Latest transactions</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-background">
                <th className="px-5 py-3 text-xs font-medium text-text-secondary w-[140px]">Amount</th>
                <th className="px-5 py-3 text-xs font-medium text-text-secondary">Merchant</th>
                <th className="px-5 py-3 text-xs font-medium text-text-secondary w-[180px]">Date</th>
                <th className="px-5 py-3 text-xs font-medium text-text-secondary text-right w-[140px]">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {recentTxs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-12">
                    <div className="flex flex-col items-center justify-center text-text-muted">
                      <SearchX size={32} className="opacity-20 mb-4" />
                      <span className="text-sm">No transactions yet</span>
                    </div>
                  </td>
                </tr>
              ) : (
                recentTxs.map((tx) => (
                  <tr key={tx.id} className="hover:bg-surface-hover transition-colors">
                    <td className="px-5 py-4 text-sm font-medium tabular-nums text-text-primary w-[140px]">
                      ${tx.amount.toFixed(2)}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-none border border-border bg-background flex items-center justify-center text-xs font-medium text-text-secondary">
                          {tx.merchant.slice(0, 2)}
                        </div>
                        <div>
                          <div className="text-sm font-medium text-text-primary">{tx.merchant}</div>
                          <div className="text-xs text-text-muted truncate max-w-[200px]">
                            {tx.product_description || tx.category}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-xs text-text-secondary w-[180px]">
                      {new Date(tx.created_at).toISOString().replace("T", " ").substring(0, 16)}
                    </td>
                    <td className="px-5 py-4 text-right w-[140px]">
                      <span className={`inline-flex px-2.5 py-1 rounded-none-full text-xs font-medium ${statusStyles[tx.status] || "bg-surface text-text-secondary"}`}>
                        {tx.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
