const API_URL = process.env.NEXT_PUBLIC_FLASK_API_URL || "http://localhost:5001";

// --- Types ---

export interface User {
  id: string;
  name: string;
  email: string;
  stripe_customer_id?: string;
  stripe_payment_method_id?: string;
  balance: number;
  created_at: string;
}

export interface Constraints {
  max_per_transaction: number;
  max_per_week: number;
  allowed_categories: string[];
  blocked_merchants: string[];
}

export interface Agent {
  id: string;
  user_id: string;
  openclaw_agent_id?: string;
  trust_score: number;
  tier: string;
  constraints: Constraints;
  created_at: string;
}

export interface Transaction {
  id: string;
  agent_id: string;
  user_id: string;
  amount: number;
  merchant: string;
  product_url?: string;
  product_description?: string;
  category: string;
  status: "pending" | "completed" | "failed" | "returned" | "disputed" | "flagged";
  evidence?: EvidenceBundle;
  dispute_type?: "unauthorized" | "wrong_item" | "fulfillment_issue" | null;
  dispute_at?: string | null;
  rye_order_id?: string;
  stripe_payment_intent_id?: string;
  solana_tx_signature?: string | null;
  session_id?: string | null;
  created_at: string;
}

export interface GeminiReview {
  verdict: "MATCH" | "MISMATCH" | "ERROR";
  reasoning: string;
  confidence?: number;
  flagged_issues?: string[];
}

export interface EvidenceBundle {
  intent_snapshot: {
    product_url: string;
    amount: number;
    merchant: string;
    category: string;
    product_description: string;
  };
  account_state_at_purchase: {
    balance: number;
    trust_score: number;
    tier: string;
    risk_status: string;
  };
  policy_checks: Array<{
    check: string;
    result: string;
    detail?: string;
  }>;
  execution_result?: {
    rye_order_id: string;
    final_amount: number;
    final_merchant: string;
    amount_match: boolean;
    merchant_match: boolean;
    flagged: boolean;
  };
  gemini_review?: GeminiReview;
  authorization?: {
    original_message: string;
    authorized_at: string;
  };
  timestamps?: Record<string, string>;
}

export interface RiskMetrics {
  dispute_rate: number;
  flagged_rate: number;
  unauthorized_rate: number;
  wrong_item_rate: number;
  status: "normal" | "elevated" | "restricted" | "frozen";
  total_completed_30d: number;
  total_disputes_30d: number;
  total_flagged_30d: number;
}

export interface AgentStep {
  id: string;
  session_id: string;
  step_type: string;
  data: Record<string, unknown>;
  created_at: string;
}

// --- Helpers ---

export function scoreToTier(score: number): string {
  if (score <= 25) return "frozen";
  if (score <= 50) return "restricted";
  if (score <= 75) return "standard";
  return "trusted";
}

async function getAuthToken(): Promise<string | null> {
  try {
    const { createBrowserClient } = await import("@supabase/ssr");
    const supabase = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token ?? null;
  } catch {
    return null;
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = await getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options?.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(API_URL + path, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

// --- Auth ---

export interface MeResponse extends User {
  agent?: Agent;
}

export async function getMe(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/auth/me");
}

export async function onboard(data: {
  name: string;
  phone: string;
  max_per_transaction: number;
  max_per_week: number;
  allowed_categories: string[];
  blocked_merchants: string[];
  balance: number;
  stripe_token?: string;
}): Promise<{ user_id: string; agent_id: string }> {
  return apiFetch("/api/auth/onboarding", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// --- User ---

export async function getUser(userId: string): Promise<User> {
  return apiFetch<User>("/api/users/" + userId);
}

export async function createUser(name: string, email: string): Promise<User> {
  return apiFetch<User>("/api/users", {
    method: "POST",
    body: JSON.stringify({ name, email }),
  });
}

// --- Agent ---

export async function getAgent(userId: string): Promise<Agent> {
  return apiFetch<Agent>("/api/users/" + userId + "/agent");
}

export interface EffectiveLimits {
  effective_max_per_transaction: number;
  effective_max_per_week: number;
  tier: string;
  overrides: string[];
}

export async function getEffectiveLimits(userId: string): Promise<EffectiveLimits> {
  return apiFetch<EffectiveLimits>("/api/users/" + userId + "/agent/effective-limits");
}

export interface TrustAnalysis {
  score: number;
  base_score?: number;
  tier: string;
  reasoning: string;
  factors: {
    purchase_reliability: number;
    spending_behavior: number;
    dispute_history: number;
    category_diversity: number;
    account_maturity: number;
  };
  computed_at: string;
}

export async function computeTrustScore(userId: string): Promise<TrustAnalysis> {
  return apiFetch<TrustAnalysis>("/api/users/" + userId + "/agent/trust-analysis", {
    method: "POST",
  });
}

export async function getTrustAnalysis(userId: string): Promise<TrustAnalysis> {
  return apiFetch<TrustAnalysis>("/api/users/" + userId + "/agent/trust-analysis");
}

export interface TrustHistoryPoint {
  score: number;
  tier: string;
  factors: Record<string, number>;
  computed_at: string;
}

export async function getTrustHistory(userId: string): Promise<TrustHistoryPoint[]> {
  return apiFetch<TrustHistoryPoint[]>("/api/users/" + userId + "/agent/trust-history");
}

export async function updateConstraints(
  userId: string,
  constraints: Partial<Constraints>
): Promise<{ constraints: Constraints }> {
  return apiFetch("/api/users/" + userId + "/agent/constraints", {
    method: "PUT",
    body: JSON.stringify(constraints),
  });
}

export async function resetScore(
  userId: string
): Promise<{ trust_score: number; tier: string }> {
  return apiFetch("/api/users/" + userId + "/agent/reset-score", {
    method: "POST",
  });
}

// --- Transactions ---

export async function getTransactions(
  userId: string,
  status?: string
): Promise<Transaction[]> {
  const query = status ? "?status=" + status : "";
  return apiFetch<Transaction[]>("/api/users/" + userId + "/transactions" + query);
}

export async function markTransaction(
  transactionId: string,
  mark: "good" | "wrong_item"
): Promise<{ transaction_id: string; trust_score: number; old_tier: string; new_tier: string }> {
  return apiFetch("/api/transactions/" + transactionId + "/mark", {
    method: "PUT",
    body: JSON.stringify({ mark }),
  });
}

export async function disputeTransaction(
  transactionId: string,
  type: "unauthorized" | "wrong_item" | "fulfillment_issue"
): Promise<{
  transaction_id: string;
  dispute_type: string;
  eligible: boolean;
  trust_score: number;
  old_tier: string;
  new_tier: string;
  balance_credited?: number;
}> {
  return apiFetch("/api/transactions/" + transactionId + "/dispute", {
    method: "PUT",
    body: JSON.stringify({ type }),
  });
}

// --- Balance & Card ---

export async function setBalance(
  userId: string,
  amount: number
): Promise<{ balance: number }> {
  return apiFetch("/api/users/" + userId + "/balance", {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
}

export async function setupCard(
  userId: string,
  stripeToken: string
): Promise<{ stripe_customer_id: string; stripe_payment_method_id: string }> {
  return apiFetch("/api/users/" + userId + "/card", {
    method: "POST",
    body: JSON.stringify({ stripe_token: stripeToken }),
  });
}

// --- Agent Steps ---

export async function getAgentSteps(sessionId: string): Promise<AgentStep[]> {
  return apiFetch<AgentStep[]>(`/api/sessions/${sessionId}/steps`);
}

// --- Risk ---

export async function getRiskMetrics(userId: string): Promise<RiskMetrics> {
  return apiFetch<RiskMetrics>("/api/users/" + userId + "/risk");
}

// --- Solana ---

export interface SolanaTxInfo {
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

export async function getLiveSteps(agentId: string, limit = 20): Promise<AgentStep[]> {
  return apiFetch<AgentStep[]>(`/api/agents/${agentId}/live-steps?limit=${limit}`);
}

export async function getSolanaTx(signature: string): Promise<SolanaTxInfo> {
  return apiFetch<SolanaTxInfo>(`/api/solana/tx/${signature}`);
}
