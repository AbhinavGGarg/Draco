"use client";

import { useState, useEffect } from "react";
import type { User, Agent, Constraints, Transaction, EffectiveLimits } from "@/lib/api";
import { updateConstraints, setBalance, resetScore, getEffectiveLimits } from "@/lib/api";
import { AlertTriangle } from "lucide-react";
import StripeCardInput from "./StripeCardInput";

const ALL_CATEGORIES = [
  "electronics", "groceries", "books", "clothing", "home", "office",
  "health", "beauty", "sports", "toys", "automotive", "garden",
  "pet supplies", "food & dining", "travel", "entertainment",
];

interface SettingsTabProps {
  user: User;
  agent: Agent;
  transactions: Transaction[];
  onRefresh: () => void;
}

export default function SettingsTab({ user, agent, transactions, onRefresh }: SettingsTabProps) {
  const [constraints, setConstraints] = useState<Constraints>(agent.constraints);
  const [balanceInput, setBalanceInput] = useState(String(user.balance));
  const [newMerchant, setNewMerchant] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const [limits, setLimits] = useState<EffectiveLimits | null>(null);

  useEffect(() => {
    getEffectiveLimits(user.id).then(setLimits).catch(() => {});
  }, [user.id]);

  const flash = (text: string, ok: boolean) => {
    setMessage({ text, ok });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleSaveConstraints = async () => {
    setSaving(true);
    try {
      await updateConstraints(user.id, constraints);
      flash("Settings saved successfully", true);
      onRefresh();
      getEffectiveLimits(user.id).then(setLimits).catch(() => {});
    } catch (err) {
      flash(err instanceof Error ? err.message : "Failed to save", false);
    } finally {
      setSaving(false);
    }
  };

  const handleSetBalance = async () => {
    const amt = parseFloat(balanceInput);
    if (isNaN(amt) || amt < 0) return;
    setSaving(true);
    try {
      await setBalance(user.id, amt);
      flash("Balance updated", true);
      onRefresh();
    } catch (err) {
      flash(err instanceof Error ? err.message : "Failed to update balance", false);
    } finally {
      setSaving(false);
    }
  };

  const handleResetScore = async () => {
    setSaving(true);
    try {
      const res = await resetScore(user.id);
      flash(`Score reset to ${res.trust_score} (${res.tier}).`, true);
      onRefresh();
      getEffectiveLimits(user.id).then(setLimits).catch(() => {});
    } catch (err) {
      flash(err instanceof Error ? err.message : "Failed to reset score", false);
    } finally {
      setSaving(false);
    }
  };

  const toggleCategory = (cat: string) => {
    setConstraints((prev) => ({
      ...prev,
      allowed_categories: prev.allowed_categories.includes(cat)
        ? prev.allowed_categories.filter((c) => c !== cat)
        : [...prev.allowed_categories, cat],
    }));
  };

  const addMerchant = async () => {
    const trimmed = newMerchant.trim().toLowerCase();
    if (!trimmed || constraints.blocked_merchants.includes(trimmed)) return;
    const updated = { ...constraints, blocked_merchants: [...constraints.blocked_merchants, trimmed] };
    setConstraints(updated);
    setNewMerchant("");
    try {
      await updateConstraints(user.id, { blocked_merchants: updated.blocked_merchants });
      onRefresh();
    } catch {
      flash("Failed to save merchant", false);
    }
  };

  const removeMerchant = async (m: string) => {
    const updated = { ...constraints, blocked_merchants: constraints.blocked_merchants.filter((x) => x !== m) };
    setConstraints(updated);
    try {
      await updateConstraints(user.id, { blocked_merchants: updated.blocked_merchants });
      onRefresh();
    } catch {
      flash("Failed to remove merchant", false);
    }
  };

  // Weekly spending calculation
  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
  const weeklySpent = transactions
    .filter((t) => t.status === "completed" && new Date(t.created_at) >= weekAgo)
    .reduce((sum, t) => sum + t.amount, 0);
  const weeklyLimit = constraints.max_per_week;
  const weeklyPct = Math.min((weeklySpent / weeklyLimit) * 100, 100);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-border">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Settings</h1>
          <p className="text-sm text-text-muted mt-1">Manage spending limits and permissions</p>
        </div>
      </div>

      {message && (
        <div className={`p-4 flex items-center gap-3 text-sm font-medium ${message.ok ? "bg-success-light border border-success/20 text-success" : "bg-danger-light border border-danger/20 text-danger"}`}>
          <span>{message.text}</span>
        </div>
      )}

      {/* Override warnings */}
      {limits && limits.overrides.length > 0 && (
        <div className="p-4 bg-warning-light border border-warning/20 flex items-start gap-3">
          <AlertTriangle size={16} className="text-warning shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-warning">Active overrides</p>
            {limits.overrides.map((o, i) => (
              <p key={i} className="text-sm text-text-secondary mt-1">{o}</p>
            ))}
          </div>
        </div>
      )}

      {/* Weekly spending progress */}
      <div className="bg-surface border border-border p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold text-text-primary">Weekly spending</h3>
          <span className="text-sm text-text-secondary tabular-nums">
            ${weeklySpent.toFixed(2)} <span className="text-text-muted">/ ${weeklyLimit.toFixed(2)}</span>
          </span>
        </div>
        <div className="w-full h-2 bg-background border border-border">
          <div
            className={`h-full transition-all ${weeklyPct > 80 ? "bg-danger" : weeklyPct > 50 ? "bg-warning" : "bg-accent"}`}
            style={{ width: `${weeklyPct}%` }}
          />
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-xs text-text-muted">{weeklyPct.toFixed(0)}% used</span>
          <span className="text-xs text-text-muted">${(weeklyLimit - weeklySpent).toFixed(2)} remaining</span>
        </div>
        {limits && (
          <div className="mt-3 pt-3 border-t border-border flex items-center gap-4 text-xs text-text-muted">
            <span>Effective tx limit: <span className="text-text-primary font-medium tabular-nums">${limits.effective_max_per_transaction}</span></span>
            <span>Tier: <span className="text-text-primary font-medium capitalize">{limits.tier}</span></span>
          </div>
        )}
      </div>

      {/* Spending limits */}
      <div className="bg-surface border border-border p-6">
        <h3 className="text-sm font-semibold text-text-primary border-b border-border pb-3 mb-6">Spending limits</h3>
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm text-text-secondary mb-2">Max per transaction</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">$</span>
              <input type="number" value={constraints.max_per_transaction} onChange={(e) => setConstraints((p) => ({ ...p, max_per_transaction: Number(e.target.value) }))} className="w-full bg-background border border-border pl-7 pr-3 py-2.5 text-sm tabular-nums focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none text-text-primary transition-colors" />
            </div>
            {limits && limits.effective_max_per_transaction < constraints.max_per_transaction && (
              <p className="text-xs text-warning mt-1">Effective: ${limits.effective_max_per_transaction} (override active)</p>
            )}
          </div>
          <div>
            <label className="block text-sm text-text-secondary mb-2">Max per week</label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">$</span>
              <input type="number" value={constraints.max_per_week} onChange={(e) => setConstraints((p) => ({ ...p, max_per_week: Number(e.target.value) }))} className="w-full bg-background border border-border pl-7 pr-3 py-2.5 text-sm tabular-nums focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none text-text-primary transition-colors" />
            </div>
          </div>
        </div>
      </div>

      {/* Allowed categories */}
      <div className="bg-surface border border-border p-6">
        <div className="flex justify-between items-center border-b border-border pb-3 mb-6">
          <h3 className="text-sm font-semibold text-text-primary">Allowed categories</h3>
          <span className="text-xs text-text-muted">{constraints.allowed_categories.length} of {ALL_CATEGORIES.length} selected</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {ALL_CATEGORIES.map((cat) => {
            const isActive = constraints.allowed_categories.includes(cat);
            return (
              <button key={cat} onClick={() => toggleCategory(cat)} className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all border capitalize ${isActive ? "bg-accent-light border-accent/30 text-accent" : "bg-background border-border text-text-muted hover:border-text-secondary hover:text-text-secondary"}`}>
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      {/* Blocked merchants */}
      <div className="bg-surface border border-border p-6">
        <h3 className="text-sm font-semibold text-text-primary border-b border-border pb-3 mb-6">Blocked merchants</h3>
        <div className="space-y-4">
          <div className="flex gap-3">
            <input type="text" value={newMerchant} onChange={(e) => setNewMerchant(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addMerchant()} placeholder="Enter merchant name" className="flex-1 bg-background border border-border px-3 py-2.5 text-sm focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none text-text-primary placeholder:text-text-muted transition-colors" />
            <button onClick={addMerchant} className="px-4 py-2.5 border border-border bg-background text-sm font-medium text-text-primary hover:bg-surface-hover transition-colors">Add</button>
          </div>
          {constraints.blocked_merchants.length > 0 ? (
            <div className="flex flex-wrap gap-2 pt-3 border-t border-border">
              {constraints.blocked_merchants.map((m) => (
                <span key={m} className="flex items-center gap-2 text-sm px-3 py-1.5 bg-danger-light text-danger font-medium">
                  {m}
                  <button onClick={() => removeMerchant(m)} className="opacity-60 hover:opacity-100 transition-opacity text-base leading-none">&times;</button>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted">No blocked merchants</p>
          )}
        </div>
      </div>

      {/* Save constraints */}
      <div className="flex justify-end">
        <button onClick={handleSaveConstraints} disabled={saving} className="w-full lg:w-auto px-6 py-2.5 bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-all disabled:opacity-50">
          {saving ? "Saving..." : "Save changes"}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
        {/* Balance */}
        <div className="bg-surface border border-border p-6">
          <h3 className="text-sm font-semibold text-text-primary border-b border-border pb-3 mb-6">Set balance</h3>
          <div className="space-y-4">
            <p className="text-sm text-text-secondary">Current balance: <span className="font-semibold text-text-primary tabular-nums">${user.balance.toFixed(2)}</span></p>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">$</span>
                <input type="number" value={balanceInput} onChange={(e) => setBalanceInput(e.target.value)} placeholder="0.00" className="w-full bg-background border border-border pl-7 pr-3 py-2.5 text-sm tabular-nums focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none text-text-primary transition-colors" />
              </div>
              <button onClick={handleSetBalance} disabled={saving} className="px-4 py-2.5 bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors disabled:opacity-50">Update</button>
            </div>
          </div>
        </div>

        {/* Payment card */}
        <div className="bg-surface border border-border p-6">
          <h3 className="text-sm font-semibold text-text-primary border-b border-border pb-3 mb-6">Payment method</h3>
          <p className="text-sm text-text-muted mb-4">{user.stripe_payment_method_id ? "Card on file. Add a new one to replace it." : "No card on file."}</p>
          <StripeCardInput userId={user.id} onSuccess={onRefresh} />
        </div>
      </div>

      {/* Trust score reset */}
      <div className="bg-surface border border-border p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Trust score</h3>
            <p className="text-sm text-text-muted mt-1">Current score: {agent.trust_score}. Reset to 50 (Standard tier).</p>
          </div>
          <button onClick={handleResetScore} disabled={saving} className="px-4 py-2.5 border border-danger text-sm font-medium text-danger hover:bg-danger-light transition-colors disabled:opacity-50">Reset Trust Score</button>
        </div>
      </div>
    </div>
  );
}
