# 🛠️ Shared Utilities (`orbiter/utils/`)

## 🎯 Single Responsibility Principle (SRP)
The `utils/` directory provides **Stateless Helpers & Infrastructure**. These modules are globally accessible functions required for system stability, logging, parsing, and data I/O.

## 📂 Architecture

### 1. `argument_parser.py`
- Parses CLI arguments (e.g., `--simulation=true --strategyId=xyz`) into generic runtime facts.
- Safely falls back to `system.json` defaults and handles case insensitivity.

### 2. `system.py` / `bootstrap.py`
- Resolves the absolute path of the `project_root` to ensure robust imports regardless of where the script is executed from.

### 3. `lock.py`
- Implements process-level locking (`.orbiter.lock`). Prevents fatal collisions by ensuring only one instance of Orbiter runs at a time.

### 4. `logger.py`
- Configures the custom logging format. Routes `INFO` logs to the console and `TRACE/DEBUG` to rotated files in `logs/system/`.

### 5. `data_manager.py` / `schema_manager.py`
- Standardizes JSON/YAML reads and writes. Centralizes schema lookups to decouple hardcoded keys from the application layer.

## 🛑 Strict Boundaries
- No trading domain knowledge or broker API logic is permitted here. Utilities must remain completely stateless and reusable.