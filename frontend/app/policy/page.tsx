"use client";

import { useState } from "react";
import NavHeader from "@/components/NavHeader";

const policies = [
  {
    id: "tos",
    title: "Terms of Service",
    summary:
      "This User Agreement governs your use of Squid's services including your account, agent, dashboard, messaging interface, and purchase flows. It covers your rights, responsibilities, dispute procedures, and the terms under which your AI agent operates.",
    sections: [
      {
        heading: "1. Related Documents",
        content:
          "This Agreement incorporates the Privacy Policy, the Acceptable Use Policy, any fee or balance disclosures, any risk or trust-tier terms presented during onboarding or in your dashboard, and any electronic communications consent we require.",
      },
      {
        heading: "2. Eligibility",
        content:
          "You may use the Services only if you are at least 18 years old, have capacity to enter into a binding contract, are authorized to use any payment method you connect, and your use does not violate any applicable law or our Acceptable Use Policy.",
      },
      {
        heading: "3. Nature of the Services",
        content:
          "Squid provides a human-authorized agentic purchasing service. You can configure spending limits, connect a payment method, fund a balance, instruct an agent to research and purchase on your behalf, and view receipts, logs, and account activity. Squid is not a bank, card issuer, money transmitter, insurance provider, or merchant of record.",
      },
      {
        heading: "4. Your Account",
        content:
          "You must provide accurate information and keep it updated. You are responsible for maintaining the confidentiality of your credentials, restricting access to your devices and messaging accounts, and all actions taken through your account. You must promptly notify us of any suspected unauthorized access.",
      },
      {
        heading: "5. Agent Authorization and Delegated Authority",
        content:
          "When you activate a Squid agent, you authorize us to operate it as a bounded execution system under your rules. Your agent may research products, compare merchants, select products, fill carts, and complete purchases — all limited by this Agreement, your configured constraints, your balance, your trust tier, and our validation systems. A transaction is considered authorized if it is initiated within the scope of authority and limits applicable to your account. You may revoke or narrow your agent's authority at any time.",
      },
      {
        heading: "6. Spending Limits, Balance, and Funding",
        content:
          "Your Squid balance is a platform control and accounting value, not a deposit or stored-value account. You may connect a payment method and represent that you are authorized to use it. If your account has insufficient balance or fails validation, we may deny the transaction. Squid does not extend consumer credit unless expressly offered in writing.",
      },
      {
        heading: "7. Trust Tier and Risk Controls",
        content:
          "Squid assigns your agent a trust score informed by successful transactions, policy compliance, disputes, blocked attempts, suspicious patterns, and other signals. Depending on your tier, we may reduce limits, require confirmation, restrict categories, delay transactions, suspend autonomy, or freeze the account. You have no property interest in any trust tier or score.",
      },
      {
        heading: "8. Purchase Flow and Execution",
        content:
          "Your agent submits purchase requests through our validation layer. We may validate before, during, and after execution — checking categories, merchants, budget, trust tier, payment status, security signals, pricing changes, and cart mutations. We rely on third-party providers for payment tokenization, checkout automation, and transaction execution. Squid does not guarantee that any product, price, or checkout path will remain available.",
      },
      {
        heading: "9. Receipts, Logs, and Records",
        content:
          "Squid creates and retains records including purchase intent data, agent action logs, merchant details, validation outcomes, order identifiers, balance changes, trust-tier changes, dispute records, and evidence such as hashes or snapshots. These records are used to operate the Services, validate activity, investigate disputes, enforce this Agreement, and comply with law.",
      },
      {
        heading: "10. Errors, Disputes, and Resolution",
        content:
          "If you believe a transaction was unauthorized, incorrect, or problematic, notify us promptly. We may review using logs, receipts, provider responses, and evidence you provide. Outcomes may include determining the transaction was valid, issuing a goodwill credit, requiring merchant-side resolution, adjusting your trust tier, or blocking future related activity. Protection may be denied if you violated this Agreement, failed to secure your account, or delayed reporting.",
      },
      {
        heading: "11. Limitation of Liability",
        content:
          "Squid will not be liable for indirect, incidental, consequential, special, or punitive damages, or for losses caused by third-party merchants, payment processors, internet failures, or events beyond our control. Our total liability will not exceed the greater of fees you paid us in the prior 12 months or US$100. The Services are provided \"as is\" and \"as available\" without warranties of any kind.",
      },
      {
        heading: "12. Termination",
        content:
          "We may suspend or terminate your account at any time if we suspect fraud, detect a security concern, a third-party provider requires it, you fail verification, or your activity creates risk. You may stop using the Services at any time. Sections on payments, records, disputes, intellectual property, disclaimers, liability, and indemnification survive termination.",
      },
    ],
  },
  {
    id: "privacy",
    title: "Privacy Policy",
    summary:
      "This Privacy Policy explains how Squid collects, uses, stores, shares, and protects your information. We use tokenized payment flows through Stripe — raw card details are never stored on our servers.",
    sections: [
      {
        heading: "1. Information We Collect",
        content:
          "Account information (name, email, contact details), agent settings (spending limits, categories, blocked merchants), transaction data (merchant, amount, status, timestamps), prompt and activity logs, tokenized payment references, and technical information (device, browser, IP).",
      },
      {
        heading: "2. How We Use Information",
        content:
          "To operate your account and agent, validate and log transactions, connect with payment and checkout providers, generate receipts and dashboard views, investigate disputes and security issues, and comply with legal obligations.",
      },
      {
        heading: "3. How We Share Information",
        content:
          "With service providers (payment processors, hosting, messaging), merchants when needed to complete purchases, professional advisors, and authorities if required by law. We do not sell your personal information.",
      },
      {
        heading: "4. Payment Data",
        content:
          "Squid uses Stripe's tokenization model. Sensitive card details are collected securely by Stripe and replaced with tokens. We store only processor IDs and payment method references needed to operate the service.",
      },
      {
        heading: "5. Security",
        content:
          "We use administrative, technical, and organizational measures to protect your information. No method is perfectly secure, and we cannot guarantee absolute security.",
      },
      {
        heading: "6. Your Choices",
        content:
          "You may update account information, modify agent settings, revoke agent authority, remove payment methods, and contact us about disputes or incorrect information.",
      },
    ],
  },
  {
    id: "aup",
    title: "Acceptable Use Policy",
    summary:
      "This policy defines what you can and cannot do with Squid. You may only use Squid for lawful, authorized, human-directed purchases within your configured settings and spending limits.",
    sections: [
      {
        heading: "1. General Rule",
        content:
          "You may use Squid only for lawful, authorized, and policy-compliant purposes. You are responsible for complying with all applicable laws in connection with your use of Squid and any purchases initiated through the service.",
      },
      {
        heading: "2. Allowed Use",
        content:
          "Squid is designed for human-authorized agentic purchases made within your account settings, spending limits, category permissions, and other controls. Your agent may only act within the authority you grant.",
      },
      {
        heading: "3. Prohibited Uses",
        content:
          "You may not: violate any law or regulation, submit false purchase instructions, purchase illegal or restricted goods, use stolen payment credentials, evade restrictions or security checks, use Squid for fraud or abuse, interfere with validation or security controls, or create multiple accounts to circumvent limits.",
      },
      {
        heading: "4. Restricted Categories",
        content:
          "Squid may restrict the platform to limited categories and may block any category, merchant, or transaction type. This includes regulated goods, financial products, subscriptions, peer-to-peer transfers, and high-risk merchants.",
      },
      {
        heading: "5. Enforcement",
        content:
          "If we believe you violated this policy, we may deny transactions, freeze your agent, lower your trust tier, block merchants or categories, suspend your account, or cooperate with law enforcement where appropriate.",
      },
    ],
  },
];

export default function PolicyPage() {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-background">
      <NavHeader />
      <main className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-text-primary">Policies</h1>
        <p className="text-lg text-text-secondary mt-2">
          Legal documents governing Squid
        </p>

        <nav className="flex gap-6 border-b border-border mt-8 pb-3">
          {policies.map((p) => (
            <a
              key={p.id}
              href={`#${p.id}`}
              className="text-text-secondary hover:text-text-primary transition-colors text-sm"
            >
              {p.title}
            </a>
          ))}
        </nav>

        {policies.map((policy) => (
          <section
            key={policy.id}
            id={policy.id}
            className="border border-border bg-surface p-8 mt-8"
          >
            <h2 className="text-2xl font-bold text-text-primary mb-4">
              {policy.title}
            </h2>
            <p className="text-text-secondary leading-relaxed mb-4">
              {policy.summary}
            </p>
            <button
              onClick={() =>
                setExpanded(expanded === policy.id ? null : policy.id)
              }
              className="text-accent hover:text-accent-hover transition-colors font-medium text-sm"
            >
              {expanded === policy.id
                ? "Collapse \u2191"
                : "Read full document \u2192"}
            </button>
            {expanded === policy.id && (
              <div className="mt-6 space-y-6 border-t border-border pt-6">
                {policy.sections.map((s) => (
                  <div key={s.heading}>
                    <h3 className="text-sm font-semibold text-text-primary mb-2">
                      {s.heading}
                    </h3>
                    <p className="text-sm text-text-secondary leading-relaxed">
                      {s.content}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>
        ))}
      </main>
    </div>
  );
}
