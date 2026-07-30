# Evolve Business Suite — Windows Server Installation Guide

This guide deploys the app on a single Windows Server host:

- **PostgreSQL** — the database
- **Python + waitress**, running as a native **Windows Service** — the Flask API, bound to `127.0.0.1:5000` only (never exposed directly to the network)
- **IIS** — serves the built React frontend as static files, and reverse-proxies `/api/*` to the backend service, so the browser only ever talks to one origin (no CORS configuration needed in production)

```
Browser  --https-->  IIS (frontend/dist + reverse proxy)  --http, loopback-->  waitress (Windows Service)  -->  PostgreSQL
```

Tested against Windows Server 2019/2022. Steps are the same on both.

## Prerequisites

Install these first, in order:

1. **PostgreSQL 16** for Windows — [postgresql.org/download/windows](https://www.postgresql.org/download/windows/) (the EDB installer). During setup, note the `postgres` superuser password you set — you'll need it once, to create the app's database and role.
2. **Python 3.11+** for Windows — [python.org/downloads/windows](https://www.python.org/downloads/windows/). On the installer's first screen, check **"Add python.exe to PATH"**.
3. **IIS** — enable via *Server Manager → Add Roles and Features → Web Server (IIS)*. Include the default **Static Content**, **Default Document**, and **HTTP Errors** role services (they're checked by default).
4. **IIS URL Rewrite module** — a separate Microsoft download, not part of the IIS role: search "IIS URL Rewrite" on microsoft.com/iis.net and install the x64 MSI.
5. **IIS Application Request Routing (ARR)** — same source, search "IIS Application Request Routing"; install the x64 MSI. ARR is what actually performs the reverse-proxy HTTP call that URL Rewrite's rule describes.

Node.js is **not** required on the server — the frontend ships pre-built in this package (`frontend-dist/`). You'd only need Node.js if you plan to modify the frontend source and rebuild it yourself.

---

## 1. Unpack the application

Copy this package to the server and unzip it, e.g. to:

```
C:\Apps\EvolveBusinessSuite\
    backend\
    frontend-dist\
    deploy\windows\
```

Everything below assumes that path; adjust if you use a different one.

## 2. Create the database

Open **SQL Shell (psql)** (installed with PostgreSQL) or `psql` from a command prompt, connect as `postgres`, and run:

```sql
CREATE ROLE acctsys WITH LOGIN PASSWORD 'choose-a-strong-password-here';
CREATE DATABASE acctsys_prod OWNER acctsys;
```

Keep that password — it goes into `.env` in the next step.

## 3. Set up the Python virtual environment

Open **Command Prompt as Administrator**, then:

```bat
cd C:\Apps\EvolveBusinessSuite\backend
python -m venv venv
venv\Scripts\pip install --upgrade pip
venv\Scripts\pip install -r requirements.txt -r requirements-windows.txt
venv\Scripts\python venv\Scripts\pywin32_postinstall.py -install
```

That last command registers pywin32's DLLs with Windows — it's a one-time step required before `windows_service.py` will work, and is documented by pywin32 itself (not specific to this app).

## 4. Configure the environment

Copy `.env.example` to `.env` in the `backend\` folder and edit it:

```bat
copy .env.example .env
notepad .env
```

Set at minimum:

| Variable | Value |
|---|---|
| `SECRET_KEY` | A long random string — generate one with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_SECRET_KEY` | A *different* long random string, same method |
| `DATABASE_URL` | `postgresql+psycopg2://acctsys:choose-a-strong-password-here@localhost:5432/acctsys_prod` |
| `CORS_ORIGINS` | Your production URL, e.g. `https://suite.yourdomain.com` (defense-in-depth — the IIS reverse proxy setup below means the browser never makes a cross-origin request in the first place, but Flask-CORS is still worth locking down) |
| `SUPERADMIN_BOOTSTRAP_EMAIL` | The ETG super-admin's login email |
| `SUPERADMIN_BOOTSTRAP_PASSWORD` | A strong password — **rotate this after first login** |
| `APP_BASE_URL` | Your production URL, e.g. `https://suite.yourdomain.com` (used to build OAuth redirect URIs if you later configure Microsoft/Google integrations under Settings → Integrations) |
| `API_BASE_URL` | Same host, e.g. `https://suite.yourdomain.com` (the API is same-origin behind IIS, so this matches `APP_BASE_URL`) |

Leave `FLASK_ENV` out entirely, or set it to `production`.

Everything else in `.env.example` (S3, Microsoft/Google OAuth, Authorize.net) is optional — the app runs correctly with none of it configured; those integrations just report themselves as "not configured" in the UI (Settings → Integrations) until you fill them in.

## 5. Initialize the database

Still in the elevated Command Prompt, from `backend\`:

```bat
venv\Scripts\flask db upgrade
```

This runs all migrations and creates every table. Then bootstrap the first tenant and super-admin:

```bat
venv\Scripts\python seed.py
```

`seed.py` reads `SUPERADMIN_BOOTSTRAP_EMAIL`/`SUPERADMIN_BOOTSTRAP_PASSWORD` from `.env` to create the ETG super-admin account, and seeds a starter `demo` tenant you can delete later from the super-admin console once you've provisioned real client tenants.

## 6. Smoke-test the backend in the foreground

Before installing it as a service, confirm it actually starts:

```bat
venv\Scripts\python wsgi_windows.py
```

You should see waitress log a line like `Serving on http://127.0.0.1:5000`. In a second Command Prompt window:

```bat
curl http://127.0.0.1:5000/api/health
```

Expect `{"status": "ok"}`. Press `Ctrl+C` in the first window to stop it once confirmed — the Windows Service will take over from here.

## 7. Install the backend as a Windows Service

From the same elevated Command Prompt, still in `backend\`:

```bat
venv\Scripts\python windows_service.py install
venv\Scripts\python windows_service.py start
```

Then set it to start automatically on boot and depend on nothing missing at boot time:

```bat
sc config EvolveBusinessSuite start= auto
```

Verify:

```bat
sc query EvolveBusinessSuite
curl http://127.0.0.1:5000/api/health
```

**Useful commands** (all from an elevated prompt):

```bat
venv\Scripts\python windows_service.py stop
venv\Scripts\python windows_service.py restart
venv\Scripts\python windows_service.py remove
```

Service logs go to the Windows **Event Viewer** (`Windows Logs → Application`, source `EvolveBusinessSuite`) for start/stop events; application-level errors are visible there too since Flask's default logger writes to stderr, which the service framework captures.

## 8. Configure IIS

1. Open **IIS Manager**.
2. Right-click **Sites → Add Website**:
   - **Site name**: `EvolveBusinessSuite`
   - **Physical path**: `C:\Apps\EvolveBusinessSuite\frontend-dist`
   - **Binding**: `https`, port `443`, with your TLS certificate (or `http`/`80` temporarily if you're setting up TLS separately — see below)
3. Copy `deploy\windows\web.config` into `frontend-dist\` (it must sit next to `index.html`).
4. Server-level, one-time: in IIS Manager, click the **server name** (top of the tree, not the site) → **Application Request Routing Cache** → in the Actions pane, **Server Proxy Settings** → check **Enable proxy** → Apply. Without this step the reverse-proxy rule in `web.config` will 502.
5. Restart the site (or `iisreset` for the whole server).

### TLS/HTTPS

Use whatever certificate your organization already issues for internal Windows Server sites (an internal CA, or a purchased cert imported via IIS Manager → Server Certificates). If you don't have one yet and this server is internet-facing, [win-acme](https://www.win-acme.com/) is the standard free tool for provisioning and auto-renewing a Let's Encrypt certificate on IIS — install and run it after the site above exists so it can bind the cert to it.

### Firewall

Open **Windows Defender Firewall with Advanced Security** and allow inbound TCP 443 (and 80 if you're doing an HTTP→HTTPS redirect) for the IIS site. **Do not** open port 5000 — the backend should only ever be reachable via `127.0.0.1`, which is exactly what `WAITRESS_HOST=127.0.0.1` (the default) already enforces.

## 9. Verify end-to-end

From a browser on the server (or anywhere, once DNS points at it):

1. Visit your site's URL — you should land on the login page.
2. Log in with tenant `demo`, email `owner@demo.com`, password `Demo123!` (seeded by `seed.py`; also printed to its console output) and confirm the dashboard loads. **Change or delete this account** once you've verified login — it's a known demo credential, not meant to survive into real use.
3. Visit `/admin/login` and sign in with the `SUPERADMIN_BOOTSTRAP_EMAIL`/`PASSWORD` from your `.env` — confirm the tenant list loads.
4. In the browser devtools Network tab, confirm `/api/...` requests return `200` from the same origin as the page (no CORS errors, no requests to `localhost:5000`).

If step 4 shows requests failing with a proxy error, re-check the ARR "Enable proxy" setting from step 8.4 — this is the most common miss.

---

## Updating the application

1. Stop the service: `venv\Scripts\python windows_service.py stop`
2. Replace the `backend\app`, `backend\migrations`, and `frontend-dist\` folders with the new versions (keep your existing `.env` and `venv\`).
3. `venv\Scripts\pip install -r requirements.txt -r requirements-windows.txt` (in case dependencies changed)
4. `venv\Scripts\flask db upgrade` (applies any new migrations)
5. `venv\Scripts\python windows_service.py start`
6. `iisreset` (picks up the new static frontend files)

## Backups

- **Database**: schedule `pg_dump` via Windows Task Scheduler (PostgreSQL's own docs cover this — search "pg_dump Windows Task Scheduler"). This is the record of truth; back it up on a real schedule with off-box retention.
- **Uploaded files**: if `S3_BUCKET` is *not* configured, the app falls back to storing contract/attachment uploads on local disk under `backend\storage\` (`LocalDiskStorage` — see `app/services/storage.py`). Back this folder up too, or configure `S3_BUCKET` + credentials in `.env` to move that storage off-box entirely, which is the recommended path for a real production deployment.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| IIS shows a generic 502/504 on any page | ARR proxy not enabled (step 8.4), or the Windows Service isn't running — check `sc query EvolveBusinessSuite` |
| Login page loads but login always fails with a network error | Backend service isn't reachable — confirm `curl http://127.0.0.1:5000/api/health` works *on the server itself* |
| Direct links like `/invoices/abc-123` 404 on refresh | `web.config` isn't next to `index.html`, or the URL Rewrite module isn't installed |
| `flask db upgrade` fails to connect | Check `DATABASE_URL` in `.env`, and that the PostgreSQL Windows service is running (`services.msc` → "postgresql-x64-16") |
| Service won't install: `pywintypes` import error | Re-run `venv\Scripts\python -m pywin32_postinstall -install` (step 3) |
| Integrations (O365/Google/Authorize.net) show "Not Configured" | Expected until you fill in the relevant keys in `.env` — see the comments in `.env.example`. The app is fully functional without them; those are optional third-party integrations, not requirements. |

## Notes on multi-tenant licensing

This is one deployment serving every tenant (client) ETG provisions — tenants are a row in the database, not separate installs. Provision new clients from the super-admin console (`/admin`, the `SUPERADMIN_BOOTSTRAP_EMAIL` login): create the tenant, toggle which modules they're licensed for (AR/AP, Inventory, Work Orders, Transportation, Order Tracking, Contract Manager, Customer Portal, Project Manager), set their seat count and license dates. None of that requires touching this server install again.
