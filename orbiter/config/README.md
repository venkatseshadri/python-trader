# ⚙️ System Configuration (`orbiter/config/`)

## 🎯 Single Responsibility Principle (SRP)
The `config/` directory serves as the **Global Configuration Registry**. It stores all static, non-strategic configurations required to boot the application.

## 📂 Architecture

### 1. `system.json`
- Defines the application's mandatory file paths, active strategy default, log directories, lock files, and automated bootstrap preferences (like `auto_login`).

### 2. `session.json`
- Defines generic session-wide constants, such as standard EOD square-off times and conflict-check toggles.

### 3. `cred.yml` / `credentials.json`
- **Security:** Stores the highly sensitive API keys, TOTP seeds, Telegram Chat IDs, and Google Service Account credentials.
- **NEVER COMMIT THESE FILES.** They must remain in `.gitignore`.

### 4. Segment Configurations (`mcx/`, `nfo/`)
- Contains segment-specific operational parameters, such as market open/close times, trade window envelopes, and valid data segments.

## 🛑 Strict Boundaries
- This directory does **not** contain trading logic, strategy rules, or dynamic state. It is strictly a static registry queried during `bootstrap()`.