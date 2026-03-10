# NFO Trading Flow - Complete Technical Specification

## Table of Contents
1. [Command Line Arguments](#1-command-line-arguments)
2. [Startup Flow](#2-startup-flow)
3. [JSON Configuration Files](#3-json-configuration-files)
4. [Strategy Execution Flow](#4-strategy-execution-flow)
5. [Option Resolution Flow](#5-option-resolution-flow)
6. [Key Methods and Python Files](#6-key-methods-and-python-files)

---

## 1. Command Line Arguments

### Entry Point
```
python orbiter/main.py [arguments]
```

### Available Arguments

| Argument | Alias | Description | Example |
|----------|-------|-------------|---------|
| `--paper_trade` | `--paper` | Paper trading mode (default: true) | `--paper_trade=false` |
| `--office_mode` | `--office` | Live data, no trades | `--office_mode=true` |
| `--strategyCode` | `--sc` | Short strategy code | `--strategyCode=n1` |
| `--strategyId` | `--sid` | Full strategy name | `--strategyId=nifty_fno_topn_trend` |
| `--strategyExecution` | `--se` | Dynamic strategy selection | `--strategyExecution=dynamic` |

### Strategy Codes (from system.json)
```json
{
  "strategy_codes": {
    "m1": "mcx_trend_follower",
    "n1": "nifty_fno_topn_trend",
    "n2": "nifty_50_nfo_expiry_day_short_straddle",
    "s1": "bsensex_bfo_topn_trend",
    "s2": "sensex_bfo_expiry_day_short_straddle"
  }
}
```

### Mode Matrix

| paper_trade | office_mode | Result |
|------------|-------------|--------|
| true | false | **PAPER TRADING** (simulated orders) |
| false | false | **LIVE TRADING** (real orders) |
| false | true | **OFFICE MODE** (live data, no trades) |

---

## 2. Startup Flow

```
main.py (Entry Point)
    │
    ├── 1. bootstrap() → Verify project.json exists
    │
    ├── 2. ArgumentParser.parse_cli_to_facts()
    │   ├── Parse CLI args → facts dict
    │   ├── Resolve strategyCode → strategyId
    │   └── Load system.json for strategy_codes mapping
    │
    ├── 3. setup_logging() → Initialize logger
    │
    ├── 4. manage_lockfile() → Acquire lock
    │
    └── 5. OrbiterApp(project_root, context).run()
        │
        ├── SessionManager → Broker login
        ├── RuleManager → Load rules
        ├── ActionManager → Register actions
        └── EngineFactory → Build trading engine
```

---

## 3. JSON Configuration Files

### File Locations and Purpose

| File Path | Purpose | Loaded By |
|-----------|---------|-----------|
| `orbiter/config/system.json` | Strategy codes mapping, default strategy | `ArgumentParser` |
| `orbiter/config/dynamic_strategy_rules.json` | Dynamic strategy config | `ArgumentParser` |
| `orbiter/config/global.json` | Global settings | `OrbiterApp` |
| `orbiter/config/constants.json` | Magic strings, keys | Multiple |
| `orbiter/config/exchange_config.json` | Exchange-specific settings (lot_size, etc.) | `BrokerClient` |
| `orbiter/strategies/{strategy}/instruments.json` | Stock symbols to trade | `EngineFactory` |
| `orbiter/strategies/{strategy}/rules.json` | Trading rules, scoring, strike_logic | `RuleManager` |
| `orbiter/strategies/{strategy}/filters.json` | Filter weights | `RuleManager` |
| `orbiter/strategies/{strategy}/strategy.json` | Strategy metadata | `EngineFactory` |
| `orbiter/data/futures_master.json` | Futures data (exists ✅) | `ScripMaster` |
| `orbiter/data/mcx_futures_map.json` | MCX futures mapping | `ScripMaster` |
| `orbiter/data/nfo_futures_map.json` | NFO futures mapping | `ScripMaster` |

### instruments.json Example
```json
[
  {
    "symbol": "RELIANCE",
    "token": "2885",
    "exchange": "NSE",
    "derivative": "option",
    "instrument_type": "stock",
    "expiry_cycle": "monthly"
  }
]
```

### rules.json Example (strike_logic from JSON)
```json
{
  "scoring_rules": [...],
  "order_operations": [
    {
      "type": "trade.place_spread",
      "params": {
        "side": "BUY",
        "strike": "ATM+1",
        "option_type": "CE",
        "expiry_type": "weekly+0"
      }
    },
    {
      "type": "trade.place_spread", 
      "params": {
        "side": "SELL",
        "strike": "ATM-1",
        "option_type": "PE",
        "expiry_type": "weekly+0"
      }
    }
  ]
}
```

---

## 4. Strategy Execution Flow

```
CoreEngine.tick()
    │
    ├── For each instrument in instruments.json:
    │   │
    │   ├── Load futures data from broker (SYMBOLDICT)
    │   │
    │   ├── FactCalculator.calculate_technical_facts()
    │   │   ├── Calculate ADX, EMA, SuperTrend
    │   │   └── YF fallback if < 12 candles
    │   │
    │   ├── RuleManager.evaluate()
    │   │   └── Calculate score from rules.json
    │   │
    │   └── If score >= threshold:
    │       └── Execute trade via ActionManager
    │
    └── ActionManager.execute_batch()
        │
        └── place_spread() [options.py]
            │
            └── BrokerClient.resolve_option_symbol()
```

---

## 5. Option Resolution Flow

### The Two-Phase Approach

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: SCANNING (Futures)                                │
│ Data Source: futures_master.json (EXISTS ✅)               │
├─────────────────────────────────────────────────────────────┤
│ 1. Load instruments.json → Get stock symbols               │
│ 2. Get futures data from futures_master.json               │
│ 3. Calculate indicators (ADX, EMA, SuperTrend)            │
│ 4. Score from rules.json                                   │
│ 5. If score >= threshold → TRADE                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: TRADE EXECUTION (Options)                         │
│ Data Source: Broker API (on-the-fly)                       │
├─────────────────────────────────────────────────────────────┤
│ 1. resolve_option_symbol()                                 │
│    Input: symbol, ltp, option_type, strike_logic, expiry │
│    └── rules.json provides: strike_logic="ATM+1"          │
│                                                          │
│ 2. _select_expiry()                                       │
│    └── Determine expiry date                              │
│                                                          │
│ 3. _get_option_rows()                                      │
│    ├── Try futures_master.json                            │
│    │   └── If empty → Query broker API                  │
│    │                                                       │
│    └── _query_broker_options_api()                        │
│        ├── get_security_info() → lot_size                │
│        └── Generate strikes around ATM (ltp)              │
│                                                          │
│ 4. Apply strike_logic (ATM, ATM+1, ATM-4)                │
│    └── From rules.json: "strike": "ATM+1"                │
│                                                          │
│ 5. Return: {token, tradingsymbol, lot_size, exchange}    │
│                                                          │
│ 6. place_spread() → Execute order via broker API        │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Key Methods and Python Files

### Phase 1: Startup & Strategy Loading

| Step | Python File | Method | JSON Read |
|------|-------------|--------|-----------|
| Parse CLI | `orbiter/utils/argument_parser.py` | `ArgumentParser.parse_cli_to_facts()` | `system.json` |
| Load Strategy | `orbiter/core/engine/builder/engine_factory.py` | `build()` | `strategy/{name}/strategy.json` |
| Load Instruments | `orbiter/core/engine/builder/engine_factory.py` | `load_instruments()` | `strategy/{name}/instruments.json` |
| Load Rules | `orbiter/core/engine/rule/rule_manager.py` | `load_rules()` | `strategy/{name}/rules.json` |
| Load Filters | `orbiter/core/engine/rule/rule_manager.py` | `load_filters()` | `strategy/{name}/filters.json` |

### Phase 2: Scanning (Futures)

| Step | Python File | Method | JSON Read |
|------|-------------|--------|-----------|
| Get Futures Data | `orbiter/core/broker/__init__.py` | `SYMBOLDICT` | `futures_master.json` |
| Calculate Indicators | `orbiter/core/engine/rule/fact_calculator.py` | `calculate_technical_facts()` | - |
| Score Calculation | `orbiter/core/engine/rule/rule_manager.py` | `evaluate()` | `rules.json` |

### Phase 3: Trade Execution (Options)

| Step | Python File | Method | Input | Output |
|------|-------------|--------|-------|--------|
| Resolve Option | `orbiter/core/broker/resolver.py` | `resolve_option_symbol()` | symbol, ltp, option_type, strike_logic | contract details |
| Get Expiry | `orbiter/core/broker/resolver.py` | `_select_expiry()` | symbol, expiry_type | expiry date |
| Get Option Rows | `orbiter/core/broker/resolver.py` | `_get_option_rows()` | symbol, ltp, expiry, instrument | option rows |
| Query Broker API | `orbiter/core/broker/resolver.py` | `_query_broker_options_api()` | symbol, ltp, expiry | lot_size, strikes |
| Execute Order | `orbiter/core/broker/executor.py` | `place_spread()` | contract details | order result |

---

## Complete Parameter Flow

```
CLI: --strategyCode=n1 --paper_trade=true
    │
    ▼
ArgumentParser.parse_cli_to_facts()
    ├── Read system.json → Get strategy_codes
    ├── Resolve "n1" → "nifty_fno_topn_trend"
    └── Return: {paper_trade: true, strategyid: "nifty_fno_topn_trend"}
    │
    ▼
OrbiterApp(project_root, context)
    │
    ▼
EngineFactory.build(strategy_id="nifty_fno_topn_trend")
    ├── Load strategy/strategy.json
    ├── Load instruments.json → [RELIANCE, TCS, HDFCBANK, ...]
    ├── Load rules.json → scoring_rules, order_operations
    └── Load filters.json → scoring weights
    │
    ▼
CoreEngine.tick() [for each instrument]
    │
    ├── Get futures data from broker (SYMBOLDICT)
    ├── calculate_technical_facts() → ADX=35, EMA=24100, ST=1
    ├── evaluate() → score = 5.0
    └── If score >= 3.0 → Execute trade
    │
    ▼
resolve_option_symbol("RELIANCE", ltp=2950, "CE", "ATM+1", "weekly")
    │
    ├── _select_expiry("RELIANCE", "weekly", "OPTSTK")
    │   └── Return: 2026-03-27
    │
    ├── _get_option_rows("RELIANCE", ltp=2950, expiry, "OPTSTK")
    │   ├── Try futures_master.json → 0 rows
    │   └── _query_broker_options_api()
    │       ├── get_security_info("NFO", "RELIANCE26MARF") → lot_size=25
    │       └── Generate strikes: 2900, 2950, 3000, ...
    │
    ├── Apply strike_logic: ATM+1 → strike = 3000
    │
    └── Return: {token: "...", tradingsymbol: "RELIANCE27MAR26CE3000", lot_size: 25}
    │
    ▼
place_spread() → Broker API
```

---

## Data Source Summary

| Phase | Data Type | Source | Exists? |
|-------|-----------|--------|---------|
| Scanning | Futures | `futures_master.json` | ✅ YES |
| Trading | Options | Broker API (on-the-fly) | - |

**Key Point**: No `options_master.json` file needed. Options data is queried from broker API at trade time.
