# 🧠 Technical Design: Automatic Candle Priming (Fast-Start)

**Date:** 2026-02-20  
**Status:** Implemented (Commit `b9cede5`)  
**Objective:** Eliminate the "Cold Start" problem where the bot must wait 15 minutes to accumulate enough candles for technical guards (Slope, ATR).

---

## 1. The Problem: "The 15-Minute Blind Spot"
Whenever the bot or Raspberry Pi restarts, the in-memory candle cache is wiped.
- **Guard Rule:** Entry Guards require at least 15 candles to calculate trend conviction.
- **Impact:** The bot is "blind" for the first 15 minutes of every restart, missing crucial trades (e.g., the SILVER move at 18:39).

---

## 2. Technical Modifications (`orbiter/core/broker/__init__.py`)

### A. Proactive REST Fetch
Added `BrokerClient.prime_candles(symbols, lookback_mins=30)`:
- Upon login, the bot calls the Shoonya REST API (`get_time_price_series`).
- It fetches the **last 30 minutes** of 1-minute data for every symbol in the active universe.

### B. Memory Re-hydration
- The fetched candles are injected into `SYMBOLDICT` before the WebSocket feed takes over.
- This "primes" the technical indicators (EMA, ATR) instantly.

---

## 3. Design Outcome
- **Instant Readiness:** The bot can take its first trade within **seconds** of startup.
- **Stability:** Technical guards (Slope Guard, Freshness Guard) have 100% data continuity across restarts.
- **Verification:** Unit test `orbiter/tests/unit/test_priming.py` confirms that `SYMBOLDICT` is correctly populated with historical data.
