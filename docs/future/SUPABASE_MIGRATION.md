# ☁️ Project: Supabase & Cloud Native Migration

## Goal
Transition from local file-based storage and Google Sheets to a professional Cloud-Native stack for better scalability and data persistence.

## 🏗 Target Stack
- **Database**: Supabase (PostgreSQL) for trade history and state.
- **Compute**: Railway Worker (for 24/7 WebSockets).
- **Frontend**: Next.js (hosted on Vercel) for a custom trading dashboard.

## 📊 Data Schema (Planned)
- `positions`: Current active trades.
- `trade_history`: Historical performance and analytics.
- `config`: Centralized bot settings.

## 📅 Roadmap
1. [ ] Define PostgreSQL schema in Supabase.
2. [ ] Replace `Syncer` class with a Database Client.
3. [ ] Build basic Next.js dashboard for monitoring.
