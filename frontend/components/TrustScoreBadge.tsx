"use client";

import { scoreToTier } from "@/lib/api";

const tierConfig: Record<string, { label: string; bg: string; text: string; dot: string }> = {
  frozen:     { label: "Frozen",     bg: "bg-danger-light",  text: "text-danger",  dot: "bg-danger" },
  restricted: { label: "Restricted", bg: "bg-warning-light", text: "text-warning", dot: "bg-warning" },
  standard:   { label: "Standard",   bg: "bg-accent-light",  text: "text-accent",  dot: "bg-accent" },
  trusted:    { label: "Trusted",    bg: "bg-success-light", text: "text-success", dot: "bg-success" },
};

interface TrustScoreBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

export default function TrustScoreBadge({ score, size = "md" }: TrustScoreBadgeProps) {
  const tier = scoreToTier(score);
  const config = tierConfig[tier];

  const sizeStyles = {
    sm: { score: "text-lg", label: "text-xs px-2 py-0.5" },
    md: { score: "text-3xl", label: "text-xs px-2.5 py-1" },
    lg: { score: "text-5xl", label: "text-sm px-3 py-1.5" },
  };

  return (
    <div className="flex items-center gap-3">
      <span className={`font-semibold tracking-tight tabular-nums text-text-primary ${sizeStyles[size].score}`}>{score}</span>
      <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${config.bg} ${config.text} ${sizeStyles[size].label}`}>
        <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} />
        {config.label}
      </span>
    </div>
  );
}
