import type { AgentStep } from "./api";

/**
 * Translate an agent step into natural language.
 */
export function translateStep(step: AgentStep): string {
  const d = step.data || {};
  switch (step.step_type) {
    case "search":
      return d.query
        ? `Searched for '${d.query}'`
        : "Performed a search";
    case "compare": {
      const count = Array.isArray(d.products) ? d.products.length : null;
      return count
        ? `Compared ${count} products`
        : "Compared products";
    }
    case "select":
      return d.merchant && d.amount
        ? `Selected item from ${d.merchant} for $${Number(d.amount).toFixed(2)}`
        : d.product_description
        ? `Selected '${d.product_description}'`
        : "Selected a product";
    case "purchase":
      return d.amount
        ? `Completed purchase for $${Number(d.amount).toFixed(2)}`
        : "Completed purchase";
    case "constraint_check":
      return "Validated spending constraints";
    case "trust_check":
      return d.score && d.tier
        ? `Verified trust score: ${d.score} (${d.tier})`
        : "Verified trust score";
    default:
      return `Agent action: ${step.step_type}`;
  }
}

/**
 * Truncate a hex hash for display: first 8 chars...last 8 chars
 */
export function formatHash(hash: string): string {
  if (hash.length <= 20) return hash;
  return `${hash.slice(0, 8)}...${hash.slice(-8)}`;
}
