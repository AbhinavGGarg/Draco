"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { AgentStep } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_FLASK_API_URL || "http://localhost:5001";

interface LiveAuditTrailProps {
  agentId: string;
}

function formatTime(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function translateStep(step: AgentStep): string {
  const { step_type, data } = step;

  switch (step_type) {
    case "search":
      return `Searched for '${data.query ?? "products"}'`;
    case "compare":
      return `Compared ${Array.isArray(data.products) ? data.products.length : "multiple"} products`;
    case "select":
      return `Selected item from ${data.merchant ?? "merchant"} for $${data.amount ?? "?"}`;
    case "purchase":
      return `Completed purchase for $${data.amount ?? "?"}`;
    case "constraint_check":
      return "Validated spending constraints";
    case "trust_check":
      return `Verified trust score: ${data.score ?? "?"} (${data.tier ?? "?"})`;
    default:
      return `Agent action: ${step_type}`;
  }
}

export default function LiveAuditTrail({ agentId }: LiveAuditTrailProps) {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const seenIds = useRef<Set<string>>(new Set());

  const fetchSteps = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_URL}/api/agents/${agentId}/live-steps?limit=20`,
        { headers: { "Content-Type": "application/json" } }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({ error: res.statusText }));
        throw new Error(err.error || res.statusText);
      }
      const data: AgentStep[] = await res.json();

      setSteps((prev) => {
        const newSteps = data.filter((s) => !seenIds.current.has(s.id));
        if (newSteps.length === 0) return prev;
        for (const s of newSteps) {
          seenIds.current.add(s.id);
        }
        return [...prev, ...newSteps];
      });
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch steps");
    }
  }, [agentId]);

  useEffect(() => {
    fetchSteps();
    const interval = setInterval(fetchSteps, 3000);
    return () => clearInterval(interval);
  }, [fetchSteps]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [steps]);

  return (
    <div className="rounded-xl border border-border overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center gap-2 bg-[#0f172a] px-4 py-2.5 border-b border-border">
        <span className="relative flex h-2 w-2">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
        </span>
        <span className="font-mono text-sm font-medium text-white">
          Live Audit Trail
        </span>
      </div>

      {/* Terminal body */}
      <div className="h-80 overflow-y-auto bg-[#0f172a] px-4 py-3">
        {error && steps.length === 0 && (
          <p className="font-mono text-xs text-text-muted">
            {error}
          </p>
        )}

        {steps.length === 0 && !error && (
          <p className="font-mono text-xs text-text-muted">
            Waiting for agent activity...
          </p>
        )}

        {steps.map((step, i) => {
          const hasSolana = typeof step.data.solana_tx_signature === "string";
          const sig = hasSolana ? (step.data.solana_tx_signature as string) : null;

          return (
            <div
              key={step.id}
              className="mb-1 font-mono text-xs leading-relaxed transition-opacity duration-300"
              style={{
                animation: `fadeUp 0.3s ease-out ${Math.min(i * 30, 300)}ms forwards`,
                opacity: 0,
              }}
            >
              <span className="text-text-muted">
                [{formatTime(step.created_at)}]
              </span>{" "}
              <span className="text-accent">
                &gt; {translateStep(step)}
              </span>
              {hasSolana && sig && (
                <div className="ml-[4.5ch] mt-0.5">
                  <span className="text-success">
                    {">"} Anchored to Solana [{sig.slice(0, 8)}...{sig.slice(-4)}]
                  </span>
                </div>
              )}
            </div>
          );
        })}

        {/* Blinking cursor */}
        <div className="font-mono text-sm text-accent animate-pulse mt-1">
          {"\u258C"}
        </div>

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
