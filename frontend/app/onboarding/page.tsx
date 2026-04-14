"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useState } from "react";

const ALL_CATEGORIES = [
  "electronics", "groceries", "books", "clothing", "home", "office",
  "health", "beauty", "sports", "toys", "automotive", "garden",
  "pet supplies", "food & dining", "travel", "entertainment",
];

const API_URL = process.env.NEXT_PUBLIC_FLASK_API_URL || "http://localhost:5001";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Step 1: Identity
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");

  // Step 2: Preferences
  const [maxPerTransaction, setMaxPerTransaction] = useState(100);
  const [maxPerWeek, setMaxPerWeek] = useState(500);
  const [allowedCategories, setAllowedCategories] = useState<string[]>([...ALL_CATEGORIES]);
  const [blockedMerchants, setBlockedMerchants] = useState<string[]>([]);
  const [merchantInput, setMerchantInput] = useState("");

  // Step 3: Payment
  const [balance, setBalance] = useState(500);

  // Step 4: Terms
  const [accepted, setAccepted] = useState(false);

  function toggleCategory(cat: string) {
    setAllowedCategories((prev) =>
      prev.includes(cat) ? prev.filter((c) => c !== cat) : [...prev, cat]
    );
  }

  function addMerchant() {
    const trimmed = merchantInput.trim();
    if (trimmed && !blockedMerchants.includes(trimmed)) {
      setBlockedMerchants((prev) => [...prev, trimmed]);
      setMerchantInput("");
    }
  }

  function removeMerchant(m: string) {
    setBlockedMerchants((prev) => prev.filter((x) => x !== m));
  }

  async function handleSubmit() {
    setLoading(true);
    setError(null);

    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        setError("Session expired. Please sign in again.");
        setLoading(false);
        return;
      }

      const res = await fetch(`${API_URL}/api/auth/onboarding`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          name,
          phone,
          max_per_transaction: maxPerTransaction,
          max_per_week: maxPerWeek,
          allowed_categories: allowedCategories,
          blocked_merchants: blockedMerchants,
          balance,
          stripe_token: "tok_visa",
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: "Onboarding failed" }));
        throw new Error(data.error || "Onboarding failed");
      }

      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Onboarding failed");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <span className="text-base font-semibold tracking-tight text-text-primary">Squid</span>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-text-primary">
            Set up your account
          </h1>
          <p className="mt-2 text-sm text-text-muted">
            Step {step} of 4
          </p>
        </div>

        {/* Progress bar */}
        <div className="mb-8 flex gap-2">
          {[1, 2, 3, 4].map((s) => (
            <div
              key={s}
              className={`h-1 flex-1 transition-colors ${
                s <= step ? "bg-accent" : "bg-border"
              }`}
            />
          ))}
        </div>

        <div className="border border-border bg-surface p-6">
          {/* Step 1: Identity */}
          {step === 1 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Your identity</h2>
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-text-secondary mb-1.5">
                  Full name
                </label>
                <input
                  id="name"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent text-text-primary"
                />
              </div>
              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-text-secondary mb-1.5">
                  Phone number
                </label>
                <input
                  id="phone"
                  type="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+1 (555) 000-0000"
                  className="w-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent text-text-primary placeholder:text-text-muted"
                />
                <p className="mt-1 text-xs text-text-muted">
                  Used for iMessage communication with your agent
                </p>
              </div>
              <button
                onClick={() => setStep(2)}
                disabled={!name.trim() || !phone.trim()}
                className="w-full bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
              >
                Continue
              </button>
            </div>
          )}

          {/* Step 2: Preferences */}
          {step === 2 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Spending preferences</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="maxTx" className="block text-sm font-medium text-text-secondary mb-1.5">
                    Max per transaction ($)
                  </label>
                  <input
                    id="maxTx"
                    type="number"
                    min={1}
                    value={maxPerTransaction}
                    onChange={(e) => setMaxPerTransaction(Number(e.target.value))}
                    className="w-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent text-text-primary tabular-nums"
                  />
                </div>
                <div>
                  <label htmlFor="maxWeek" className="block text-sm font-medium text-text-secondary mb-1.5">
                    Max per week ($)
                  </label>
                  <input
                    id="maxWeek"
                    type="number"
                    min={1}
                    value={maxPerWeek}
                    onChange={(e) => setMaxPerWeek(Number(e.target.value))}
                    className="w-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent text-text-primary tabular-nums"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Allowed categories
                </label>
                <div className="flex flex-wrap gap-2">
                  {ALL_CATEGORIES.map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => toggleCategory(cat)}
                      className={`px-3 py-1 text-xs font-medium transition-colors border capitalize ${
                        allowedCategories.includes(cat)
                          ? "bg-accent-light border-accent/30 text-accent"
                          : "bg-background border-border text-text-muted hover:border-text-secondary hover:text-text-secondary"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Blocked merchants (optional)
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={merchantInput}
                    onChange={(e) => setMerchantInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addMerchant())}
                    placeholder="e.g. Wish.com"
                    className="flex-1 border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent text-text-primary placeholder:text-text-muted"
                  />
                  <button
                    type="button"
                    onClick={addMerchant}
                    className="border border-border px-3 py-2 text-sm font-medium hover:bg-surface-hover transition-colors text-text-primary"
                  >
                    Add
                  </button>
                </div>
                {blockedMerchants.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {blockedMerchants.map((m) => (
                      <span
                        key={m}
                        className="inline-flex items-center gap-1 bg-danger-light px-2.5 py-0.5 text-xs font-medium text-danger"
                      >
                        {m}
                        <button type="button" onClick={() => removeMerchant(m)} className="hover:text-danger/70">&times;</button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setStep(1)}
                  className="flex-1 border border-border px-4 py-2.5 text-sm font-semibold hover:bg-surface-hover transition-colors text-text-primary"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(3)}
                  className="flex-1 bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover transition-colors"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Payment */}
          {step === 3 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Payment setup</h2>
              <div>
                <label htmlFor="balance" className="block text-sm font-medium text-text-secondary mb-1.5">
                  Spending balance ($)
                </label>
                <input
                  id="balance"
                  type="number"
                  min={1}
                  value={balance}
                  onChange={(e) => setBalance(Number(e.target.value))}
                  className="w-full border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent text-text-primary tabular-nums"
                />
                <p className="mt-1 text-xs text-text-muted">
                  This is your self-imposed spending cap, not held funds
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-secondary mb-1.5">
                  Payment method
                </label>
                <div className="border border-border bg-background p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-text-primary">Test card</p>
                      <p className="text-xs text-text-muted">Visa ending in 4242</p>
                    </div>
                    <span className="bg-success-light px-2 py-0.5 text-xs font-medium text-success">
                      Default
                    </span>
                  </div>
                </div>
                <p className="mt-1 text-xs text-text-muted">
                  Using Stripe test card for development
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setStep(2)}
                  className="flex-1 border border-border px-4 py-2.5 text-sm font-semibold hover:bg-surface-hover transition-colors text-text-primary"
                >
                  Back
                </button>
                <button
                  onClick={() => setStep(4)}
                  className="flex-1 bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover transition-colors"
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Terms */}
          {step === 4 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Terms of service</h2>
              <div className="border border-border bg-background p-4 text-xs text-text-secondary leading-relaxed max-h-40 overflow-y-auto">
                <p className="mb-2">
                  By using Squid, you agree that your AI shopping agent will
                  operate within the constraints you configure. Squid manages
                  liability and risk on your behalf, but you are ultimately
                  responsible for purchases made through your account.
                </p>
                <p className="mb-2">
                  You may file disputes for unauthorized purchases, wrong items,
                  or fulfillment issues within 7 days of the transaction.
                </p>
                <p>
                  Squid uses Stripe for payment processing. Your card details
                  are tokenized and never stored on our servers.
                </p>
              </div>

              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={accepted}
                  onChange={(e) => setAccepted(e.target.checked)}
                  className="mt-0.5 h-4 w-4 border-border text-accent focus:ring-accent"
                />
                <span className="text-sm text-text-secondary">
                  I agree to the Terms of Service and understand the dispute policy
                </span>
              </label>

              {error && (
                <p className="text-sm text-danger">{error}</p>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => setStep(3)}
                  className="flex-1 border border-border px-4 py-2.5 text-sm font-semibold hover:bg-surface-hover transition-colors text-text-primary"
                >
                  Back
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!accepted || loading}
                  className="flex-1 bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
                >
                  {loading ? "Setting up..." : "Complete Setup"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
