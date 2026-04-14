import Link from "next/link";

export default function NavHeader() {
  return (
    <header className="h-14 w-full border-b border-border bg-surface flex items-center px-6">
      {/* Left: Logo */}
      <Link href="/" className="flex items-center gap-2.5">
        <div className="flex h-7 w-7 items-center justify-center rounded-none bg-accent text-white">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M13 10V3L4 14h7v7l9-11h-7z" fill="currentColor" strokeWidth={0} />
          </svg>
        </div>
        <span className="text-sm font-semibold text-text-primary">Squid</span>
      </Link>

      {/* Center: Nav links */}
      <nav className="flex-1 flex items-center justify-center gap-8">
        <Link
          href="/product"
          className="text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          Product
        </Link>
        <Link
          href="/policy"
          className="text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          Policy
        </Link>
        <Link
          href="/docs"
          className="text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          Docs
        </Link>
      </nav>

      {/* Right: Auth buttons */}
      <div className="flex items-center gap-3">
        <Link
          href="/login"
          className="text-sm text-text-secondary hover:text-text-primary transition-colors"
        >
          Sign In
        </Link>
        <Link
          href="/signup"
          className="rounded-none bg-accent px-4 py-1.5 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
        >
          Sign Up
        </Link>
      </div>
    </header>
  );
}
