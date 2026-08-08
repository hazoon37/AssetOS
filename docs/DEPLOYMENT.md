# AssetOS Streamlit Community Cloud Deployment

## 1. Prerequisites

- A Git repository accessible to Streamlit Community Cloud
- A Google Cloud project with an OAuth consent screen
- A Google OAuth 2.0 Web application client
- An AssetOS deployment URL such as `https://assetos-pilot.streamlit.app`

The repository contains no OAuth credential. Do not commit `.streamlit/secrets.toml`,
client secrets, cookie secrets, or API keys.

## 2. Streamlit deployment

1. Push the reviewed release commit and tag to the deployment branch.
2. In Streamlit Community Cloud, create an app from that repository.
3. Select `app.py` as the entrypoint.
4. Select Python from `runtime.txt`; dependencies are installed from
   `requirements.txt`, including the Authlib dependency required by `st.login()`.
5. Choose the final app slug before configuring Google OAuth.
6. Add the secrets below in **App settings → Secrets** and deploy.

`.streamlit/config.toml` enables headless mode and does not fix a localhost address or
port, so Community Cloud can supply its own server configuration.

## 3. Required secrets

Paste this TOML into Streamlit Community Cloud Secrets, replacing every placeholder:

```toml
DART_API_KEY = ""
KRX_ID = ""
KRX_PW = ""

[auth]
redirect_uri = "https://<app-slug>.streamlit.app/oauth2callback"
cookie_secret = "<random-secret-at-least-32-bytes>"

[auth.google]
client_id = "<google-oauth-client-id>"
client_secret = "<google-oauth-client-secret>"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Generate the cookie secret outside the repository, for example:

```bash
openssl rand -hex 32
```

Streamlit native OIDC reads the nested `[auth]` structure from Streamlit Secrets.
Raw process environment variables cannot replace this nested structure. Community
Cloud stores these values securely and exposes them only to the application runtime.

## 4. Google OAuth configuration

In Google Cloud Console:

1. Configure the OAuth consent screen and add the pilot users while the app is in
   testing status.
2. Create or edit an **OAuth client ID → Web application**.
3. Add this authorized JavaScript origin:

   `https://<app-slug>.streamlit.app`

4. Add this exact authorized redirect URI:

   `https://<app-slug>.streamlit.app/oauth2callback`

5. Copy the client ID and client secret only into Streamlit Community Cloud Secrets.

The Google redirect URI and `[auth].redirect_uri` must match exactly, including HTTPS,
hostname, path, and absence of a trailing slash.

## 5. Environment variables

Non-secret deployment metadata can use environment variables:

| Variable | Required | Purpose |
| --- | --- | --- |
| `ASSETOS_BUILD` | No | Build or commit identifier shown in About |
| `ASSETOS_GIT_TAG` | No | Release tag shown in About |
| `STREAMLIT_SERVER_HEADLESS` | No | Cloud normally supplies this; local override |
| `STREAMLIT_SERVER_PORT` | No | Platform-assigned server port override |

When build variables are absent, AssetOS reads the local Git commit and exact tag at
About-dialog time. Client ID, client secret, and cookie secret must remain in Streamlit
Secrets rather than environment variables or source code.

## 6. Post-deployment verification

1. Open the deployed URL in an incognito Chrome window.
2. Confirm Google login redirects to Google and returns to `/oauth2callback`.
3. Confirm the sidebar displays the expected name and email.
4. Add one test asset, log out, log in again, and confirm it is restored.
5. Sign in as a second pilot account and confirm the first account's asset is absent.
6. Verify Guest and Developer modes, Smart Import, export, resolver, and current prices.
7. Submit feedback and confirm no secrets or tokens appear in application logs.

## 7. SQLite pilot limitation

Each identity uses isolated files under `database/users/<user-id>/`: `portfolio.db`,
`feedback.db`, and `logs.db`. Google user IDs are SHA-256 hashes of normalized email
addresses. Guest and Developer identities use different directories.

SQLite remains instance-local. Streamlit Community Cloud may replace, restart, or move
the container, which can remove all of these files. This release is suitable only for a
controlled, recoverable pilot. Export or backup pilot data regularly, and move the
Repository implementation to durable storage before general availability.
