"use client";

import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import Link from "next/link";

export default function SignUpPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSignUp(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const password = formData.get("password") as string;
    const confirmPassword = formData.get("confirmPassword") as string;

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      setLoading(false);
      return;
    }

    const supabase = createClient();
    const { data, error } = await supabase.auth.signUp({
      email: formData.get("email") as string,
      password,
    });

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    // Wait for session to be established before redirecting.
    // signUp may return a session directly (if email confirmation is disabled)
    // or require confirmation. If we have a session, proceed.
    if (data.session) {
      router.push("/onboarding");
      router.refresh();
    } else {
      // If email confirmation is enabled, signUp won't return a session.
      // Try signing in immediately with the same credentials.
      const email = formData.get("email") as string;
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      if (signInError) {
        // Email confirmation likely required — tell the user
        setError("Check your email to confirm your account, then sign in.");
        setLoading(false);
        return;
      }
      router.push("/onboarding");
      router.refresh();
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link href="/" className="text-base font-semibold tracking-tight">
            Squid
          </Link>
          <h1 className="mt-6 text-2xl font-bold tracking-tight">
            Create your account
          </h1>
        </div>

        <form onSubmit={handleSignUp} className="space-y-4">
          <div>
            <label
              htmlFor="email"
              className="block text-sm font-medium text-text-secondary mb-1.5"
            >
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              required
              autoComplete="email"
              className="w-full border border-border bg-backgroundpx-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent"
            />
          </div>
          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-text-secondary mb-1.5"
            >
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              required
              minLength={6}
              autoComplete="new-password"
              className="w-full border border-border bg-backgroundpx-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent"
            />
          </div>
          <div>
            <label
              htmlFor="confirmPassword"
              className="block text-sm font-medium text-text-secondary mb-1.5"
            >
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              required
              minLength={6}
              autoComplete="new-password"
              className="w-full border border-border bg-backgroundpx-3 py-2 text-sm outline-none focus:border-accent focus:ring-1 focus:ring-accent"
            />
          </div>

          {error && (
            <p className="text-sm text-danger">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {loading ? "Creating account..." : "Sign Up"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-text-muted">
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-accent hover:text-accent-hover"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
