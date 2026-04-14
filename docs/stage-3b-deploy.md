# Stage 3b: Deployment

**Goal:** Deploy Flask + Next.js to Render. Fix production config (debug mode, CORS, gunicorn). Error handling on all endpoints.

Created ONLY after user approves Auth gate (3a).

---

## Task Dependency Graph

```
STAGE 3b: DEPLOYMENT
  Task 0l: skill-discovery-deploy         owner: builder-deploy
  Task 31: build-deploy-config            owner: builder-deploy            blocked_by: [0l]
  Task 32: validate-deploy-config         owner: validator-deploy          blocked_by: [31]

  Task 33: build-error-handling           owner: lead                      blocked_by: [32]
  Task 34: production-integration         owner: lead                      blocked_by: [33]
  Task 35: deploy                         owner: lead                      blocked_by: [34]

  --- GATE: Lead presents deployed app, evaluates 3b gate criteria, asks user to approve release ---
```

---

## builder-deploy — Spawn Prompt

> **NOTE:** Expand through teammate-maker before spawning.

```
## Role
You are the builder-deploy teammate. Your ONE job: create the Render deployment
configuration for Flask and Next.js.

## Spec
Read `CLAUDE.md`:
- "Deployment (Stage 3b)" — Render services, configuration, health checks
- "Environment Variables" — all env vars needed

## Scope
- render.yaml

## MCP Servers
- render: for creating services, setting env vars, checking deploy status
- context7: for Render docs

## What to Build

1. **render.yaml** — Render Blueprint:
   - Flask web service:
     - runtime: python
     - buildCommand: pip install -r api/requirements.txt
     - startCommand: gunicorn api.app:app --bind 0.0.0.0:$PORT
     - healthCheckPath: /health
     - envVars: all API keys with sync: false, FLASK_DEBUG=False,
       ALLOWED_ORIGINS (set to frontend URL after deploy)
   - Next.js web service:
     - runtime: node
     - buildCommand: cd frontend && npm install && npm run build
     - startCommand: cd frontend && npm start
     - envVars: NEXT_PUBLIC_FLASK_API_URL (set to Flask URL after deploy),
       NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY, NEXT_PUBLIC_SUPABASE_URL,
       NEXT_PUBLIC_SUPABASE_ANON_KEY

## Constraints
- NEVER put secret values in render.yaml — use sync: false
- ALL services must bind to 0.0.0.0:$PORT
- Flask MUST use gunicorn, not the dev server
- Every web service MUST have healthCheckPath
```

---

## build-error-handling — Lead Task

After deploy config is validated:

1. Fix `api/app.py`:
   - `debug=os.environ.get("FLASK_DEBUG") == "True"` (not hardcoded True)
   - `CORS(app, origins=os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(","))`
2. Add consistent error handling on all Flask endpoints:
   - All errors return `{ "error": string, "code": string }`
   - Stripe failures: retry once, then return error
   - Rye failures: try alternative, then error
   - Supabase connection: 503 with retry hint
   - Add `@app.errorhandler(500)` global handler

## production-integration — Lead Task

1. Run full test suite
2. Verify auth flow works end-to-end
3. Verify all endpoints return consistent error format
4. Test edge cases: card decline, Rye failure, invalid JWT, expired session

## deploy — Lead Task

1. Use Render MCP to create services (or `render blueprint apply` with render.yaml)
2. Set environment variables via Render MCP `update_environment_variables`
3. Wait for deploys to complete
4. Verify health endpoints on deployed URLs
5. Run smoke tests against production
6. Set ALLOWED_ORIGINS on Flask to the deployed frontend URL
7. Set NEXT_PUBLIC_FLASK_API_URL on frontend to the deployed Flask URL
8. Evaluate 3b gate criteria
9. **Ask user: "Deployment gate criteria pass/fail. Approve release?"**
