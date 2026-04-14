import NavHeader from "@/components/NavHeader";

export default function ProductPage() {
  return (
    <div className="min-h-screen bg-background">
      <NavHeader />
      <main className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-text-primary">Our Philosophy</h1>
        <p className="text-lg text-text-secondary mt-2">The Squid Manifesto</p>

        <p className="text-text-secondary leading-relaxed mb-4 mt-8">
          Online shopping already has an easy interface: you just say what you
          want. What has been missing is a safe way to let an AI actually do the
          work for you. That is why we built Squid.
        </p>
        <p className="text-text-secondary leading-relaxed mb-4">
          Squid is based on a simple idea: AI should be useful, but it should
          not be unaccountable.
        </p>

        <h2 className="text-2xl font-bold text-text-primary mt-12 mb-4">
          Our belief
        </h2>
        <p className="text-text-secondary leading-relaxed mb-4">
          People should be able to tell an agent what they want, let it research
          the best option, and let it complete the purchase — without giving up
          control, safety, or clarity.
        </p>
        <p className="text-text-secondary leading-relaxed mb-4">
          We do not believe AI should act like a mystery box. We do not believe
          &ldquo;the model decided&rdquo; is a good enough answer. We do not
          believe convenience should come at the cost of trust.
        </p>
        <p className="text-text-secondary leading-relaxed mb-4">
          We believe the future of AI commerce should feel:
        </p>
        <ul className="list-disc list-inside text-text-secondary space-y-1 mb-4">
          <li>Simple for users</li>
          <li>Clear about responsibility</li>
          <li>Safe by design</li>
          <li>Honest about limits</li>
        </ul>

        <h2 className="text-2xl font-bold text-text-primary mt-12 mb-4">
          What Squid stands for
        </h2>
        <div className="space-y-4">
          <div className="border border-border bg-surface p-6 rounded-none">
            <h3 className="text-xl font-semibold text-text-primary mb-3">
              1. Human-first control
            </h3>
            <p className="text-text-secondary leading-relaxed">
              The user stays in charge. The agent acts within limits set by the
              user and enforced by the platform.
            </p>
          </div>

          <div className="border border-border bg-surface p-6 rounded-none">
            <h3 className="text-xl font-semibold text-text-primary mb-3">
              2. Bounded autonomy
            </h3>
            <p className="text-text-secondary leading-relaxed">
              We want AI to be powerful enough to help, but not so unconstrained
              that it becomes reckless. Guardrails are part of the product, not
              an afterthought.
            </p>
          </div>

          <div className="border border-border bg-surface p-6 rounded-none">
            <h3 className="text-xl font-semibold text-text-primary mb-3">
              3. Clear responsibility
            </h3>
            <p className="text-text-secondary leading-relaxed">
              If an agent can spend money, there must be a clear system for who
              authorized it, what it was allowed to do, what happened, and what
              can be reviewed later.
            </p>
          </div>

          <div className="border border-border bg-surface p-6 rounded-none">
            <h3 className="text-xl font-semibold text-text-primary mb-3">
              4. Receipts, not magic
            </h3>
            <p className="text-text-secondary leading-relaxed">
              Every important action should leave a trail. When something goes
              right, users should be able to see what happened. When something
              goes wrong, there should be a record to review.
            </p>
          </div>

          <div className="border border-border bg-surface p-6 rounded-none">
            <h3 className="text-xl font-semibold text-text-primary mb-3">
              5. Safety before scale
            </h3>
            <p className="text-text-secondary leading-relaxed">
              We would rather start with limits, supported categories, and
              careful rollout than pretend every purchase on the internet is
              equally safe.
            </p>
          </div>
        </div>

        <h2 className="text-2xl font-bold text-text-primary mt-12 mb-4">
          Our promise
        </h2>
        <p className="text-text-secondary leading-relaxed mb-4">
          You tell the agent what you want. The agent finds the best path. The
          system checks the purchase against your rules. The purchase is
          completed only inside those rules. You can see what happened afterward.
        </p>
        <p className="text-text-secondary leading-relaxed mb-4">
          <strong className="text-text-primary font-semibold">
            AI that acts, but never without structure.
          </strong>
        </p>
      </main>
    </div>
  );
}
