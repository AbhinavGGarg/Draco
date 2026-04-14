"use client";

import Link from "next/link";
import { motion, useMotionValue, useTransform, animate, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import NavHeader from "@/components/NavHeader";

const spring = { type: "spring" as const, stiffness: 300, damping: 24 };

const rotatingPhrases = ["Rules you set.", "Trust built in.", "You decide."];

const transactions = [
  { merchant: "Amazon", amount: "$29.99", status: "Completed" },
  { merchant: "Best Buy", amount: "$149.00", status: "Pending" },
  { merchant: "Target", amount: "$12.50", status: "Completed" },
  { merchant: "Walmart", amount: "$67.20", status: "Completed" },
];

function TypingRotator() {
  const [phraseIndex, setPhraseIndex] = useState(0);
  const [displayed, setDisplayed] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const phrase = rotatingPhrases[phraseIndex];

    if (!isDeleting && displayed === phrase) {
      // Pause before deleting
      const timeout = setTimeout(() => setIsDeleting(true), 2000);
      return () => clearTimeout(timeout);
    }

    if (isDeleting && displayed === "") {
      // Move to next phrase
      setIsDeleting(false);
      setPhraseIndex((prev) => (prev + 1) % rotatingPhrases.length);
      return;
    }

    const speed = isDeleting ? 40 : 80;
    const timeout = setTimeout(() => {
      if (isDeleting) {
        setDisplayed(phrase.slice(0, displayed.length - 1));
      } else {
        setDisplayed(phrase.slice(0, displayed.length + 1));
      }
    }, speed);

    return () => clearTimeout(timeout);
  }, [displayed, isDeleting, phraseIndex]);

  return (
    <span className="text-text-primary">
      {displayed}
      <motion.span
        animate={{ opacity: [1, 0] }}
        transition={{ duration: 0.6, repeat: Infinity, repeatType: "reverse" }}
        className="inline-block w-[3px] h-[0.85em] bg-accent ml-1 align-baseline translate-y-[2px]"
      />
    </span>
  );
}

function AnimatedCounter({ target, delay = 0.4 }: { target: number; delay?: number }) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (v) => Math.round(v));

  useEffect(() => {
    const controls = animate(count, target, {
      duration: 1.6,
      ease: "easeOut",
      delay,
    });
    return controls.stop;
  }, [count, target, delay]);

  return (
    <motion.span className="text-6xl font-bold text-text-primary tabular-nums">
      {rounded}
    </motion.span>
  );
}

/* Large background chart — middle layer, jagged and interesting */
function BackgroundChart() {
  const W = 1400;
  const H = 600;
  // Peak at ~2/3, right side: same as before but last point goes down not up
  const points = [
    15, 40, 30, 80, 55, 120, 90, 180,
    150, 280, 220, 420, 350, 500,
    380, 450, 360, 430, 370, 340,
  ];
  const max = Math.max(...points);
  const startX = W * 0.25;
  const chartW = W - startX;
  const coords = points.map((v, i) => ({
    x: startX + (i / (points.length - 1)) * chartW,
    y: H - (v / max) * (H - 30) - 15,
  }));

  // Find peak point for the annotation
  const peakIndex = points.indexOf(max);
  const peakCoord = coords[peakIndex];

  const linePath = coords.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const areaPath = `${linePath} L ${W} ${H} L ${startX} ${H} Z`;

  // Annotation line extends left from the dot
  const dotX = peakCoord.x;
  const dotY = peakCoord.y;
  const lineEndX = dotX - 160;

  return (
    <div className="absolute inset-0 pointer-events-none z-[5]">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="absolute bottom-0 left-0 w-full"
        style={{ height: "85%", overflow: "visible" }}
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="bgChartGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#111827" stopOpacity="0.14" />
            <stop offset="50%" stopColor="#111827" stopOpacity="0.06" />
            <stop offset="100%" stopColor="#111827" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Area fill */}
        <motion.path
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.5, delay: 2.0 }}
          d={areaPath}
          fill="url(#bgChartGrad)"
        />

        {/* Line — draws itself, sharp jagged */}
        <motion.path
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.3 }}
          transition={{ duration: 3, delay: 0.3, ease: "easeInOut" }}
          d={linePath}
          fill="none"
          stroke="#111827"
          strokeWidth="2"
          strokeLinejoin="miter"
          strokeLinecap="square"
        />

        {/* Peak annotation: line extending left from dot */}
        <motion.line
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.8 }}
          transition={{ duration: 0.5, delay: 3.2 }}
          x1={lineEndX} y1={dotY}
          x2={dotX} y2={dotY}
          stroke="#111827"
          strokeWidth="1"
        />

        {/* Peak dot */}
        <motion.circle
          initial={{ opacity: 0, r: 0 }}
          animate={{ opacity: 1, r: 4 }}
          transition={{ duration: 0.3, delay: 3.0 }}
          cx={dotX}
          cy={dotY}
          fill="#111827"
        />

        {/* Peak label */}
        <motion.text
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 3.4 }}
          x={lineEndX - 8}
          y={dotY - 10}
          textAnchor="end"
          className="text-[13px] font-semibold"
          fill="#111827"
          style={{ fontFamily: "Inter, system-ui, sans-serif" }}
        >
          Risk threshold exceeded
        </motion.text>
        <motion.text
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.7 }}
          transition={{ duration: 0.5, delay: 3.6 }}
          x={lineEndX - 8}
          y={dotY + 8}
          textAnchor="end"
          className="text-[11px]"
          fill="#111827"
          style={{ fontFamily: "Inter, system-ui, sans-serif" }}
        >
          Agent paused for review
        </motion.text>
      </svg>
    </div>
  );
}

/* Trust card — compact, bottom right */
function TrustCard() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20, filter: "blur(4px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ ...spring, delay: 0.5 }}
      className="border border-border bg-surface w-[480px] divide-y divide-border origin-bottom-right"
    >
      {/* Trust Score */}
      <div className="p-7">
        <div className="text-sm text-text-muted mb-4">Trust Score</div>
        <div className="flex items-end justify-between">
          <AnimatedCounter target={72} />
          <span className="bg-accent-light text-accent text-sm font-medium px-3 py-1">
            Standard
          </span>
        </div>
        <div className="mt-4 flex items-center gap-2">
          <motion.span
            className="h-2 w-2 rounded-full bg-success"
            animate={{ scale: [1, 1.4, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
          <span className="text-sm text-success font-medium">Normal risk</span>
        </div>
      </div>

      {/* Transaction Feed */}
      <div>
        <div className="px-7 py-3 text-sm text-text-muted border-b border-border bg-background">
          Recent Transactions
        </div>
        {transactions.map((tx, i) => (
          <motion.div
            key={tx.merchant}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ ...spring, delay: 0.8 + i * 0.12 }}
            className="flex items-center justify-between px-7 py-3.5 text-sm border-b border-border last:border-b-0"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 border border-border bg-background flex items-center justify-center text-[10px] font-medium text-text-secondary">
                {tx.merchant.slice(0, 2)}
              </div>
              <span className="text-text-primary font-medium text-sm">{tx.merchant}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-text-secondary tabular-nums text-sm">{tx.amount}</span>
              <span
                className={`text-xs font-medium px-2 py-0.5 ${
                  tx.status === "Completed"
                    ? "bg-success-light text-success"
                    : "bg-warning-light text-warning"
                }`}
              >
                {tx.status}
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

export default function LandingPage() {
  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden relative">
      {/* Layer 0: Partial grid — right/bottom, visible */}
      <div
        className="absolute pointer-events-none"
        style={{
          top: "8%",
          right: 0,
          width: "70%",
          height: "92%",
          backgroundImage:
            "linear-gradient(to right, rgba(0,0,0,0.12) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,0,0,0.12) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          maskImage: "linear-gradient(to left, rgba(0,0,0,0.5) 40%, transparent 100%)",
          WebkitMaskImage: "linear-gradient(to left, rgba(0,0,0,0.5) 40%, transparent 100%)",
        }}
      />

      {/* Layer 1: Big animated chart */}
      <BackgroundChart />

      <NavHeader />

      {/* Layer 2: Content */}
      <main className="flex-1 flex flex-col relative z-10">
        {/* Top: big text, left aligned */}
        <div className="flex-1 flex items-center px-16 pl-[12%]">
          <motion.div
            initial={{ opacity: 0, y: 20, filter: "blur(4px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            transition={spring}
            className="max-w-3xl"
          >
            <h1 className="text-8xl font-bold tracking-tight leading-[1.05]">
              <span className="text-text-primary">AI that buys.</span>
              <br />
              <TypingRotator />
            </h1>
            <p className="mt-8 text-xl text-text-secondary max-w-lg leading-relaxed">
              Squid lets your AI agent shop the internet on your behalf — within
              spending limits, category rules, and trust tiers you control.
            </p>
            <div className="mt-10 flex items-center gap-4">
              <Link
                href="/signup"
                className="bg-accent px-6 py-3 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
              >
                Get Started
              </Link>
              <Link
                href="/product"
                className="border border-border bg-surface px-6 py-3 text-sm font-medium text-text-primary hover:bg-surface-hover transition-colors"
              >
                Read Philosophy
              </Link>
            </div>
          </motion.div>
        </div>

        {/* Bottom right: trust card snuggled into corner */}
        <div className="absolute bottom-0 right-0">
          <TrustCard />
        </div>
      </main>
    </div>
  );
}
