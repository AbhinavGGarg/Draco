# Stage 3a: Auth & Onboarding

**Goal:** Identity system. Landing page, sign up/sign in, onboarding questionnaire, JWT-protected API, session management. Identity before deployment — money must be tied to identity.

Created ONLY after user approves MVP 2b gate.

---

## Task Dependency Graph

```
STAGE 3a: AUTH & ONBOARDING
  Task 0j: skill-discovery-auth-backend    owner: builder-auth-backend
  Task 25: build-auth-backend              owner: builder-auth-backend       blocked_by: [0j]
  Task 26: validate-auth-backend           owner: validator-auth-backend     blocked_by: [25]

  Task 0k: skill-discovery-auth-frontend   owner: builder-auth-frontend
  Task 27: build-auth-frontend             owner: builder-auth-frontend      blocked_by: [0k, 26]
  Task 28: validate-auth-frontend          owner: validator-auth-frontend    blocked_by: [27]

  Task 29: auth-integration                owner: lead                       blocked_by: [28]
  Task 30: auth-demo                       owner: lead                       blocked_by: [29]

  --- GATE: Lead presents auth flow, evaluates 3a gate criteria, asks user "Proceed to Stage 3b?" ---
```

**Why backend before frontend:** The frontend auth pages need to call Flask endpoints (`GET /api/auth/me`, `POST /api/auth/onboarding`). The `@require_auth` middleware must exist before the frontend can test against it.

---

## builder-auth-backend — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-auth-backend teammate. Your ONE job: add Supabase Auth
JWT validation and auth-related endpoints to the Flask API.

## Spec
Read `CLAUDE.md`:
- "Auth & Onboarding (Stage 3a)" — full flow, edge cases, Supabase Auth details, API changes
- "Database Schema" — note the `supabase_auth_id` column on users table

## Scope
- api/src/middleware/__init__.py
- api/src/middleware/auth.py
- api/src/routes/auth.py
- api/tests/test_auth.py

Do NOT modify existing route files. The lead will add @require_auth to them during integration.

## MCP Servers
- supabase: for auth docs lookup, schema changes
- context7: for PyJWT / Supabase JWT verification docs

## What to Build

1. **api/src/middleware/auth.py**:
   - `verify_jwt(token: str) -> dict` — decodes Supabase JWT using the project's JWT secret
     (from `SUPABASE_JWT_SECRET` env var). Returns decoded payload with `sub` (user ID).
   - `@require_auth` decorator — extracts Bearer token from Authorization header,
     calls verify_jwt, looks up OpenPay user by `supabase_auth_id`, injects `user_id`
     into Flask's `g` object. Returns 401 if no token, invalid token, or expired.

2. **api/src/routes/auth.py** (blueprint: auth_bp, prefix='/api/auth'):
   - `GET /api/auth/me` — uses `g.user_id` from @require_auth. Returns OpenPay user
     profile or 404 if no user row exists (onboarding not complete).
   - `POST /api/auth/onboarding` — accepts `{ name, phone, max_per_transaction,
     max_per_week, allowed_categories, blocked_merchants, balance, stripe_token }`.
     Creates user row (with `supabase_auth_id` from JWT), creates agent row,
     attaches Stripe card if token provided. Returns `{ user_id, agent_id }`.

3. **Database migration** — add `supabase_auth_id UUID UNIQUE` column to users table
   via Supabase MCP.

4. **test_auth.py** (write FIRST):
   - Valid JWT → user_id injected into request context
   - Invalid JWT → 401
   - Expired JWT → 401
   - No Authorization header → 401
   - GET /api/auth/me with valid user → returns profile
   - GET /api/auth/me with no OpenPay profile → 404
   - POST /api/auth/onboarding → creates user + agent

## Self-Validation
1. py_compile all files
2. pytest api/tests/test_auth.py -v — ALL pass

## Constraints
- Use PyJWT to decode (not Supabase client — Flask doesn't need Supabase Auth SDK)
- JWT secret from env var `SUPABASE_JWT_SECRET`
- Do NOT modify existing routes — lead handles adding @require_auth during integration
- Do NOT touch frontend files
```

---

## builder-auth-frontend — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-auth-frontend teammate. Your ONE job: build the landing page,
auth pages (login/signup), onboarding questionnaire, and session management for
the Next.js frontend.

## Spec
Read `CLAUDE.md`:
- "Auth & Onboarding (Stage 3a)" — full user flow, edge cases
- "Frontend Pages" — landing, auth, onboarding, dashboard sections

## Scope
- frontend/middleware.ts
- frontend/lib/supabase.ts
- frontend/app/page.tsx (replace with landing page)
- frontend/app/login/page.tsx (new)
- frontend/app/signup/page.tsx (new)
- frontend/app/onboarding/page.tsx (new)
- frontend/app/dashboard/page.tsx (move existing 4-tab app here)

Do NOT modify components/ (OverviewTab, TransactionsTab, etc.) — they stay as-is,
just rendered inside /dashboard instead of /.

## MCP Servers
- supabase: for auth docs
- context7: for Next.js, @supabase/ssr docs
- playwright: for testing auth flows

## What to Build

1. **lib/supabase.ts** — Supabase client using `@supabase/ssr` (cookie-based sessions).
   Export `createClient()` for use in client and server components.

2. **middleware.ts** — Next.js middleware that runs on every request:
   - Check for valid Supabase session
   - No session + hitting /dashboard or /onboarding → redirect to /login
   - Valid session + hitting /login or /signup → redirect to /dashboard
   - Valid session + hitting /onboarding + already has profile → redirect to /dashboard
   - Valid session + hitting /dashboard + no profile → redirect to /onboarding

3. **app/page.tsx** — Landing page:
   - Hero: "OpenPay — Your AI shops, you stay in control"
   - Sign Up button → /signup
   - Sign In button → /login
   - Clean, minimal design

4. **app/login/page.tsx** — Sign in:
   - Email + password fields
   - Submit → `supabase.auth.signInWithPassword()`
   - Error display (invalid credentials)
   - Link: "Don't have an account? Sign up" → /signup

5. **app/signup/page.tsx** — Sign up:
   - Email + password + confirm password
   - Submit → `supabase.auth.signUp()`
   - Redirect to /onboarding on success
   - Link: "Already have an account? Sign in" → /login

6. **app/onboarding/page.tsx** — Multi-step questionnaire:
   - Step 1: Name, phone number
   - Step 2: Max per transaction, max per week, allowed categories (checkboxes), blocked merchants
   - Step 3: Balance amount, "Use test card" button (calls POST /api/users/:id/card with tok_visa)
   - Step 4: TOS checkbox, submit
   - Submit → POST /api/auth/onboarding with all data
   - Redirect to /dashboard

7. **app/dashboard/page.tsx** — Move the existing 4-tab app from app/page.tsx to here.
   Change the hardcoded user ID to use the session's user ID (from GET /api/auth/me).
   Add sign-out button → `supabase.auth.signOut()` → redirect to /

## Constraints
- Install `@supabase/ssr` (add to package.json)
- All Supabase Auth calls happen client-side (signUp, signIn, signOut)
- Session cookies managed by @supabase/ssr automatically
- Do NOT modify component files (OverviewTab, TransactionsTab, etc.)
- Use Tailwind for all styling — match existing dashboard aesthetic
```

---

## auth-integration — Lead Task

After both auth builders are validated:

1. Pull auth-backend code: register auth_bp in app.py
2. Add `@require_auth` to all existing endpoints (agents, transactions, webhooks, disputes, risk)
3. Change route patterns from `/api/users/<user_id>/...` to `/api/me/...` using `g.user_id`
4. Pull auth-frontend code
5. Install `@supabase/ssr`: `cd frontend && npm install @supabase/ssr`
6. Verify: sign up → onboarding → dashboard → sign out → sign in → dashboard
7. Run all backend tests (some may need updating for @require_auth)

## auth-demo — Lead Task

Present the auth flow to the user:
1. Walk through: landing → sign up → onboarding → dashboard
2. Show sign out → redirect to landing
3. Show sign in → straight to dashboard (skip onboarding)
4. Show expired session handling
5. Show /api/auth/me returns correct profile
6. Evaluate each 3a gate criterion
7. **Ask user: "Auth gate criteria pass/fail. Proceed to Stage 3b (Deployment)?"**
8. Wait for approval.
