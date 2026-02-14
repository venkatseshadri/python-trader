# 📜 Changelog

All notable changes to the ORBITER project will be documented in this file.

## [3.0.0] - 2026-02-14
### Added
- **Modular Engine**: Decoupled Evaluator, Executor, and State management.
- **Docker Support**: Added `Dockerfile` and `docker-compose.yml` for containerized deployment.
- **Unified Installation**: New `install/` directory for Docker and Raspberry Pi setups.
- **Documentation Hub**: Comprehensive Technical, Functional, and Integration guides in `docs/`.
- **Shoonya Integration**: Low-level API client and Master contract handling.
- **Google Sheets Logging**: Real-time position tracking and trade logs.

### Fixed
- Redundant root directories cleaned up and organized.
- `.gitignore` and `.dockerignore` optimized for `__pycache__` and environment files.

## [Planned: 3.1.0]
- **Remote Control**: PM2 integration and Telegram Bot for status/kill-switch.
- **Dynamic Config**: Ability to update risk parameters via Google Sheets.

## [Planned: 4.0.0]
- **Cloud Native**: Migration to Railway (Worker) and Supabase (PostgreSQL).
- **Web UI**: Next.js dashboard for portfolio management.
