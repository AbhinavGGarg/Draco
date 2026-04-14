"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, ShieldCheck, ShieldX, ChevronRight } from "lucide-react";
import type { RiskMetrics, Transaction, EvidenceBundle } from "@/lib/api";

const disputeTypeLabels: Record<string, { label: string; color: string }> = {
  unauthorized:      { label: "Unauthorized", color: "text-danger bg-danger-light" },
  wrong_item:        { label: "Wrong Item", color: "text-orange bg-orange-light" },
  fulfillment_issue: { label: "Fulfillment", color: "text-warning bg-warning-light" },
};

function RateRow({ label, rate, threshold }: { label: string; rate: number; threshold: number }) {
  const pct = rate * 100;
  const pctStr = pct.toFixed(2);
  const barWidth = Math.min((pct / (threshold * 2)) * 100, 100);
  const thresholdPos = 50; // threshold is at 50% of the bar visually

  return (
    <div className="flex items-center gap-6">
      <span className="text-sm text-text-secondary w-36 shrink-0">{label}</span>
      <div className="flex-1 relative">
        <div className="w-full h-1.5 bg-background border border-border relative">
          {/* Threshold marker */}
          <div
            className="absolute top-[-4px] bottom-[-4px] w-px bg-text-muted"
            style={{ left: `${thresholdPos}%` }}
          />
          {/* Current rate fill */}
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${barWidth}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="h-full bg-text-primary"
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-text-muted">0%</span>
          <span className="text-[10px] text-text-muted" style={{ position: "absolute", left: `${thresholdPos}%`, transform: "translateX(-50%)", marginTop: "2px" }}>{threshold}%</span>
        </div>
      </div>
      <span className={`text-sm font-medium tabular-nums w-16 text-right ${pct > threshold ? "text-danger" : "text-text-primary"}`}>{pctStr}%</span>
    </div>
  );
}

function EvidenceViewer({ evidence, solanaSig }: { evidence: EvidenceBundle; solanaSig?: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-3">
      <button onClick={() => setExpanded(!expanded)} className="text-xs font-medium text-accent hover:text-accent-hover transition-colors flex items-center gap-1">
        <ChevronRight size={12} className={`transition-transform ${expanded ? "rotate-90" : ""}`} />
        {expanded ? "Hide evidence" : "View evidence"}
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden mt-3 space-y-4">

            {evidence.authorization && (
              <div className="border border-border bg-background p-4">
                <h4 className="text-xs font-semibold text-text-primary mb-3">Authorization</h4>
                <div>
                  <span className="text-text-muted text-xs">Original Message</span>
                  <p className="text-text-primary text-sm mt-0.5">&ldquo;{evidence.authorization.original_message}&rdquo;</p>
                </div>
                {evidence.authorization.authorized_at && (
                  <div className="mt-2">
                    <span className="text-text-muted text-xs">Authorized</span>
                    <p className="text-text-secondary text-xs font-mono mt-0.5">{new Date(evidence.authorization.authorized_at).toLocaleString()}</p>
                  </div>
                )}
              </div>
            )}

            {evidence.intent_snapshot && (
              <div className="border border-border bg-background p-4">
                <h4 className="text-xs font-semibold text-text-primary mb-3">Intent Snapshot</h4>
                <div className="grid grid-cols-2 gap-y-2 gap-x-6 text-sm">
                  <div>
                    <span className="text-text-muted text-xs">Product</span>
                    <p className="text-text-primary">{evidence.intent_snapshot.product_description}</p>
                  </div>
                  <div>
                    <span className="text-text-muted text-xs">Merchant</span>
                    <p className="text-text-primary">{evidence.intent_snapshot.merchant}</p>
                  </div>
                  <div>
                    <span className="text-text-muted text-xs">Amount</span>
                    <p className="text-text-primary tabular-nums">${evidence.intent_snapshot.amount.toFixed(2)}</p>
                  </div>
                  <div>
                    <span className="text-text-muted text-xs">Category</span>
                    <p className="text-text-primary capitalize">{evidence.intent_snapshot.category}</p>
                  </div>
                </div>
              </div>
            )}

            {evidence.policy_checks && (
              <div className="border border-border bg-background p-4">
                <h4 className="text-xs font-semibold text-text-primary mb-3">Policy Checks</h4>
                <div className="space-y-2">
                  {evidence.policy_checks.map((check, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        {check.result === "pass" ? (
                          <ShieldCheck size={14} className="text-success" />
                        ) : (
                          <ShieldX size={14} className="text-danger" />
                        )}
                        <span className="text-text-secondary">{check.check.replace(/_/g, " ")}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {check.detail && <span className="text-xs text-text-muted">{check.detail}</span>}
                        <span className={`text-xs font-medium px-2 py-0.5 ${check.result === "pass" ? "bg-success-light text-success" : "bg-danger-light text-danger"}`}>
                          {check.result}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {evidence.account_state_at_purchase && (
              <div className="border border-border bg-background p-4">
                <h4 className="text-xs font-semibold text-text-primary mb-3">Account State at Purchase</h4>
                <div className="grid grid-cols-4 gap-4">
                  <div>
                    <span className="text-text-muted text-xs">Balance</span>
                    <p className="text-text-primary text-sm tabular-nums font-medium">${evidence.account_state_at_purchase.balance.toFixed(2)}</p>
                  </div>
                  <div>
                    <span className="text-text-muted text-xs">Trust Score</span>
                    <p className="text-text-primary text-sm tabular-nums font-medium">{evidence.account_state_at_purchase.trust_score}</p>
                  </div>
                  <div>
                    <span className="text-text-muted text-xs">Tier</span>
                    <p className="text-text-primary text-sm font-medium capitalize">{evidence.account_state_at_purchase.tier}</p>
                  </div>
                  <div>
                    <span className="text-text-muted text-xs">Risk Status</span>
                    <p className="text-text-primary text-sm font-medium capitalize">{evidence.account_state_at_purchase.risk_status}</p>
                  </div>
                </div>
              </div>
            )}

            {evidence.execution_result && (
              <div className="border border-border bg-background p-4">
                <h4 className="text-xs font-semibold text-text-primary mb-3">Execution Result</h4>
                <div className="grid grid-cols-2 gap-y-2 gap-x-6 text-sm">
                  <div>
                    <span className="text-text-muted text-xs">Final Amount</span>
                    <p className="text-text-primary tabular-nums">${evidence.execution_result.final_amount.toFixed(2)}</p>
                  </div>
                  <div>
                    <span className="text-text-muted text-xs">Final Merchant</span>
                    <p className="text-text-primary">{evidence.execution_result.final_merchant}</p>
                  </div>
                  <div>
                    <span className="text-text-muted text-xs">Amount Match</span>
                    <span className={`text-xs font-medium px-2 py-0.5 ${evidence.execution_result.amount_match ? "bg-success-light text-success" : "bg-danger-light text-danger"}`}>
                      {evidence.execution_result.amount_match ? "Match" : "Mismatch"}
                    </span>
                  </div>
                  <div>
                    <span className="text-text-muted text-xs">Merchant Match</span>
                    <span className={`text-xs font-medium px-2 py-0.5 ${evidence.execution_result.merchant_match ? "bg-success-light text-success" : "bg-danger-light text-danger"}`}>
                      {evidence.execution_result.merchant_match ? "Match" : "Mismatch"}
                    </span>
                  </div>
                </div>
                {evidence.execution_result.rye_order_id && (
                  <div className="mt-3 pt-3 border-t border-border">
                    <span className="text-text-muted text-xs">Order ID</span>
                    <p className="text-text-secondary text-xs font-mono mt-0.5">{evidence.execution_result.rye_order_id}</p>
                  </div>
                )}
              </div>
            )}

            {evidence.timestamps && (
              <div className="border border-border bg-background p-4">
                <h4 className="text-xs font-semibold text-text-primary mb-3">Audit Timeline</h4>
                <div className="space-y-2">
                  {Object.entries(evidence.timestamps as Record<string, string>).map(([key, val]) => (
                    <div key={key} className="flex items-center justify-between text-sm">
                      <span className="text-text-secondary">{key.replace(/_/g, " ").replace(" at", "")}</span>
                      <span className="text-xs text-text-muted font-mono">{new Date(val).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {solanaSig && (
              <div className="border border-border bg-background p-4">
                <h4 className="text-xs font-semibold text-text-primary mb-3">On-Chain Proof</h4>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-text-muted text-xs">Solana Signature</span>
                    <p className="text-text-secondary text-xs font-mono mt-0.5 truncate max-w-[300px]">{solanaSig}</p>
                  </div>
                  <a
                    href={`https://explorer.solana.com/tx/${solanaSig}?cluster=devnet`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs font-medium text-accent hover:text-accent-hover transition-colors"
                  >
                    View on Explorer <ExternalLink size={10} />
                  </a>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const container = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.1 } } };
const item: any = { hidden: { opacity: 0, y: 15, filter: "blur(4px)" }, show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { type: "spring", stiffness: 300, damping: 24 } } };

interface RiskTabProps {
  risk: RiskMetrics | null;
  transactions: Transaction[];
}

export default function RiskTab({ risk, transactions }: RiskTabProps) {
  const disputedTxs = transactions.filter((t) => t.status === "disputed" || t.dispute_type).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  const flaggedTxs = transactions.filter((t) => t.status === "flagged").sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  if (!risk) {
    return <div className="bg-surface border border-border px-6 py-12 text-center text-sm text-text-muted">Risk data unavailable. Please check your connection.</div>;
  }

  const totalIssues = (risk.total_disputes_30d || 0) + (risk.total_flagged_30d || 0);
  const riskRate = risk.total_completed_30d > 0
    ? (totalIssues / risk.total_completed_30d * 100).toFixed(1)
    : "0.0";

  return (
    <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Risk Monitor</h1>
          <p className="text-sm text-text-muted mt-1">30-day rolling transaction health</p>
        </div>
      </div>

      {/* Top row: risk rate + rate breakdown */}
      <motion.div variants={item} className="grid grid-cols-3 gap-6">
        <div className="bg-surface border border-border p-8 col-span-1 flex flex-col items-center justify-center text-center">
          <p className="text-xs text-text-muted mb-3">Incident Rate</p>
          <p className="text-5xl font-semibold tracking-tight tabular-nums text-text-primary">{riskRate}%</p>
          <p className="text-xs text-text-muted mt-3">{totalIssues} of {risk.total_completed_30d} transactions · 30d</p>
        </div>
        <div className="bg-surface border border-border p-6 col-span-2">
          <p className="text-xs text-text-muted mb-4">Rate Breakdown</p>
          <div className="space-y-4">
            <RateRow label="Disputes" rate={risk.dispute_rate} threshold={5} />
            <RateRow label="Flagged" rate={risk.flagged_rate} threshold={5} />
            <RateRow label="Unauthorized" rate={risk.unauthorized_rate} threshold={5} />
            <RateRow label="Wrong Item" rate={risk.wrong_item_rate} threshold={5} />
          </div>
        </div>
      </motion.div>

      {/* Disputes */}
      <motion.div variants={item} className="bg-surface border border-border overflow-hidden">
        <div className="border-b border-border px-6 py-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text-primary">Disputes</h3>
          <span className="text-xs text-text-muted">{disputedTxs.length} total</span>
        </div>
        {disputedTxs.length === 0 ? (
          <div className="px-6 py-8 text-center text-sm text-text-muted">No disputes found</div>
        ) : (
          <div className="divide-y divide-border">
            {disputedTxs.map((tx) => {
              const dtConfig = tx.dispute_type ? disputeTypeLabels[tx.dispute_type] : null;
              return (
                <div key={tx.id} className="px-6 py-5 transition-colors hover:bg-surface-hover">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-text-primary">{tx.merchant}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {dtConfig && (
                          <span className={`text-xs font-medium px-2 py-0.5 ${dtConfig.color}`}>{dtConfig.label}</span>
                        )}
                        <span className="text-xs text-text-muted">{tx.dispute_at ? new Date(tx.dispute_at).toLocaleDateString() : "Unknown"}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium tabular-nums text-text-primary mb-1">${tx.amount.toFixed(2)}</p>
                      <span className="px-2.5 py-1 text-xs font-medium text-orange bg-orange-light">Disputed</span>
                    </div>
                  </div>
                  {tx.evidence && <EvidenceViewer evidence={tx.evidence} solanaSig={tx.solana_tx_signature ?? undefined} />}
                </div>
              );
            })}
          </div>
        )}
      </motion.div>

      {/* Flagged */}
      {flaggedTxs.length > 0 && (
        <motion.div variants={item} className="bg-surface border border-border overflow-hidden">
          <div className="border-b border-border px-6 py-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text-primary">Flagged Transactions</h3>
            <span className="text-xs text-text-muted">{flaggedTxs.length} total</span>
          </div>
          <div className="divide-y divide-border">
            {flaggedTxs.map((tx) => (
              <div key={tx.id} className="px-6 py-5 transition-colors hover:bg-surface-hover">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-text-primary">{tx.merchant}</p>
                    <p className="text-xs text-text-muted mt-1">{tx.product_description}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium tabular-nums text-text-primary mb-1">${tx.amount.toFixed(2)}</p>
                    <span className="px-2.5 py-1 text-xs font-medium text-purple bg-purple-light">Flagged</span>
                  </div>
                </div>
                {tx.evidence && <EvidenceViewer evidence={tx.evidence} solanaSig={tx.solana_tx_signature ?? undefined} />}
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </motion.div>
  );
}
