"use client";

import { useState } from "react";
import type { Transaction } from "@/lib/api";
import { markTransaction, disputeTransaction } from "@/lib/api";
import { SearchX, ArrowDownUp } from "lucide-react";
import { toast } from "sonner";

const statusStyles: Record<string, string> = {
  pending: "bg-warning-light text-warning",
  completed: "bg-success-light text-success",
  failed: "bg-danger-light text-danger",
  returned: "bg-surface text-text-secondary",
  disputed: "bg-orange-light text-orange",
  flagged: "bg-purple-light text-purple",
};

interface TransactionsTabProps {
  transactions: Transaction[];
  onRefresh: () => void;
}

export default function TransactionsTab({ transactions, onRefresh }: TransactionsTabProps) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "completed" | "failed">("all");

  const sorted = [...transactions].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  const filtered = filter === "all" ? sorted : sorted.filter((t) => t.status === filter);

  const handleMark = async (txId: string) => {
    setActionLoading(txId);
    try {
      const res = await markTransaction(txId, "good");
      toast.success(`Marked good. Score: ${res.trust_score} (${res.new_tier})`);
      onRefresh();
    } catch (err) {
      toast.error(String(err));
    } finally {
      setActionLoading(null);
    }
  };

  const handleDispute = async (txId: string, type: "unauthorized" | "wrong_item" | "fulfillment_issue") => {
    setActionLoading(txId);
    try {
      const res = await disputeTransaction(txId, type);
      const creditMsg = res.balance_credited ? ` $${res.balance_credited} credited.` : "";
      if (res.eligible) {
        toast.success(`Disputed (${type}). Score: ${res.trust_score} (${res.new_tier}).${creditMsg}`);
      } else {
        toast.error(`Disputed (${type}). Score: ${res.trust_score} (${res.new_tier}).${creditMsg}`);
      }
      onRefresh();
    } catch (err) {
      toast.error(String(err));
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Transaction History</h1>
          <p className="text-sm text-text-muted mt-1">All transaction activity</p>
        </div>
      </div>

      <div className="bg-surface border border-border overflow-hidden rounded-none">
        <div className="p-4 border-b border-border flex justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="inline-flex rounded-none border border-border bg-background p-1">
              {(["all", "completed", "failed"] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-none-md capitalize transition-colors ${
                    filter === f
                      ? "bg-accent text-white"
                      : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
            <span className="text-xs text-text-muted pl-3 border-l border-border">
              {filtered.length} records
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-background">
                <th className="px-5 py-3 text-xs font-medium text-text-secondary">
                  <div className="flex items-center gap-1">Date <ArrowDownUp size={10} /></div>
                </th>
                <th className="px-5 py-3 text-xs font-medium text-text-secondary">Merchant</th>
                <th className="px-5 py-3 text-xs font-medium text-text-secondary">Product</th>
                <th className="px-5 py-3 text-xs font-medium text-text-secondary">Category</th>
                <th className="px-5 py-3 text-xs font-medium text-text-secondary text-right">Amount</th>
                <th className="px-5 py-3 text-xs font-medium text-text-secondary w-[100px]">Status</th>
                <th className="px-5 py-3 text-xs font-medium text-text-secondary text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12">
                    <div className="flex flex-col items-center justify-center text-text-muted">
                      <SearchX size={32} className="opacity-20 mb-4" />
                      <span className="text-sm mb-1">No records found</span>
                      <span className="text-xs text-text-muted">
                        {filter === "completed" ? "No completed transactions"
                          : filter === "failed" ? "No failed transactions"
                          : "No transactions yet"}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.map((tx) => (
                  <tr key={tx.id} className="hover:bg-surface-hover transition-colors">
                    <td className="whitespace-nowrap px-5 py-4 text-xs text-text-secondary">
                      {new Date(tx.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-none border border-border bg-background flex items-center justify-center text-xs font-medium text-text-secondary shrink-0">
                          {tx.merchant.slice(0, 2)}
                        </div>
                        <span className="text-sm font-medium text-text-primary">{tx.merchant}</span>
                      </div>
                    </td>
                    <td className="max-w-[200px] truncate px-5 py-4 text-sm text-text-secondary">
                      {tx.product_description || "-"}
                    </td>
                    <td className="px-5 py-4">
                      <span className="inline-flex px-2 py-0.5 rounded-none-full text-xs font-medium bg-background border border-border text-text-secondary capitalize">
                        {tx.category}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-5 py-4 text-right text-sm font-medium tabular-nums text-text-primary">
                      ${tx.amount.toFixed(2)}
                    </td>
                    <td className="px-5 py-4 w-[100px]">
                      <span className={`inline-flex px-2.5 py-1 rounded-none-full text-xs font-medium capitalize ${statusStyles[tx.status] || "bg-surface text-text-secondary"}`}>
                        {tx.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      {tx.status === "completed" && (
                        <div className="flex items-center justify-end gap-1.5">
                          <button onClick={() => handleMark(tx.id)} disabled={actionLoading === tx.id}
                            className="text-xs font-medium px-2.5 py-1 rounded-none border border-success/30 text-success hover:bg-success-light transition-colors disabled:opacity-50">
                            Good
                          </button>
                          <button onClick={() => handleDispute(tx.id, "unauthorized")} disabled={actionLoading === tx.id}
                            className="text-xs font-medium px-2.5 py-1 rounded-none border border-danger/30 text-danger hover:bg-danger-light transition-colors disabled:opacity-50">
                            Unauth
                          </button>
                          <button onClick={() => handleDispute(tx.id, "wrong_item")} disabled={actionLoading === tx.id}
                            className="text-xs font-medium px-2.5 py-1 rounded-none border border-orange/30 text-orange hover:bg-orange-light transition-colors disabled:opacity-50">
                            Wrong
                          </button>
                          <button onClick={() => handleDispute(tx.id, "fulfillment_issue")} disabled={actionLoading === tx.id}
                            className="text-xs font-medium px-2.5 py-1 rounded-none border border-border text-text-secondary hover:bg-surface-hover transition-colors disabled:opacity-50">
                            Fulfill
                          </button>
                        </div>
                      )}
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
