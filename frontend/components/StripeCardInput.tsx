"use client";

import { useState } from "react";
import { loadStripe } from "@stripe/stripe-js";
import { Elements, CardElement, useStripe, useElements } from "@stripe/react-stripe-js";
import { setupCard } from "@/lib/api";

const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || ""
);

function CardForm({ userId, onSuccess }: { userId: string; onSuccess: () => void }) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setLoading(true);
    setError(null);

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) return;

    const { error: stripeError, token } = await stripe.createToken(cardElement);
    if (stripeError) {
      setError(stripeError.message || "Card error");
      setLoading(false);
      return;
    }

    try {
      await setupCard(userId, token!.id);
      setSuccess(true);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save card");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="rounded-lg border border-border bg-white p-4">
        <CardElement
          options={{
            style: {
              base: {
                fontSize: "15px",
                fontFamily: "DM Sans, system-ui, sans-serif",
                color: "#0f172a",
                "::placeholder": { color: "#94a3b8" },
              },
              invalid: { color: "#dc2626" },
            },
          }}
        />
      </div>
      {error && (
        <p className="text-sm text-danger">{error}</p>
      )}
      {success && (
        <p className="text-sm text-success">Card saved successfully.</p>
      )}
      <button
        type="submit"
        disabled={!stripe || loading}
        className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:opacity-50"
      >
        {loading ? "Saving..." : "Save Card"}
      </button>
    </form>
  );
}

export default function StripeCardInput({
  userId,
  onSuccess,
}: {
  userId: string;
  onSuccess: () => void;
}) {
  return (
    <Elements stripe={stripePromise}>
      <CardForm userId={userId} onSuccess={onSuccess} />
    </Elements>
  );
}
