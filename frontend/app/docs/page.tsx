import NavHeader from "@/components/NavHeader";

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-background">
      <NavHeader />
      <main className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-text-primary">Documentation</h1>
        <p className="text-lg text-text-secondary mt-2">
          Learn how Squid works
        </p>

        <div className="border border-border bg-surface p-8 mt-8 rounded-none">
          <h2 className="text-2xl font-bold text-text-primary mb-6">
            How Purchases Work
          </h2>
          <div className="space-y-6">
            <div className="flex gap-4">
              <span className="flex-shrink-0 w-8 h-8 border border-border bg-background flex items-center justify-center text-text-primary font-semibold text-sm rounded-none">
                1
              </span>
              <div>
                <h3 className="text-xl font-semibold text-text-primary mb-1">
                  Send a request
                </h3>
                <p className="text-text-secondary leading-relaxed">
                  Tell your agent what you want via iMessage.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <span className="flex-shrink-0 w-8 h-8 border border-border bg-background flex items-center justify-center text-text-primary font-semibold text-sm rounded-none">
                2
              </span>
              <div>
                <h3 className="text-xl font-semibold text-text-primary mb-1">
                  Agent researches
                </h3>
                <p className="text-text-secondary leading-relaxed">
                  Your agent finds the best product match.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <span className="flex-shrink-0 w-8 h-8 border border-border bg-background flex items-center justify-center text-text-primary font-semibold text-sm rounded-none">
                3
              </span>
              <div>
                <h3 className="text-xl font-semibold text-text-primary mb-1">
                  Automatic validation
                </h3>
                <p className="text-text-secondary leading-relaxed">
                  Squid checks the purchase against your spending limits,
                  allowed categories, blocked merchants, and trust tier.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <span className="flex-shrink-0 w-8 h-8 border border-border bg-background flex items-center justify-center text-text-primary font-semibold text-sm rounded-none">
                4
              </span>
              <div>
                <h3 className="text-xl font-semibold text-text-primary mb-1">
                  Secure checkout
                </h3>
                <p className="text-text-secondary leading-relaxed">
                  If approved, payment is processed through Stripe and the order
                  is placed.
                </p>
              </div>
            </div>

            <div className="flex gap-4">
              <span className="flex-shrink-0 w-8 h-8 border border-border bg-background flex items-center justify-center text-text-primary font-semibold text-sm rounded-none">
                5
              </span>
              <div>
                <h3 className="text-xl font-semibold text-text-primary mb-1">
                  Confirmation
                </h3>
                <p className="text-text-secondary leading-relaxed">
                  You receive a confirmation with full transaction details.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="border border-border bg-surface p-8 mt-8 rounded-none">
          <h2 className="text-2xl font-bold text-text-primary mb-6">
            Safety &amp; Controls
          </h2>
          <div className="space-y-5">
            <div className="border-b border-border pb-5">
              <p className="text-text-secondary leading-relaxed">
                <strong className="text-text-primary font-semibold">
                  Trust Tiers
                </strong>{" "}
                — Your agent earns trust over time. New agents start at Standard
                tier. Good purchases increase trust; issues decrease it. Four
                tiers: Frozen, Restricted, Standard, Trusted.
              </p>
            </div>

            <div className="border-b border-border pb-5">
              <p className="text-text-secondary leading-relaxed">
                <strong className="text-text-primary font-semibold">
                  Spending Limits
                </strong>{" "}
                — Set max per transaction and max per week. Your agent cannot
                exceed these limits.
              </p>
            </div>

            <div className="border-b border-border pb-5">
              <p className="text-text-secondary leading-relaxed">
                <strong className="text-text-primary font-semibold">
                  Category Controls
                </strong>{" "}
                — Choose which product categories your agent can shop from.
              </p>
            </div>

            <div className="border-b border-border pb-5">
              <p className="text-text-secondary leading-relaxed">
                <strong className="text-text-primary font-semibold">
                  Merchant Blocking
                </strong>{" "}
                — Block specific merchants you don&apos;t want your agent to
                use.
              </p>
            </div>

            <div className="border-b border-border pb-5">
              <p className="text-text-secondary leading-relaxed">
                <strong className="text-text-primary font-semibold">
                  Dispute Protection
                </strong>{" "}
                — File disputes for unauthorized purchases, wrong items, or
                fulfillment issues within 7 days.
              </p>
            </div>

            <div>
              <p className="text-text-secondary leading-relaxed">
                <strong className="text-text-primary font-semibold">
                  Evidence Trail
                </strong>{" "}
                — Every transaction records what was requested, what was
                checked, and what happened — viewable in your dashboard.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
