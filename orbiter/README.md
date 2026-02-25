# 🚀 Orbiter

Welcome to **Orbiter**, the high-performance, rule-based algorithmic trading orchestrator.

## 🎯 Single Responsibility Principle (SRP)
The `orbiter/` directory serves as the **Root Orchestrator**. Its singular responsibility is to bootstrap the application, parse command-line arguments, initialize the core engine, and manage the top-level application lifecycle (start, loop, shutdown).

## 📂 Architecture Overview
Orbiter is highly modular, separating concerns into distinct directories:
- **`core/`**: The heart of the application. Contains the execution engine, broker integrations, and analytical summaries.
- **`strategies/`**: Strategy-specific configurations, including rules, filters, and instruments.
- **`bot/`**: Telegram Command & Control (C2) interface for notifications and remote management.
- **`config/`**: System-wide, static configurations (e.g., system.json, secrets).
- **`utils/`**: Shared utilities like logging, file locks, data management, and the CLI argument parser.
- **`tests/`**: Unit and integration tests guaranteeing system integrity.

## 🛠️ Entry Point
- **`main.py`**: The universal entry point. It sets up the environment, resolves the `project_root`, locks the process (to prevent duplicate instances), and instantiates `OrbiterApp`.
- **`CLI Arguments`**: Passing `--simulation=true` or `--strategyId=xyz` allows headless, dynamic strategy swapping without touching the codebase.

## ⚠️ Core Rules
1. **Never leak secrets**: No credentials should ever exist in code. Use `orbiter/bot/credentials.json` or `.env` variables.
2. **Never break the loop**: `main.py` wraps the core execution in a resilient `try-finally` block to guarantee lock releases and graceful degradation.