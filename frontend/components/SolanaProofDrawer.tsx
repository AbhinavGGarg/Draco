"use client";

import { useState, useEffect, useCallback } from "react";
import type { Transaction, EvidenceBundle, AgentStep } from "@/lib/api";
import { getAgentSteps } from "@/lib/api";

// --- Solana RPC helpers (direct devnet fetch, no backend route needed) ---

interface SolanaTxInfo {
  block: number | null;
  timestamp: number | null;
  fee: number;
  memo: string | null;
}

async function fetchSolanaTxInfo(signature: string): Promise<SolanaTxInfo | null> {
  const rpcUrl = "https://api.devnet.solana.com";
  try {
    const res = await fetch(rpcUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "getTransaction",
        params: [signature, { encoding: "jsonParsed", maxSupportedTransactionVersion: 0 }],
      }),
    });
    const json = await res.json();
    if (!json.result) return null;

    const result = json.result;
    const logMessages: string[] = result.meta?.logMessages || [];
    let memo: string | null = null;
    for (const log of logMessages) {
      if (log.startsWith("Program log: Memo")) {
        const match = log.match(/"(.+)"/);
        if (match) memo = match[1];
      }
    }
    // Also try inner instructions memo data
    if (!memo && result.meta?.logMessages) {
      for (const log of logMessages) {
        if (log.includes("Memo") && log.includes("{")) {
          const jsonStart = log.indexOf("{");
          if (jsonStart !== -1) memo = log.slice(jsonStart);
        }
      }
    }

    return {
      block: result.slot ?? null,
      timestamp: result.blockTime ?? null,
      fee: (result.meta?.fee ?? 0) / 1_000_000_000, // lamports to SOL
      memo,
    };
  } catch {
    return null;
  }
}

// --- Step type display helpers ---

const stepTypeConfig: Record<string, { color: string; dotColor: string; label: string }> = {
  search:   { color: "text-accent",  dotColor: "bg-accent",  label: "Search" },
  compare:  { color: "text-warning", dotColor: "bg-warning", label: "Compare" },
  select:   { color: "text-purple",  dotColor: "bg-purple",  label: "Select" },
  purchase: { color: "text-success", dotColor: "bg-success", label: "Purchase" },
};

function getStepConfig(stepType: string) {
  return stepTypeConfig[stepType] || { color: "text-text-secondary", dotColor: "bg-text-muted", label: stepType };
}

function describeStep(step: AgentStep): string {
  const d = step.data || {};
  switch (step.step_type) {
    case "search":
      return d.query
        ? `Searched for "${d.query as string}"${d.results_count ? ` and found ${d.results_count as number} results` : ""}`
        : "Performed a product search";
    case "compare":
      return d.products
        ? `Compared ${(d.products as unknown[]).length} products${d.criteria ? ` by ${d.criteria as string}` : ""}`
        : "Compared product options";
    case "select":
      return d.product_name
        ? `Selected "${d.product_name as string}"${d.price ? ` at $${d.price as number}` : ""}`
        : "Selected a product";
    case "purchase":
      return d.status === "approved"
        ? `Purchase approved${d.amount ? ` for $${d.amount as number}` : ""}`
        : d.status === "denied"
        ? `Purchase denied${d.reason ? `: ${d.reason as string}` : ""}`
        : "Initiated purchase request";
    default:
      return d.description ? String(d.description) : `Agent step: ${step.step_type}`;
  }
}

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

function truncateSignature(sig: string): string {
  if (sig.length <= 16) return sig;
  return sig.slice(0, 8) + "..." + sig.slice(-8);
}

// --- Main Component ---

interface SolanaProofDrawerProps {
  transaction: Transaction;
  open: boolean;
  onClose: () => void;
}

export default function SolanaProofDrawer({ transaction, open, onClose }: SolanaProofDrawerProps) {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [stepsLoading, setStepsLoading] = useState(false);
  const [stepsError, setStepsError] = useState<string | null>(null);

  const [solanaTx, setSolanaTx] = useState<SolanaTxInfo | null>(null);
  const [solanaLoading, setSolanaLoading] = useState(false);

  const [rawExpanded, setRawExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const evidence = transaction.evidence;

  // Fetch agent steps
  useEffect(() => {
    if (!open) return;
    if (!transaction.session_id) return;

    setStepsLoading(true);
    setStepsError(null);
    getAgentSteps(transaction.session_id)
      .then(setSteps)
      .catch((err) => setStepsError(String(err)))
      .finally(() => setStepsLoading(false));
  }, [open, transaction.session_id]);

  // Fetch Solana tx info
  useEffect(() => {
    if (!open) return;
    if (!transaction.solana_tx_signature) return;

    setSolanaLoading(true);
    fetchSolanaTxInfo(transaction.solana_tx_signature)
      .then(setSolanaTx)
      .finally(() => setSolanaLoading(false));
  }, [open, transaction.solana_tx_signature]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  const handleCopySignature = useCallback(async () => {
    if (!transaction.solana_tx_signature) return;
    try {
      await navigator.clipboard.writeText(transaction.solana_tx_signature);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard API may fail in some contexts
    }
  }, [transaction.solana_tx_signature]);

  // Build summary section
  const policyPassed = evidence?.policy_checks?.filter((c) => c.result === "pass").length ?? 0;
  const policyTotal = evidence?.policy_checks?.length ?? 0;
  const policyFailed = evidence?.policy_checks?.filter((c) => c.result !== "pass") ?? [];

  return (
    <>
      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/30 transition-opacity duration-300"
          onClick={onClose}
        />
      )}

      {/* Drawer panel */}
      <div
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-lg flex-col bg-white shadow-xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* A. Header */}
        <div className="flex items-start justify-between border-b border-border px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Transaction Proof</h2>
            <div className="mt-1.5 flex items-center gap-3 text-sm text-text-secondary">
              <span className="font-medium">{transaction.merchant}</span>
              <span className="tabular-nums">${transaction.amount.toFixed(2)}</span>
              <span>
                {new Date(transaction.created_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                })}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface hover:text-text-primary"
            aria-label="Close drawer"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="5" y1="5" x2="15" y2="15" />
              <line x1="15" y1="5" x2="5" y2="15" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">

          {/* B. What Happened */}
          <section>
            <h3 className="text-sm font-semibold text-text-primary mb-3">What Happened</h3>
            {evidence ? (
              <div className="rounded-xl border border-border bg-white p-4 space-y-2">
                <p className="text-sm text-text-secondary">
                  Your agent purchased &lsquo;{evidence.intent_snapshot.product_description}&rsquo; from{" "}
                  {evidence.intent_snapshot.merchant} for ${evidence.intent_snapshot.amount.toFixed(2)}.
                </p>
                <p className="text-sm text-text-secondary">
                  Account had ${evidence.account_state_at_purchase.balance.toFixed(2)} balance with trust score{" "}
                  {evidence.account_state_at_purchase.trust_score} ({evidence.account_state_at_purchase.tier} tier).
                </p>
                <p className="text-sm text-text-secondary">
                  {policyPassed} of {policyTotal} policy checks passed.
                </p>
                {policyFailed.length > 0 && (
                  <ul className="mt-1 space-y-0.5">
                    {policyFailed.map((check, i) => (
                      <li key={i} className="text-sm text-danger">
                        Failed: {check.check}{check.detail ? ` (${check.detail})` : ""}
                      </li>
                    ))}
                  </ul>
                )}
                {evidence.execution_result?.flagged && (
                  <p className="text-sm font-medium text-warning">
                    Post-purchase review found a mismatch.
                  </p>
                )}
                {evidence.gemini_review && (
                  <div className="mt-2 rounded-lg border border-border-light bg-surface p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-text-secondary">Gemini Review</span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          evidence.gemini_review.verdict === "MATCH"
                            ? "bg-success-light text-success"
                            : evidence.gemini_review.verdict === "MISMATCH"
                            ? "bg-danger-light text-danger"
                            : "bg-warning-light text-warning"
                        }`}
                      >
                        {evidence.gemini_review.verdict}
                      </span>
                      {evidence.gemini_review.confidence !== undefined && (
                        <span className="text-xs text-text-muted">
                          {(evidence.gemini_review.confidence * 100).toFixed(0)}% confidence
                        </span>
                      )}
                    </div>
                    <p className="mt-1.5 text-xs text-text-secondary leading-relaxed">
                      {evidence.gemini_review.reasoning}
                    </p>
                    {evidence.gemini_review.flagged_issues && evidence.gemini_review.flagged_issues.length > 0 && (
                      <ul className="mt-1 list-disc pl-4">
                        {evidence.gemini_review.flagged_issues.map((issue, i) => (
                          <li key={i} className="text-xs text-danger">{issue}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-border bg-surface px-4 py-6 text-center text-sm text-text-muted">
                Evidence bundle not available for this transaction.
              </div>
            )}
          </section>

          {/* C. Agent Activity Timeline */}
          <section>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Agent Activity</h3>
            {!transaction.session_id ? (
              <div className="rounded-xl border border-border bg-surface px-4 py-6 text-center text-sm text-text-muted">
                No audit trail available
              </div>
            ) : stepsLoading ? (
              <div className="rounded-xl border border-border bg-white px-4 py-6 text-center text-sm text-text-muted">
                Loading agent activity...
              </div>
            ) : stepsError ? (
              <div className="rounded-xl border border-border bg-danger-light px-4 py-6 text-center text-sm text-danger">
                Failed to load agent steps
              </div>
            ) : steps.length === 0 ? (
              <div className="rounded-xl border border-border bg-surface px-4 py-6 text-center text-sm text-text-muted">
                No steps recorded for this session
              </div>
            ) : (
              <div className="rounded-xl border border-border bg-white p-4">
                <div className="relative pl-6">
                  {/* Vertical timeline line */}
                  <div className="absolute left-[7px] top-2 bottom-2 w-0.5 bg-border" />

                  <div className="space-y-4">
                    {steps.map((step) => {
                      const config = getStepConfig(step.step_type);
                      return (
                        <div key={step.id} className="relative">
                          {/* Dot */}
                          <div
                            className={`absolute -left-6 top-1 h-3.5 w-3.5 rounded-full border-2 border-white ${config.dotColor}`}
                          />
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-semibold ${config.color}`}>
                                {config.label}
                              </span>
                              <span className="text-xs text-text-muted">
                                {relativeTime(step.created_at)}
                              </span>
                            </div>
                            <p className="mt-0.5 text-sm text-text-secondary">
                              {describeStep(step)}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* D. Solana Verification */}
          <section>
            <h3 className="text-sm font-semibold text-text-primary mb-3">Solana Verification</h3>
            {transaction.solana_tx_signature ? (
              <div className="rounded-xl border border-border bg-white p-4 space-y-3">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-success-light px-3 py-1 text-sm font-medium text-success">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M2.5 7.5L5.5 10.5L11.5 3.5" />
                  </svg>
                  Verified on Solana
                </span>

                {solanaLoading ? (
                  <p className="text-sm text-text-muted">Loading on-chain data...</p>
                ) : solanaTx ? (
                  <div className="space-y-2 text-sm">
                    {solanaTx.block !== null && (
                      <div className="flex justify-between">
                        <span className="text-text-muted">Block</span>
                        <span className="font-mono text-text-secondary tabular-nums">{solanaTx.block.toLocaleString()}</span>
                      </div>
                    )}
                    {solanaTx.timestamp !== null && (
                      <div className="flex justify-between">
                        <span className="text-text-muted">Timestamp</span>
                        <span className="text-text-secondary">
                          {new Date(solanaTx.timestamp * 1000).toLocaleString()}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-text-muted">Fee</span>
                      <span className="font-mono text-text-secondary tabular-nums">{solanaTx.fee.toFixed(9)} SOL</span>
                    </div>
                    {solanaTx.memo && (
                      <div>
                        <span className="text-text-muted">Memo</span>
                        <pre className="mt-1 rounded-lg bg-surface p-2 font-mono text-xs text-text-secondary overflow-x-auto">
                          {solanaTx.memo}
                        </pre>
                      </div>
                    )}
                  </div>
                ) : null}

                <div className="flex items-center gap-2">
                  <span className="text-sm text-text-muted">Signature:</span>
                  <code className="font-mono text-xs text-text-secondary">
                    {truncateSignature(transaction.solana_tx_signature)}
                  </code>
                  <button
                    onClick={handleCopySignature}
                    className="rounded px-1.5 py-0.5 text-xs font-medium text-accent transition-colors hover:bg-accent-light"
                  >
                    {copied ? "Copied" : "Copy"}
                  </button>
                </div>

                <a
                  href={`https://explorer.solana.com/tx/${transaction.solana_tx_signature}?cluster=devnet`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm font-medium text-accent hover:text-accent-hover"
                >
                  View on Solana Explorer
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3.5 2H10V8.5" />
                    <path d="M10 2L2 10" />
                  </svg>
                </a>
              </div>
            ) : (
              <div className="rounded-xl border border-border bg-white p-4">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-warning-light px-3 py-1 text-sm font-medium text-warning">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <circle cx="7" cy="7" r="5.5" />
                    <path d="M7 4.5V7.5" />
                    <circle cx="7" cy="9.5" r="0.5" fill="currentColor" />
                  </svg>
                  Not yet anchored
                </span>
                <p className="mt-2 text-sm text-text-muted">
                  This transaction has not been anchored to Solana yet. Anchoring happens after purchase completion.
                </p>
              </div>
            )}
          </section>

          {/* E. Raw Evidence (collapsible) */}
          {evidence && (
            <section>
              <button
                onClick={() => setRawExpanded(!rawExpanded)}
                className="text-xs font-medium text-accent hover:text-accent-hover"
              >
                {rawExpanded ? "Hide raw data" : "View raw data"}
              </button>
              {rawExpanded && (
                <pre className="mt-2 rounded-lg bg-surface p-4 font-mono text-xs text-text-secondary overflow-x-auto">
                  {JSON.stringify(evidence, null, 2)}
                </pre>
              )}
            </section>
          )}
        </div>
      </div>
    </>
  );
}
