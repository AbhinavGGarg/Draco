"use client";

import { useState } from "react";
import type { Transaction } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";

interface SpendingChartProps {
  transactions: Transaction[];
}

type Range = "7d" | "30d" | "all";

const RANGE_OPTIONS: { key: Range; label: string }[] = [
  { key: "7d", label: "7D" },
  { key: "30d", label: "30D" },
  { key: "all", label: "All" },
];

export default function SpendingChart({ transactions }: SpendingChartProps) {
  const [range, setRange] = useState<Range>("7d");

  const now = new Date();
  const getDaysBack = (r: Range) => (r === "7d" ? 7 : r === "30d" ? 30 : 90);

  const daysBack = getDaysBack(range);

  const buckets: { label: string; date: Date; amount: number }[] = [];
  for (let i = daysBack; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const label = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    buckets.push({ label, date: new Date(d.toDateString()), amount: 0 });
  }

  transactions
    .filter(t => t.status === "completed")
    .forEach(tx => {
      const txDate = new Date(new Date(tx.created_at).toDateString());
      const bucket = buckets.find(b => b.date.getTime() === txDate.getTime());
      if (bucket) bucket.amount += tx.amount;
    });

  const totalVolume = buckets.reduce((s, b) => s + b.amount, 0);
  const maxAmount = Math.max(...buckets.map(b => b.amount), 1);

  const W = 1000;
  const H = 200;
  const PAD_X = 0;
  const PAD_Y = 20;
  const chartW = W - PAD_X * 2;
  const chartH = H - PAD_Y * 2;

  const points = buckets.map((b, i) => {
    const x = PAD_X + (i / Math.max(buckets.length - 1, 1)) * chartW;
    const y = PAD_Y + chartH - (b.amount / maxAmount) * chartH;
    return { x, y, ...b };
  });

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
    .join(" ");

  const areaPath = [
    `M ${points[0]?.x ?? 0} ${H}`,
    ...points.map(p => `L ${p.x} ${p.y}`),
    `L ${points[points.length - 1]?.x ?? W} ${H}`,
    "Z",
  ].join(" ");

  return (
    <div className="bg-surface border border-border rounded-none p-6 flex flex-col justify-between mb-8 overflow-hidden">
      <div className="flex items-start justify-between mb-8">
        <div>
          <h2 className="text-sm font-medium text-text-secondary mb-2">Spending volume</h2>
          <div className="flex gap-1 items-baseline">
            <span className="text-3xl font-semibold text-text-primary tabular-nums">${totalVolume.toFixed(2)}</span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-text-muted mb-2">Period</p>
          <div className="inline-flex border border-border bg-background overflow-hidden">
            {RANGE_OPTIONS.map((opt) => (
              <button
                key={opt.key}
                onClick={() => setRange(opt.key)}
                className={`px-3 py-1.5 text-xs font-medium transition-colors border-l border-border first:border-l-0 ${
                  range === opt.key
                    ? "text-accent bg-accent-light"
                    : "text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="w-full mt-4">
        <div className="relative w-full h-[180px]">
          <AnimatePresence mode="wait">
            <motion.svg
              key={range}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              viewBox={`0 0 ${W} ${H}`}
              preserveAspectRatio="none"
              className="absolute inset-0 w-full h-full"
              style={{ overflow: "visible" }}
            >
              <defs>
                <linearGradient id="indigoArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#111827" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="#111827" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {[0.25, 0.5, 0.75, 1].map(v => (
                <line
                  key={v}
                  x1={0} y1={PAD_Y + chartH - v * chartH}
                  x2={W} y2={PAD_Y + chartH - v * chartH}
                  stroke="#E5E7EB"
                  strokeWidth="1"
                />
              ))}

              <motion.path
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 0.1 }}
                d={areaPath}
                fill="url(#indigoArea)"
              />

              <line x1={0} y1={H} x2={W} y2={H} stroke="#E5E7EB" strokeWidth="1" />

              <motion.path
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 1 }}
                transition={{ duration: 1.2, ease: "easeInOut" }}
                d={linePath}
                fill="none"
                stroke="#111827"
                strokeWidth="2"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </motion.svg>
          </AnimatePresence>
        </div>

        <div className="flex justify-between mt-3 px-1">
          <span className="text-xs text-text-muted">{buckets[0].label}</span>
          {buckets.length > 14 && (
            <span className="text-xs text-text-muted">{buckets[Math.floor(buckets.length / 2)].label}</span>
          )}
          <span className="text-xs text-text-muted">{buckets[buckets.length - 1].label}</span>
        </div>
      </div>
    </div>
  );
}
