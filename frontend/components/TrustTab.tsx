"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import type { User, Agent, TrustAnalysis, TrustHistoryPoint } from "@/lib/api";
import { getTrustAnalysis, getTrustHistory } from "@/lib/api";
import TrustScoreBadge from "./TrustScoreBadge";

const FACTOR_KEYS = [
  "purchase_reliability",
  "spending_behavior",
  "dispute_history",
  "category_diversity",
  "account_maturity",
];

const FACTOR_LABELS: Record<string, string> = {
  purchase_reliability: "Reliability",
  spending_behavior: "Spending",
  dispute_history: "Disputes",
  category_diversity: "Diversity",
  account_maturity: "Maturity",
};

const TIERS = [
  { tier: "Frozen", range: "0 — 25", desc: "Agent cannot make purchases", limit: "$0", score: 25 },
  { tier: "Restricted", range: "26 — 50", desc: "Limited merchant access", limit: "$25/tx", score: 50 },
  { tier: "Standard", range: "51 — 75", desc: "Normal spending within limits", limit: "$100/tx", score: 75 },
  { tier: "Trusted", range: "76 — 100", desc: "Full autonomy within your settings", limit: "Your limit", score: 100 },
];

function SpiderChart({ factors }: { factors: Record<string, number> }) {
  const size = 220;
  const cx = size / 2;
  const cy = size / 2;
  const radius = 85;
  const levels = [0.25, 0.5, 0.75, 1.0];
  const angleStep = (2 * Math.PI) / FACTOR_KEYS.length;
  const startAngle = -Math.PI / 2;

  const getPoint = (index: number, value: number) => {
    const angle = startAngle + index * angleStep;
    return { x: cx + radius * value * Math.cos(angle), y: cy + radius * value * Math.sin(angle) };
  };

  const dataPoints = FACTOR_KEYS.map((key, i) => getPoint(i, factors[key] || 0));
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full h-full">
      {levels.map((level) => {
        const pts = FACTOR_KEYS.map((_, i) => getPoint(i, level));
        const path = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") + " Z";
        return <path key={level} d={path} fill="none" stroke="#E5E7EB" strokeWidth="1" />;
      })}
      {FACTOR_KEYS.map((_, i) => {
        const end = getPoint(i, 1);
        return <line key={i} x1={cx} y1={cy} x2={end.x} y2={end.y} stroke="#E5E7EB" strokeWidth="1" />;
      })}
      <motion.path initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6 }}
        d={dataPath} fill="rgba(17, 24, 39, 0.06)" stroke="#111827" strokeWidth="1.5" />
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill="#111827" />
      ))}
      {FACTOR_KEYS.map((key, i) => {
        const lp = getPoint(i, 1.3);
        return (
          <text key={key} x={lp.x} y={lp.y} textAnchor="middle" dominantBaseline="middle"
            className="text-[9px] fill-text-secondary" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
            {FACTOR_LABELS[key]}
          </text>
        );
      })}
    </svg>
  );
}

function TrustHistoryChart({ history }: { history: TrustHistoryPoint[] }) {
  if (history.length < 2) return null;
  const W = 1000;
  const H = 200;
  const PAD_Y = 10;
  const chartH = H - PAD_Y * 2;

  const points = history.map((h, i) => ({
    x: (i / (history.length - 1)) * W,
    y: PAD_Y + chartH - (h.score / 100) * chartH,
  }));
  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const areaPath = `${linePath} L ${W} ${H} L 0 ${H} Z`;

  const firstDate = new Date(history[0].computed_at).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const midDate = new Date(history[Math.floor(history.length / 2)].computed_at).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const lastDate = new Date(history[history.length - 1].computed_at).toLocaleDateString("en-US", { month: "short", day: "numeric" });

  return (
    <div>
      <div className="relative w-full h-[180px]">
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="absolute inset-0 w-full h-full" style={{ overflow: "visible" }}>
          <defs>
            <linearGradient id="trustAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#111827" stopOpacity="0.06" />
              <stop offset="100%" stopColor="#111827" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[25, 50, 75].map((t) => (
            <line key={t} x1={0} y1={PAD_Y + chartH - (t / 100) * chartH} x2={W} y2={PAD_Y + chartH - (t / 100) * chartH} stroke="#E5E7EB" strokeWidth="1" strokeDasharray="4 4" />
          ))}
          <motion.path initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1, delay: 0.3 }} d={areaPath} fill="url(#trustAreaGrad)" />
          <motion.path initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 1 }} transition={{ duration: 1.5, ease: "easeInOut" }}
            d={linePath} fill="none" stroke="#111827" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        </svg>
      </div>
      <div className="flex justify-between mt-2 px-1">
        <span className="text-xs text-text-muted">{firstDate}</span>
        <span className="text-xs text-text-muted">{midDate}</span>
        <span className="text-xs text-text-muted">{lastDate}</span>
      </div>
    </div>
  );
}

interface TrustTabProps {
  user: User;
  agent: Agent;
}

export default function TrustTab({ user, agent }: TrustTabProps) {
  const [analysis, setAnalysis] = useState<TrustAnalysis | null>(null);
  const [history, setHistory] = useState<TrustHistoryPoint[]>([]);

  useEffect(() => {
    getTrustAnalysis(user.id).then(setAnalysis).catch(() => {});
    getTrustHistory(user.id).then(setHistory).catch(() => {});
  }, [user.id]);

  const score = analysis?.score ?? agent.trust_score;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Trust Score</h1>
          <p className="text-sm text-text-muted mt-1">AI-computed from your complete transaction history</p>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-text-muted">
          <div className="w-5 h-5 bg-accent-light flex items-center justify-center">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#111827" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2L2 7l10 5 10-5-10-5z" /><path d="M2 17l10 5 10-5" /><path d="M2 12l10 5 10-5" />
            </svg>
          </div>
          <span>Gemini 3 Flash</span>
        </div>
      </div>

      {/* Hero: Trust History Chart */}
      <div className="bg-surface border border-border p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="text-sm font-medium text-text-secondary mb-2">Trust score over time</p>
            <TrustScoreBadge score={score} size="md" />
          </div>
          {analysis && (
            <div className="text-right">
              <p className="text-xs text-text-muted mb-1">Last updated</p>
              <p className="text-xs text-text-secondary">{new Date(analysis.computed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</p>
            </div>
          )}
        </div>
        {history.length > 1 ? (
          <TrustHistoryChart history={history} />
        ) : (
          <div className="h-[180px] flex items-center justify-center text-sm text-text-muted">
            History will appear after your first purchase
          </div>
        )}
      </div>

      {/* Analysis text */}
      {analysis && (
        <div className="bg-surface border border-border p-6">
          <p className="text-xs text-text-muted mb-3">Gemini expert analysis</p>
          <p className="text-sm text-text-secondary leading-relaxed">{analysis.reasoning}</p>
          {analysis.base_score !== undefined && (
            <p className="text-xs text-text-muted mt-3">
              Model base score: <span className="text-text-primary font-medium tabular-nums">{analysis.base_score}</span>
              {analysis.score !== analysis.base_score && (
                <span> · AI adjustment: <span className="text-text-primary font-medium">{analysis.score > analysis.base_score ? "+" : ""}{analysis.score - analysis.base_score}</span></span>
              )}
            </p>
          )}
        </div>
      )}

      {/* Spider chart + Factor bars — same height, coherent */}
      {analysis && (
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-surface border border-border p-6">
            <p className="text-xs text-text-muted mb-4">Factor Profile</p>
            <div className="flex items-center justify-center" style={{ height: 220 }}>
              <div className="w-[220px] h-[220px]">
                <SpiderChart factors={analysis.factors} />
              </div>
            </div>
          </div>

          <div className="bg-surface border border-border p-6 flex flex-col">
            <p className="text-xs text-text-muted mb-4">Factor Breakdown</p>
            <div className="space-y-5 flex-1 flex flex-col justify-center">
              {FACTOR_KEYS.map((key) => {
                const val = (analysis.factors as Record<string, number>)[key] || 0;
                return (
                  <div key={key} className="flex items-center gap-4">
                    <span className="text-sm text-text-secondary w-24 shrink-0">{FACTOR_LABELS[key]}</span>
                    <div className="flex-1 h-1 bg-border">
                      <motion.div initial={{ width: 0 }} animate={{ width: `${val * 100}%` }} transition={{ duration: 0.8, ease: "easeOut" }} className="h-full bg-text-primary" />
                    </div>
                    <span className="text-sm text-text-primary tabular-nums font-medium w-8 text-right">{(val * 100).toFixed(0)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Tier system — 4 equal columns, coherent */}
      <div className="grid grid-cols-4 gap-px bg-border border border-border">
        {TIERS.map((t, i) => {
          const isActive = score <= t.score && (i === 0 || score > TIERS[i - 1].score);
          return (
            <div key={t.tier} className={`p-5 ${isActive ? "bg-surface" : "bg-background"}`}>
              <div className="flex items-center justify-between mb-3">
                <p className={`text-sm font-semibold ${isActive ? "text-text-primary" : "text-text-muted"}`}>{t.tier}</p>
                <span className={`text-[10px] tabular-nums ${isActive ? "text-text-secondary" : "text-text-muted"}`}>{t.range}</span>
              </div>
              <p className={`text-xs ${isActive ? "text-text-secondary" : "text-text-muted"}`}>{t.desc}</p>
              <p className={`text-xs mt-2 pt-2 border-t border-border ${isActive ? "text-text-primary font-medium" : "text-text-muted"}`}>{t.limit}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
