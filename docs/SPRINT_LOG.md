# Sprint Log

## Sprint 5D — Guest to Google Transition

### Goal

Keep Guest fallback while making Google login continuously accessible and preserving
Guest portfolio work during account conversion.

### Completed

- Added the Google login action to the Guest sidebar whenever OAuth is configured.
- Added a friendly configuration notice when OAuth is unavailable.
- Migrated Guest assets, accounts, and preferences into the Google user repository before
  replacing the Guest session with the Google session.
- Cleared migrated Guest assets only after the Google copy completed successfully.
- Added regression coverage for callback activation and Guest-to-Google migration.

### Known Issues

- Portfolio migration spans two SQLite files and therefore cannot be one cross-database
  transaction; the source is cleared only after the destination writes succeed.

### Next Sprint

- Verify the conversion flow with a deployed Google callback and a real Guest portfolio.

## Sprint 5D — Google Login Activation

### Goal

Activate production Google authentication with deterministic user identity and complete
file-level separation between Google, Guest, and Developer data.

### Completed

- Read Google credentials exclusively through Streamlit Secrets and retained the official
  Streamlit 1.60 `st.user` API for verified claims.
- Added normalized-email SHA-256 IDs and reusable user-specific SQLite directories.
- Routed portfolios, feedback, and error logs to separate databases for each identity.
- Added safe Guest fallback for missing OAuth configuration, invalid claims, login errors,
  cookie/auth errors surfaced by Streamlit, and logout.
- Kept User Context-based repository filtering inside each isolated portfolio database.
- Added hashing, storage-path, repeat-login, and cross-user isolation regression coverage.

### Modified Files

- Authentication/UI: `app.py`, `services/auth/google_auth.py`,
  `services/auth/local_user.py`, `services/auth/session.py`,
  `services/auth/user_service.py`.
- Storage: `repositories/__init__.py`, `services/user_storage_service.py`,
  `services/pilot_support_service.py`, `.gitignore`.
- Tests: `tests/unit/test_google_auth.py`, `tests/unit/test_pilot_support_service.py`,
  `tests/unit/test_user_storage_service.py`.
- Documentation: `README.md`, `docs/DEPLOYMENT.md`, `CHANGELOG.md`,
  `docs/SPRINT_LOG.md`.

### Known Issues

- Streamlit Cloud can replace the local filesystem, including all user SQLite files.
- Google redirect, cookie, and browser behavior require final testing on the deployed URL.
- Automated tests cannot substitute for the requested two-real-Google-account pilot check.

### Next Sprint

- Execute the two-account Chrome/Edge pilot checklist on the production callback URL.
- Replace local SQLite files with a durable repository before broader rollout.

## Sprint 5C — Deployment Ready

### Goal

Prepare AssetOS and its Google OAuth callback configuration for Streamlit Community
Cloud while retaining the SQLite pilot backend.

### Completed

- Added Authlib to clean-install dependencies so Streamlit native OIDC can execute.
- Enabled headless server defaults and removed fixed localhost address and port settings.
- Added production-safe Streamlit Secrets and exact Google callback instructions.
- Documented build environment variables, deployment steps, post-deployment isolation
  checks, and the SQLite durability boundary.
- Added regression coverage confirming the named Google provider is passed to
  `st.login()`.

### Modified Files

- Runtime configuration: `requirements.txt`, `.streamlit/config.toml`,
  `.streamlit/secrets.toml.example`.
- Tests: `tests/unit/test_google_auth.py`.
- Documentation: `README.md`, `docs/DEPLOYMENT.md`, `CHANGELOG.md`,
  `docs/SPRINT_LOG.md`.

### Known Issues

- Native Streamlit OIDC requires nested `[auth]` values in Streamlit Secrets; raw
  environment variables cannot represent this configuration directly.
- SQLite, feedback, and logs are not durable across Community Cloud instance replacement.
- Final OAuth callback testing requires the real app slug and deployment-owner secrets.

### Next Sprint

- Run the deployment checklist against the final Streamlit URL and Google test users.
- Move user data and operational records to durable managed storage before GA.

## Sprint 5B — Pilot Ready

### Goal

Prepare the existing Google-isolated SQLite application for a controlled pilot of up
to ten external users, focusing only on supportability and stability.

### Completed

- Added an About dialog showing Version, Build commit, and deployment Git Tag.
- Added user-scoped Bug, Suggestion, and Comment feedback stored in lightweight JSONL.
- Added a rotating local error log and a safe user-facing fallback for unexpected page
  exceptions.
- Retained Google, Guest, and Developer authentication paths and repository isolation.
- Completed the full portfolio and pilot-support regression gate.

### Modified Files

- Pilot UI: `app.py`.
- Support services: `services/pilot_support_service.py`.
- Tests: `tests/unit/test_pilot_support_service.py`.
- Local artifact exclusions and release records: `.gitignore`, `CHANGELOG.md`,
  `docs/SPRINT_LOG.md`.

### Known Issues

- Feedback, errors, and SQLite portfolios are local to one Streamlit Cloud instance and
  are not durable across instance replacement.
- Browser-specific Chrome, Edge, and responsive-device checks require the deployed pilot
  URL and cannot be fully automated in the local unit-test environment.

### Next Sprint

- Move portfolios, feedback, and operational logs to durable managed services.
- Add deployment-driven Chrome, Edge, mobile, and OAuth callback smoke tests.

## Sprint 5B — Pilot Release: Google Login + Multi User

### Goal

Allow pilot users to sign in through Google and access only their own SQLite-backed
portfolio while retaining Guest and Developer access.

### Completed

- Completed Streamlit OIDC login, verified-claim synchronization, session restoration,
  profile display, and logout flow.
- Stored Google identities as `google:<subject>` so first login creates an empty default
  account and returning login restores the same portfolio.
- Verified separate Google identities cannot read or mutate each other's assets.
- Retained stable Guest Mode and browser-local Developer Login.
- Documented local and Streamlit Community Cloud OAuth secrets configuration.

### Modified Files

- Authentication and UI: `app.py`, `services/auth/*`, `services/user_context.py`.
- Persistence: `repositories/asset_repository.py`,
  `repositories/sqlite_asset_repository.py`.
- Tests and documentation: `tests/unit/test_google_auth.py`, `CHANGELOG.md`,
  `docs/SPRINT_LOG.md`.

### Known Issues

- SQLite storage on Streamlit Community Cloud is instance-local and may be lost when the
  container is replaced or redeployed.
- Production Google Cloud credentials, consent-screen publication, authorized origin,
  and callback registration must be configured by the deployment owner.

### Next Sprint

- Move the repository implementation to durable managed storage before a wider release.
- Add browser-driven OAuth and deployment smoke tests against a non-production client.

## Sprint 5A-1 — User Context Foundation

### Goal

Prepare one authoritative user scope for future multi-user architecture without
changing SQLite, portfolio behavior, Smart Import, resolver, or pricing logic.

### Completed

- Expanded `current_user` with ID, name, email, photo, plan, guest state, and
  authentication state.
- Kept repository defaults connected to the single `get_current_user_id()` boundary.
- Added a stable session-scoped Guest User ID and preserved the offline Developer User.
- Confirmed legacy SQLite assets migrate automatically to `default_user` and its default
  account without data loss.
- Confirmed the login screen exposes Google, Guest, and Developer entry points; Guest
  and Developer modes are operational without OAuth configuration.
- Added regression coverage for context activation and stable guest identity.

### Modified Files

- User context and authentication: `services/user_context.py`, `services/auth/session.py`,
  `services/auth/user_service.py`, `services/auth/local_user.py`, `services/auth_service.py`.
- Tests and documentation: `tests/unit/test_google_auth.py`, `CHANGELOG.md`,
  `docs/SPRINT_LOG.md`.

### Known Issues

- Guest identity persists for the Streamlit browser session, not across cleared browser
  storage or a replaced Streamlit Cloud instance.
- Google OAuth deployment credentials and cloud data synchronization remain out of scope.

### Next Sprint

- Add an explicit migration flow from guest/developer identities to authenticated users.
- Add durable cloud persistence only after choosing a provider and migration policy.

## Sprint 5A — User Context + Authentication Foundation

### Goal

Prepare AssetOS for multi-user operation while preserving SQLite and all existing
portfolio behavior.

### Completed

- Added one request-scoped `current_user` containing ID, name, email, and plan.
- Connected repository defaults to the shared user context with backward-compatible
  optional `user_id` parameters.
- Added Google OAuth, session-persistent Guest Mode, and offline Developer Login.
- Added authenticated sidebar profile and logout behavior.

### Known Issues

- SQLite data is local to the running AssetOS instance.
- Existing local portfolios are not automatically linked to a Google identity.
- Firestore and cloud synchronization are not enabled.

### Next Sprint

- Design an explicit, user-confirmed local-to-Google portfolio linking flow.
- Add deployment-level authentication and user-isolation integration tests.

## Sprint 5A — Final Quality Gate

### Goal

Verify authentication, repository isolation, portfolio integrity, exports, resolver,
pricing, calculations, performance, and deployability before release.

### Completed

- Passed 115 unit tests covering Portfolio, Smart Import, Resolver, pricing, exports,
  AI Advisor, authentication session behavior, Guest Mode, logout, and user isolation.
- Verified account assets bypass ticker resolution and common US, KRX, and crypto
  assets resolve through the shared resolver.
- Verified invalid prices are refreshed and USD-to-KRW value, profit, and return
  calculations remain consistent.
- Cleared repository-wide Ruff and Pylance/Pyright diagnostics and compiled every
  Python module successfully.
- Confirmed Streamlit boot, health endpoint, startup latency, and process memory.

### Modified Files

- Authentication/context: `app.py`, `services/auth/*`, `services/user_context.py`,
  `services/auth_service.py`, `services/local_user_service.py`.
- Repository/data boundaries: `repositories/*`, `database/db.py`, `models/*`.
- Type-safe UI boundaries: `components/*`, `pages/*`, `ui/*`.
- Type-safe service boundaries: affected files under `services/*`; portfolio formulas
  and resolver matching rules were not changed.
- Regression coverage: affected files under `tests/unit/*` and import-related manual
  tests.
- Documentation: `CHANGELOG.md`, `docs/SPRINT_LOG.md`.

### Known Issues

- Google OAuth requires deployment-specific client credentials and redirect URI.
- SQLite remains instance-local and is not durable across Streamlit Community Cloud
  container replacement.
- Existing local portfolios require an explicit future linking flow before moving to
  a Google identity.
- Firestore and cloud synchronization remain intentionally disabled.

### Next Sprint

- Add browser-driven OAuth callback and sidebar interaction tests in a deployment
  test environment with non-production Google credentials.
- Design explicit local-to-Google portfolio linking with user confirmation and an
  auditable rollback path.
