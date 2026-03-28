# Orbiter Architecture & Flow Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Startup Flow](#startup-flow)
3. [Tick Flow (Trading Cycle)](#tick-flow-trading-cycle)
4. [Scoring Flow](#scoring-flow)
5. [Order Execution Flow](#order-execution-flow)
6. [Strategy Configuration](#strategy-configuration)
7. [Key Components](#key-components)
8. [Configuration Files](#configuration-files)
9. [Testing Guidelines](#testing-guidelines)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ORBITER                                         │
│                    (Root Orchestrator)                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  main.py ──► OrbiterApp ──► EngineBuilder ──► CoreEngine                 │
│      │            │              │                  │                       │
│      │            │              │                  ├──► RuleManager        │
│      │            │              │                  ├──► ActionManager      │
│      │            │              │                  └──► StateManager       │
│      │            │              │                                             │
│      │            │              └──► BrokerClient                           │
│      │            │                             │                            │
│      │            │                    ┌────────┴────────┐                   │
│      │            │                    │ ScripMaster    │                   │
│      │            │                    │ (Token Maps)  │                   │
│      └──► Lock   │                    └────────▲────────┘                   │
│           File   │                             │                            │
│                                         ┌─────┴─────┐                       │
│                                         │ Equity    │                       │
│                                         │ Futures   │                       │
│                                         │ Options   │                       │
└─────────────────────────────────────────┴───────────┴───────────────────────┘
```

### Directory Structure

| Directory | Purpose |
|-----------|---------|
| `core/` | Execution engine, broker integrations, analytics |
| `strategies/` | Strategy configs (rules, filters, instruments) |
| `bot/` | Telegram C2 interface |
| `config/` | System-wide configs (system.json, secrets) |
| `utils/` | Shared utilities |
| `tests/` | Unit and integration tests |

---

## Startup Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            STARTUP FLOW                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. main.py                                                                 │
│     ├── Parse CLI (--caller, --logLevel, --mode, --strategyCode)        │
│     ├── Acquire lock file (prevent duplicate instances)                    │
│     ├── setup_logging()                                                   │
│     └── bootstrap() loads manifest, constants, config                       │
│                                                                             │
│  2. OrbiterApp.__init__                                                   │
│     ├── Load SchemaManager (loads schema.json)                             │
│     ├── Load SessionManager                                                │
│     │   └── Load strategy bundle from strategy.json                        │
│     │       └── files: {rules_file, instruments_file, filters_file}       │
│     ├── Create RuleManager (loads scoring rules)                          │
│     └── Create ActionManager                                               │
│                                                                             │
│  3. OrbiterApp.run()                                                       │
│     ├── EngineBuilder.build()                                              │
│     │   ├── Load universe (instruments)                                    │
│     │   ├── Create BrokerClient                                            │
│     │   │   └── Load ScripMaster (token maps)                             │
│     │   ├── Create StateManager                                            │
│     │   └── Create CoreEngine                                              │
│     │       └── Create RuleManager (strategy-specific rules)               │
│     ├── Login to broker                                                    │
│     ├── Prime data (fetch historical candles)                             │
│     └── Start WebSocket feed                                               │
│                                                                             │
│  4. Enter main loop                                                        │
│     └── tick() called every UPDATE_INTERVAL seconds                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Files in Startup

| File | Responsibility |
|------|----------------|
| `main.py` | Entry point, lock management |
| `core/app.py` | OrbiterApp - orchestrates initialization |
| `core/engine/session/session_manager.py` | Loads strategy config |
| `core/engine_builder.py` | Builds CoreEngine |
| `core/engine/runtime/core_engine.py` | The tick loop |

---

## Tick Flow (Trading Cycle)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TICK FLOW                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  tick() ──┬──► 1. Evaluate Global Engine Rules                            │
│           │       (non-instrument rules like market hours check)           │
│           │                                                               │
│           ├──► 2. For Each Symbol in Universe:                           │
│           │                                                               │
│           │    a. Get live price from WebSocket                           │
│           │                                                               │
│           │    b. Fetch OHLCV candles                                     │
│           │                                                               │
│           │    c. Calculate Technical Facts                                │
│           │        ├── TechnicalAnalyzer.analyze()                        │
│           │        │   └── Computes: EMA, RSI, ADX, ATR, SuperTrend      │
│           │        └── FactCalculator                                      │
│           │            └── Runs custom filters (F1-F11)                   │
│           │                                                               │
│           │    d. SCORING (if tech facts calculated)                      │
│           │        └── evaluate_score()                                    │
│           │            └── Uses scoring_expression from rules.json        │
│           │                                                               │
│           │    e. Check Entry Filters (F1-F11)                            │
│           │                                                               │
│           │    f. If filters pass and score > threshold:                  │
│           │        └── Trigger ORDER OPERATIONS                            │
│           │                                                               │
│           │    g. Check Exit Filters (SL/TP)                              │
│           │                                                               │
│           └──► 3. Process Actions (batch execute)                        │
│                   ├── Place orders                                         │
│                   ├── Update SL/TP                                        │
│                   └── Sync with broker                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tick Flow Details

1. **Global Rules Evaluation**: Checks rules that apply to the entire engine (e.g., is market open?)

2. **Per-Symbol Processing**:
   - Get latest price from WebSocket
   - Fetch OHLCV candles (historical data)
   - Calculate technical indicators
   - Run custom filters
   - Calculate score
   - Check entry/exit conditions

3. **Action Processing**: Batch execute all generated actions

---

## Scoring Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SCORING FLOW                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Scoring is defined in: strategies/<strategy>/rules.json                  │
│                                                                             │
│  {                                                                           │
│    "scoring_rules": [                                                       │
│      {                                                                      │
│        "name": "Calculate Trend Score",                                     │
│        "priority": 10,                                                     │
│        "scoring_expression": "market_adx * weight_adx + ..."              │
│      }                                                                      │
│    ]                                                                        │
│  }                                                                           │
│                                                                             │
│  Evaluation:                                                                │
│                                                                             │
│  1. CoreEngine.tick() calls rule_manager.evaluate_score()                 │
│                                                                             │
│  2. evaluate_score() builds facts dict:                                   │
│     ├── market_adx (from TechnicalAnalyzer)                                │
│     ├── market_ema_fast                                                    │
│     ├── market_ema_slow                                                    │
│     ├── market_supertrend_dir                                              │
│     └── filters_scoring_combined_score_weight_*                           │
│         (from filters.json scoring.combined_score section)                │
│                                                                             │
│  3. Compile scoring expression (replace dots with underscores)            │
│                                                                             │
│  4. Evaluate using rule_engine library                                     │
│                                                                             │
│  5. Return score (float)                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Scoring Expression Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `market_adx` | TechnicalAnalyzer | ADX indicator value |
| `market_ema_fast` | TechnicalAnalyzer | Fast EMA (5 period) |
| `market_ema_slow` | TechnicalAnalyzer | Slow EMA (20 period) |
| `market_supertrend_dir` | TechnicalAnalyzer | Direction: 1 (bull) or -1 (bear) |
| `filters_scoring_combined_score_weight_*` | filters.json | Weights from config |

### ADX Fallback

When broker historical data is insufficient (less than 12 candles), the system falls back to Yahoo Finance for ADX based on exchange:

```
Insufficient broker candles (< 12)
         │
         ▼
FactCalculator.calculate_technical_facts()
         │
         ├─► MCX: Return zeros (no fallback - avoids false signals)
         │
         ├─► NFO: YF Adapter.get_market_adx('NIFTY', '5m')
         │
         ├─► BFO: YF Adapter.get_market_adx('SENSEX', '5m')
         │
         ▼
Cache ADX for 5 minutes
```

| Exchange | YF Index | Why |
|----------|----------|-----|
| NFO | NIFTY | NSE derivatives track NIFTY |
| BFO | SENSEX | BSE derivatives track SENSEX |
| MCX | None | Commodities don't track equity indices |

The `data_source` fact is set to `'broker'`, `'yf_fallback'`, or `'none'` to track data origin.
         │
         ▼
Use YF ADX in scoring
```

This ensures scoring works:
- Outside market hours (no broker candles)
- On fresh start before WebSocket populates data

---

## Order Execution Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ORDER EXECUTION FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Rule Action Triggered ──► ActionManager.queue_action()                   │
│                                                                             │
│  After all symbols processed ──► ActionManager.process_queue()             │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │                     ActionExecutor                           │           │
│  ├─────────────────────────────────────────────────────────────┤           │
│  │  1. Get action from queue                                  │           │
│  │  2. Determine action type (place_order, update_sl, etc.)  │           │
│  │  3. Resolve contract (for futures)                         │           │
│  │     └── BrokerClient.get_near_future()                     │           │
│  │  4. Calculate margin/span                                   │           │
│  │     └── BrokerClient.calculate_span()                       │           │
│  │  5. Execute via BrokerClient                                │           │
│  │     └── BrokerClient.place_order()                          │           │
│  │  6. Update StateManager                                    │           │
│  │     └── state.on_order_update()                            │           │
│  └─────────────────────────────────────────────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Strategy Configuration

### Strategy Directory Structure

```
strategies/
├── mcx_trend_follower/
│   ├── strategy.json      # Strategy metadata & parameters
│   ├── rules.json         # Entry/exit rules & scoring
│   ├── filters.json       # Filter configurations
│   └── instruments.json   # Trading universe
├── nifty_fno_topn_trend/
│   └── ...
└── bsensex_bfo_topn_trend/
    └── ...
```

### strategy.json

```json
{
  "name": "MCX Commodities TopN Trend",
  "exchange_id": "mcx",
  "strategy_type": "top_n",
  "files": {
    "rules_file": "orbiter/strategies/mcx_trend_follower/rules.json",
    "instruments_file": "orbiter/strategies/mcx_trend_follower/instruments.json",
    "filters_file": "orbiter/strategies/mcx_trend_follower/filters.json"
  },
  "strategy_parameters": {
    "top_n": 3,
    "trend_score_threshold": 0.40,
    "lot_multiplier": 1,
    "max_drawdown": 10000
  }
}
```

### rules.json

```json
{
  "scoring_rules": [
    {
      "name": "Calculate Commodity Trend Score",
      "priority": 10,
      "scoring_expression": "market_adx * weight_adx + ...",
      "description": "..."
    }
  ],
  "strategies": [
    {
      "name": "MCX_TopN_Trend_Execution",
      "priority": 100,
      "market_signals": {
        "allOf": [
          { "fact": "session.is_trade_window", "operator": "equal", "value": true },
          { "fact": "portfolio.active_positions", "operator": "equal", "value": 0 }
        ]
      },
      "execution_logic": "TOP_N",
      "scoring_fact": "strategy.trend_score",
      "order_operations": [
        { "type": "trade.place_future_order", "params": {...} }
      ]
    }
  ]
}
```

### filters.json

```json
{
  "entry": {
    "adx": { "enabled": true, "time_period": 14, "threshold": 20 },
    "supertrend": { "enabled": true, "period": 10, "multiplier": 3 }
  },
  "scoring": {
    "combined_score": {
      "enabled": true,
      "score_weight_adx": 0.4,
      "score_weight_ema_slope": 0.3,
      "score_weight_supertrend": 0.3
    }
  },
  "exit": {
    "sl": { "smart_atr": { "enabled": true, "mult": 2.0 } },
    "tp": { "trailing_sl": { "enabled": true, "retracement_pct": 30 } }
  }
}
```

---

## Key Components

### ScripMaster (`core/broker/master/__init__.py`)

Manages token mappings for equities, futures, and options.

| Method | Purpose |
|--------|---------|
| `load_mappings(segment)` | Load token mappings for NFO/MCX/BFO |
| `download_scrip_master(exchange)` | Download master from broker |
| `check_and_update_mcx_expiry()` | Auto-update expired MCX contracts |

### RuleManager (`core/engine/rule/rule_manager.py`)

Compiles and evaluates strategy rules.

| Method | Purpose |
|--------|---------|
| `evaluate(source, context)` | Evaluate rules and return actions |
| `evaluate_score(source, context)` | Calculate trading score |
| `_load_and_compile_scoring_rules()` | Load scoring rules from rules.json |

### SessionManager (`core/engine/session/session_manager.py`)

Manages strategy selection and session context.

| Method | Purpose |
|--------|---------|
| `get_active_rules_file()` | Get path to strategy rules.json |
| `get_active_universe()` | Get instruments list |
| `get_active_segment_name()` | Get current exchange (mcx/nfo/bfo) |

---

## Configuration Files

| File | Purpose |
|------|---------|
| `orbiter/config/manifest.json` | Master registry of all config files |
| `orbiter/config/constants.json` | Hardcoded strings, event types |
| `orbiter/config/config.json` | Strategy codes, defaults |
| `orbiter/config/global_config.json` | Global trading params (optional) |
| `orbiter/config/session.json` | Broker credentials path |
| `orbiter/data/mcx_futures_map.json` | MCX token mappings with expiry |

> **Token Verification:** Run `python -m orbiter.utils.mcx.update_mcx_config --full` to fetch latest tokens from Shoonya API. Verify instruments.json tokens match MCX_symbols.txt.

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_rule_manager_*.py
│   ├── test_fact_calculator_*.py
│   └── ...
├── brokers/                 # Broker integration tests
├── integration/             # Full flow tests
└── README.md               # Testing documentation
```

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/unit/test_rule_manager_real_data.py

# With coverage
pytest --cov=orbiter tests/
```

### Key Test Cases Required

1. **Startup Flow**: Test strategy loading, schema initialization
2. **Scoring Flow**: Test score calculation with various inputs
3. **Filter Flow**: Test custom filters (F1-F11)
4. **Order Execution**: Test order placement, margin calculation
5. **MCX Updates**: Test expiry checking and contract updates

---

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|-----------|
| `Session Expired` | Broker session token invalid | Check login, re-authenticate |
| `No module named 'orbiter.*'` | PYTHONPATH issue | Ensure project_root in sys.path |
| `Lock file exists` | Previous instance running | Remove lock file or check process |
| `Score 0.00` | Scoring facts not loading | Check rules.json and filters.json |
| `Future contract not found` | MCX contract expired | Run update_mcx_config.py |

### Logging Levels

| Level | Usage |
|-------|-------|
| `TRACE` | Detailed debug (function entry, variable values) |
| `DEBUG` | Debug info (API calls, state changes) |
| `INFO` | General info (ticks, scores, orders) |
| `WARNING` | Recoverable issues |
| `ERROR` | Errors that need attention |
| `CRITICAL` | Fatal errors |

Set via: `ORBITER_LOG_LEVEL=DEBUG python main.py ...`
