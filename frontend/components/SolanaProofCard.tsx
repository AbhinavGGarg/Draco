"use client";

import { useEffect, useState, useCallback } from "react";
import type { Transaction } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_FLASK_API_URL || "http://localhost:5001";

interface SolanaTxInfo {
  signature: string;
  block_time: number | null;
  slot: number;
  fee_lamports: number;
  fee_sol: number;
  memo: string | null;
  confirmations: string;
  success: boolean;
  explorer_url: string;
}

interface ParsedMemo {
  sid?: string;
  root?: string;
  txid?: string;
}

interface SolanaProofCardProps {
  transactions: Transaction[];
}

function truncate(str: string, startLen = 12, endLen = 12): string {
  if (str.length <= startLen + endLen + 3) return str;
  return str.slice(0, startLen) + "..." + str.slice(-endLen);
}

function formatTimestamp(unixSeconds: number): string {
  const date = new Date(unixSeconds * 1000);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatSlot(slot: number): string {
  return slot.toLocaleString();
}

export default function SolanaProofCard({ transactions }: SolanaProofCardProps) {
  const [txInfo, setTxInfo] = useState<SolanaTxInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const anchoredTxs = transactions.filter(
    (t) => t.solana_tx_signature && t.solana_tx_signature.length > 0
  );

  const mostRecent = anchoredTxs.length > 0
    ? [...anchoredTxs].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )[0]
    : null;

  const signature = mostRecent?.solana_tx_signature ?? null;

  const fetchTxData = useCallback(async () => {
    if (!signature) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/solana/tx/${signature}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error || res.statusText);
      }
      const data: SolanaTxInfo = await res.json();
      setTxInfo(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to fetch on-chain data");
    } finally {
      setLoading(false);
    }
  }, [signature]);

  useEffect(() => {
    fetchTxData();
  }, [fetchTxData]);

  const handleCopy = async () => {
    if (!txInfo) return;
    try {
      await navigator.clipboard.writeText(txInfo.signature);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard API may fail in some contexts
    }
  };

  let parsedMemo: ParsedMemo | null = null;
  if (txInfo?.memo) {
    try {
      parsedMemo = JSON.parse(txInfo.memo) as ParsedMemo;
    } catch {
      parsedMemo = null;
    }
  }

  // Empty state: no anchored transactions
  if (anchoredTxs.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-white p-5">
        <div className="flex items-center gap-2 mb-3">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-accent">
            <path
              d="M10 2L3 6v8l7 4 7-4V6l-7-4z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
            <path
              d="M3 6l7 4m0 0l7-4M10 10v8"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
          <h3 className="text-sm font-semibold text-text-primary">On-Chain Proof</h3>
        </div>
        <p className="text-sm text-text-muted">No proofs anchored yet</p>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="rounded-xl border border-border bg-white p-5">
        <div className="flex items-center gap-2 mb-4">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-accent">
            <path
              d="M10 2L3 6v8l7 4 7-4V6l-7-4z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
            <path
              d="M3 6l7 4m0 0l7-4M10 10v8"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
          <h3 className="text-sm font-semibold text-text-primary">On-Chain Proof</h3>
        </div>
        <div className="space-y-3">
          <div className="h-4 w-24 animate-pulse rounded bg-surface" />
          <div className="h-4 w-full animate-pulse rounded bg-surface" />
          <div className="h-4 w-3/4 animate-pulse rounded bg-surface" />
          <div className="h-4 w-1/2 animate-pulse rounded bg-surface" />
          <div className="h-16 w-full animate-pulse rounded bg-surface" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-xl border border-border bg-white p-5">
        <div className="flex items-center gap-2 mb-3">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-accent">
            <path
              d="M10 2L3 6v8l7 4 7-4V6l-7-4z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
            <path
              d="M3 6l7 4m0 0l7-4M10 10v8"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
          <h3 className="text-sm font-semibold text-text-primary">On-Chain Proof</h3>
        </div>
        <p className="text-sm text-text-secondary mb-3">Unable to fetch on-chain data</p>
        <button
          onClick={fetchTxData}
          className="rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-accent-hover"
        >
          Retry
        </button>
      </div>
    );
  }

  // Success state
  if (!txInfo) return null;

  return (
    <div className="rounded-xl border border-border bg-white p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" className="text-accent">
            <path
              d="M10 2L3 6v8l7 4 7-4V6l-7-4z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
            <path
              d="M3 6l7 4m0 0l7-4M10 10v8"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
          <h3 className="text-sm font-semibold text-text-primary">On-Chain Proof</h3>
        </div>
        {/* Status badge */}
        {txInfo.success && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-success-light px-2.5 py-1 text-xs font-medium text-success">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            Confirmed
          </span>
        )}
      </div>

      {/* Data rows */}
      <div className="divide-y divide-border-light">
        <div className="flex items-center justify-between py-2.5">
          <span className="text-sm text-text-secondary">Block</span>
          <span className="text-sm font-medium text-text-primary tabular-nums">
            {formatSlot(txInfo.slot)}
          </span>
        </div>
        <div className="flex items-center justify-between py-2.5">
          <span className="text-sm text-text-secondary">Time</span>
          <span className="text-sm font-medium text-text-primary">
            {txInfo.block_time ? formatTimestamp(txInfo.block_time) : "Pending"}
          </span>
        </div>
        <div className="flex items-center justify-between py-2.5">
          <span className="text-sm text-text-secondary">Fee</span>
          <span className="text-sm font-medium text-text-primary font-mono">
            {txInfo.fee_sol} SOL
          </span>
        </div>
        <div className="flex items-center justify-between py-2.5">
          <span className="text-sm text-text-secondary">Status</span>
          <span className="text-sm font-medium text-text-primary">
            {txInfo.confirmations}
          </span>
        </div>
      </div>

      {/* Memo section */}
      {parsedMemo && (
        <div className="mt-4">
          <p className="text-xs font-medium text-text-secondary mb-2">Anchored Memo</p>
          <div className="rounded-lg bg-surface p-3 font-mono text-sm space-y-1.5">
            {parsedMemo.sid && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-text-muted text-xs">Session</span>
                <span className="text-text-primary text-xs truncate max-w-[200px]">
                  {truncate(parsedMemo.sid, 8, 8)}
                </span>
              </div>
            )}
            {parsedMemo.root && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-text-muted text-xs">Root</span>
                <span className="text-text-primary text-xs truncate max-w-[200px]">
                  {truncate(parsedMemo.root, 8, 8)}
                </span>
              </div>
            )}
            {parsedMemo.txid && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-text-muted text-xs">Transaction</span>
                <span className="text-text-primary text-xs truncate max-w-[200px]">
                  {truncate(parsedMemo.txid, 8, 8)}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Signature row */}
      <div className="mt-4 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-medium text-text-secondary mb-1">Signature</p>
          <p className="text-xs font-mono text-text-primary truncate">
            {truncate(txInfo.signature)}
          </p>
        </div>
        <button
          onClick={handleCopy}
          className="shrink-0 rounded-lg border border-border px-2.5 py-1.5 text-xs font-medium text-text-secondary transition-colors hover:bg-surface hover:text-text-primary"
          title="Copy signature to clipboard"
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {/* Explorer link */}
      <div className="mt-4">
        <a
          href={txInfo.explorer_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-accent transition-colors hover:text-accent-hover"
        >
          View on Solana Explorer &#x2197;
        </a>
      </div>

      {/* Footer */}
      <div className="mt-4 border-t border-border-light pt-3">
        <p className="text-xs text-text-muted">
          Total proofs: {anchoredTxs.length}
        </p>
      </div>
    </div>
  );
}
