# 🚀 Modern Orbiter Cloud Stack: Migration Roadmap

> **Update: Feb 23, 2026**
> We have selected **Oracle Cloud (OCI)** as the specific implementation for the "Dedicated VPS" path. This provides an "Always-On" brain for the bot while the Raspberry Pi handles local execution. 
> See the detailed implementation guide here: [OCI Migration Plan](technical_plans/OCI_MIGRATION_20260223.md)

This document outlines the architectural path to migrate the **ORBITER** trading bot from a local/Raspberry Pi environment to a modern, scalable cloud-native stack.

---

## ⚔️ Cloud Provider Comparison

| Feature | **Vercel** | **Railway** | **DigitalOcean** |
| :--- | :--- | :--- | :--- |
| **Best For** | Frontends & Serverless APIs | Modern Backend Workers | Raw Infrastructure (VPS) |
| **Execution Model** | **Serverless:** Short-lived (max 10-60s) | **PaaS:** Persistent (runs 24/7) | **IaaS:** Persistent (runs 24/7) |
| **Trading Bot Compatibility** | ❌ **Poor:** Will timeout; no WebSockets. | ✅ **Excellent:** Handles long-running Python scripts. | ✅ **Excellent:** Full control via Linux (VPS). |
| **Developer Experience** | 🏆 **Elite:** Just push to GitHub. | 🥈 **Great:** Auto-detects Docker/Python. | 🥉 **Manual:** Requires SSH/Linux config. |
| **Pricing** | Free for UI; expensive for APIs. | Pay-as-you-go (very cheap for light bots). | Fixed monthly cost ($4–$6/month). |
| **Persistence** | None (Stateless) | Ephemeral (uses volumes for data) | Full Disk Persistence |

---

## 🏗 The Stack at a Glance

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Execution** | [Railway.app](https://railway.app) | Background worker to run the Python bot 24/7. |
| **Database** | [Supabase](https://supabase.com) | PostgreSQL database for trade logs, P&L, and state persistence. |
| **Frontend** | [Vercel](https://vercel.com) | Next.js dashboard for real-time monitoring and "Kill-switch" control. |
| **Intelligence** | [FastAPI](https://fastapi.tiangolo.com/) | Lightweight API layer for the dashboard to interact with the bot. |

---

## 🛣 Migration Path

### Phase 1: The Data Layer (Supabase)
**Goal:** Move away from volatile `.json` files and rate-limited Google Sheets.
1.  **Schema Design:** Create tables for `trades`, `active_positions`, and `daily_pnl`.
2.  **Client Update:** Modify `orbiter/core/broker/executor.py` to use the Supabase Python SDK for logging instead of `sheets.py`.
3.  **Persistence:** Use Supabase to store the `span_cache` instead of local JSON.

### Phase 2: The Execution Engine (Railway)
**Goal:** High-availability execution with auto-restart and zero maintenance.
1.  **Containerization:** Create a `Dockerfile` for the Orbiter project.
2.  **Environment Variables:** Move all secrets (Shoonya keys, Supabase URLs) from `cred.yml` to Railway Environment Variables.
3.  **Deployment:** Link the GitHub repository to Railway as a "Background Worker."

### Phase 3: The Command Center (Vercel)
**Goal:** A professional-grade UI to monitor the bot from any device.
1.  **Framework:** Initialize a Next.js project with Tailwind CSS.
2.  **Real-time UI:** Use Supabase's Realtime (Postgres Changes) to update the dashboard instantly when a trade is executed.
3.  **Control:** Add buttons to the UI to manually trigger `square_off_all` via a FastAPI webhook running on the bot.

---

## 🛠 Required Technical Artifacts

### 1. Sample `Dockerfile` (for Railway)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r python-trader/orbiter/requirements.txt
CMD ["python", "python-trader/orbiter/main.py"]
```

### 2. Supabase SQL Schema (Initial)
```sql
CREATE TABLE trades (
  id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
  symbol text NOT NULL,
  entry_price numeric,
  exit_price numeric,
  pnl_pct numeric,
  strategy text,
  created_at timestamp with time zone DEFAULT now()
);
```

---

## ⚠️ Critical Considerations

### 1. Latency & Region Matching
- **Constraint:** Most Indian brokers (Shoonya/Finvasia) have servers in **Mumbai**.
- **Action:** When deploying to Railway or Supabase, select the **Mumbai (ap-south-1)** or **Singapore** region if available. This reduces the time it takes for a price tick to reach your bot and for your order to reach the broker.

### 2. Secrets Management
- **Never** commit `cred.yml` or `credentials.json` to GitHub.
- **Railway:** Use the "Variables" tab to store `SHOONYA_USER`, `SHOONYA_PASSWORD`, etc.
- **Python Code:** Update `ConnectionManager` to check for environment variables first before looking for a local file:
  ```python
  import os
  user = os.getenv('SHOONYA_USER') or config['user']
  ```

### 3. WebSocket Stability in Serverless
- Railway is persistent, so WebSockets will stay open. However, cloud providers perform maintenance restarts.
- **Robustness:** Ensure your `BrokerClient` has auto-reconnect logic for the WebSocket feed.

### 4. Cost Optimization
- **Supabase:** The Free Tier is generous enough for a single trader (500MB DB).
- **Railway:** Uses a "vCPU/RAM per hour" model. Ensure you aren't over-provisioning; Orbiter is lightweight and should run on the smallest plan (e.g., 512MB RAM).

---

---

## 📈 Scenario Analysis: Choosing Your Environment

### Scenario A: The Raspberry Pi (Self-Hosted)
*Best for: Hobbyists with zero budget and high Linux skills.*

| Dimension | Rating | Details |
| :--- | :--- | :--- |
| **Monthly Cost** | 🟢 $0 | No recurring fees (excluding home electricity). |
| **Maintenance** | 🔴 High | You are the sysadmin. Power outages or Wi-Fi drops kill trades. |
| **Ease of Use** | 🟡 Medium | Requires SSH, manual updates, and local troubleshooting. |
| **TCO** | 🔴 High | Time spent fixing local hardware issues often exceeds cloud costs. |
| **Scalability** | 🔴 Low | Limited by RPi hardware; scaling requires buying more units. |

**Pros:** Total privacy, no monthly bills.  
**Cons:** High risk of "Slippage" or failed exits during power/internet instability.

---

### Scenario B: Managed Cloud (Railway + Supabase)
*Best for: Serious traders who value time and reliability over raw control.*

| Dimension | Rating | Details |
| :--- | :--- | :--- |
| **Monthly Cost** | 🟡 $5 - $10 | Pay-as-you-go. Usually stays within free tiers for light use. |
| **Maintenance** | 🟢 Low | Zero server management. Auto-restarts on failure. |
| **Ease of Use** | 🏆 High | "Git Push" to deploy. UI-based logs and monitoring. |
| **TCO** | 🟢 Low | Highly efficient; you spend 99% of your time on strategy, 1% on infra. |
| **Scalability** | 🏆 High | One-click upgrades for CPU/RAM. Handles multi-user easily. |

**Pros:** High availability, professional-grade uptime, excellent developer experience.  
**Cons:** Third-party dependency; costs can scale with heavy data usage.

---

### Scenario C: Dedicated VPS (DigitalOcean / AWS)
*Best for: Professional setups requiring low-latency and fixed IPs.*

| Dimension | Rating | Details |
| :--- | :--- | :--- |
| **Monthly Cost** | 🟡 $4 - $6 | Fixed, predictable monthly billing. |
| **Maintenance** | 🟡 Medium | Must handle OS security patches and `systemd` configs. |
| **Ease of Use** | 🔴 Low | Requires manual Linux setup and environment configuration. |
| **TCO** | 🟡 Medium | Balanced; cheap monthly cost but requires manual oversight. |
| **Scalability** | 🟡 Medium | Vertically scale by resizing the VPS (requires downtime). |

**Pros:** Lowest latency (Mumbai region), dedicated IP, full filesystem control.  
**Cons:** If the OS crashes or fills up with logs, you must fix it manually.

---

## 💡 Why this path?
- **Stability:** Cloud data centers have 99.9% uptime compared to home Wi-Fi/Power.
- **Speed:** Lower latency to broker servers when hosted in professional data centers.
- **Scalability:** Easily add multi-user support or trade multiple segments simultaneously without hardware constraints.

---
*Created: Feb 2026 | Reference for Future Development*
