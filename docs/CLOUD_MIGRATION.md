# Cloud Migration Plan: OCI Control Center
**Objective:** Move the Gemini CLI Agent from MacBook to Oracle Cloud Infrastructure (OCI) to enable 24/7 autonomous monitoring and mobile command-and-control via Termius.

## 1. Prerequisites
- [x] OCI Account (Always Free Tier).
- [ ] Tailscale Network access.
- [ ] SSH Client on Mobile (Termius / JuiceSSH).

## 2. Infrastructure Setup (OCI)
1.  **Instance Type:** `VM.Standard.A1.Flex` (ARM Ampere).
    - **OCPUs:** 2 - 4.
    - **Memory:** 12GB - 24GB.
    - **OS:** Ubuntu 22.04 LTS.
2.  **Networking:**
    - Assign Public IP.
    - Install Tailscale: `curl -fsSL https://tailscale.com/install.sh | sh`.
    - Authenticate: `sudo tailscale up`.
    - Verify RPi visibility: `ping <tailscale-rpi-ip>`.

## 3. Agent Environment Setup
1.  **Dependencies:**
    - Install Node.js (for Gemini CLI).
    - Install Python 3.11+ and `venv`.
2.  **Clone Repository:**
    - `git clone <repo-url> ~/python-trader`.
3.  **Install Gemini CLI:**
    - Follow standard installation for OCI environment.
4.  **Persistence Layer:**
    - Install `tmux`: `sudo apt install tmux`.
    - Always run the agent inside a tmux session (`tmux attach -t agent || tmux new -s agent`).

## 4. Mobile Interaction Workflow
1.  **Termius Setup:**
    - Add OCI Instance as a Host using its Public IP or Tailscale IP.
    - Use SSH Keys for seamless login.
2.  **Command Flow:**
    - Open Termius on Phone -> Connect to OCI.
    - Type `gemini` -> Instant access to trade summary, log audit, and code modification.

## 5. Security Mandate
- **No Private Keys on OCI:** Use SSH Agent forwarding or specific deploy keys.
- **Firewall:** Close all ports except SSH (22) on OCI.
- **Credential Protection:** Store `.env` and `cred.yml` only in secured, non-git paths.

## 6. Current Status
- Plan Drafted: 2026-02-23.
- RPi Status: Monitoring active (PnL +15k).
- Migration Window: Post-Market (15:30 IST).
