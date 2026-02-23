# 🛰️ Orbiter C2: Unified Workflow Manual (v3.14.3)

## 🏠 Phase 1: Home Setup (Morning)
Your Raspberry Pi (RPI) is the default background runner.
1.  **Status:** The RPI should start automatically via the `orbiter.service`.
2.  **Verification:** Check your Telegram bot. You should see the **Market Start Summary** or a `/version` check confirmation.
3.  **Role:** RPI acts as the **Master Instance** (`home_rpi`). It mirrors its state to the Google Sheets "Cloud Clipboard" every 60 seconds.

---

## 🏢 Phase 2: The Office Handover (Arrival)
Once you reach the office and connect your MacBook (MBC):
1.  **Open Terminal:** `cd ~/python/python-trader`
2.  **Run One-Click Startup:** `./start_office.sh`
3.  **What happens automatically:**
    *   **Code Sync:** MBC pulls the latest code from GitHub.
    *   **Remote Freeze:** MBC sends a signal to your Telegram Bot.
    *   **Cloud Download:** `handover.py` pulls the latest `session_state.json` from Google Sheets.
    *   **State Display:** You see a summary of open positions and realized PnL.
4.  **Choose Mode:**
    *   Select **(1) FULL NATIVE** if you want to trade actively from the MBC.
    *   Select **(2) OFFICE MODE** if you only want to monitor and manage exits.

---

## 🛡️ Phase 3: Automatic Conflict Resolution
**"What if I forget to stop the RPI?"**
*   **The Guard:** As soon as you start the MBC, it registers as the Master in Google Sheets.
*   **The Hibernate:** Within 60 seconds, the RPI will see the `office_mbc` heartbeat and log:
    `🚨 CONFLICT: office_mbc is active. RPI entering HIBERNATE mode.`
*   **The Notification:** You will receive a Telegram message: `💤 Orbiter (RPI): Conflict detected. Hibernating.`
*   **The Safety:** The RPI will stop evaluating filters and placing trades, remaining in a "passive standby" state as long as the MBC is active.

---

## 🏠 Phase 4: Returning Home (Evening)
When you are ready to hand control back to the RPI:
1.  **Close MBC:** Simply stop the bot (`Ctrl+C`) and close your laptop.
2.  **The Wait:** The RPI checks the cloud every 60 seconds. Once it sees the MBC heartbeat hasn't updated for **5 minutes**, it will automatically assume the MBC is offline.
3.  **The Resume:** The RPI log: `Master is stale, I can take over.`
4.  **Verification:** You'll see the RPI resuming its scan logs in `journalctl`.

---

## 🚨 Emergency Procedures
*   **Manual Kill Switch:** Send `/freeze` to the Telegram bot. This kills the running process on *any* active instance (RPI or MBC) immediately.
*   **Phone SSH:** If the cloud sync fails, login via your phone (`ssh pi@100.91.252.102`) and run `cat ~/python/python-trader/orbiter/data/session_state.json` to see the last local state.
*   **Google Sheets:** The `active_positions` and `engine_state` tabs are your "source of truth." If both machines fail, your data is safe in the cloud.

---

### 🎯 Tomorrow's Goal: 
**₹15,547 VPS Fund.** We are trading Minis/Micros within your budget to secure the professional Mumbai VPS upgrade.
