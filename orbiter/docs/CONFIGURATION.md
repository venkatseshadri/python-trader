# Orbiter Configuration Documentation

## Table of Contents
1. [Configuration Hierarchy](#configuration-hierarchy)
2. [Config Files](#config-files)
3. [Strategy Configuration](#strategy-configuration)
4. [Data Files](#data-files)
5. [Environment Variables](#environment-variables)

---

## Configuration Hierarchy

```
Global Config (config/global.json)
    │
    ├── Exchange Config (config/exchange_config.json)
    │       │
    │       └── Strategy Override (strategies/<name>/overrides/exchange_config.json)
    │
    └── Strategy Bundle
            ├── strategy.json (metadata, parameters)
            ├── rules.json (entry/exit rules, scoring)
            ├── filters.json (filter configurations)
            └── instruments.json (trading universe)
```

---

## Config Files

### config/system.json

System-wide settings and strategy code mappings.

```json
{
  "paths": {
    "log_dir": "logs/system",
    "lock_file": ".orbiter.lock",
    "overrides_file": "orbiter/config/overrides.json"
  },
  "bootstrap": {
    "auto_login": true,
    "default_update_interval": 5
  },
  "strategy_codes": {
    "m1": "mcx_trend_follower",
    "n1": "nifty_fno_topn_trend",
    "n2": "nifty_50_nfo_expiry_day_short_straddle",
    "s1": "bsensex_bfo_topn_trend",
    "s2": "sensex_bfo_expiry_day_short_straddle"
  }
}
```

### config/schema.json

Defines schema keys for dynamic configuration loading.

```json
{
  "rule_schema": {
    "rules_key": "strategies",
    "conditions_key": "market_signals",
    "actions_key": "order_operations",
    "priority_key": "priority",
    "fact_key": "fact",
    "operator_key": "operator",
    "value_key": "value"
  },
  "strategy_schema": {
    "name_key": "name",
    "exchange_id_key": "exchange_id",
    "files_key": "files",
    "rules_file_key": "rules_file",
    "instruments_file_key": "instruments_file",
    "strategy_parameters_key": "strategy_parameters"
  }
}
```

### config/global.json

Global trading parameters that apply to all strategies.

```json
{
  "trade_score": 0.40,
  "top_n": 1,
  "option_execute": false,
  "option_product_type": "I",
  "option_price_type": "MKT",
  "option_expiry": "weekly",
  "hedge_steps": 4,
  "update_interval": 5,
  "verbose_logs": true,
  "log_level": "TRACE"
}
```

### config/exchange_config.json

Exchange-specific configuration.

```json
{
  "mcx": {
    "plumbing": {
      "segment_name": "mcx",
      "exchange": "MCX"
    },
    "order_prefix": "MCX"
  },
  "nfo": {
    "plumbing": {
      "segment_name": "nfo",
      "exchange": "NSE"
    }
  }
}
```

### config/mcx/config.json

MCX-specific settings.

```json
{
  "market_close": "23:30:00",
  "option_instrument": "OPTFUT"
}
```

---

## Strategy Configuration

### strategy.json

Located in `strategies/<strategy_name>/strategy.json`.

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

Entry/exit rules and scoring expressions.

```json
{
  "scoring_rules": [
    {
      "name": "Calculate Commodity Trend Score",
      "priority": 10,
      "scoring_expression": "market_adx * weight_adx + ...",
      "description": "Combines ADX, EMA slope, and SuperTrend for scoring"
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
      "order_operations": [
        { "type": "trade.place_future_order", "params": {...} }
      ]
    }
  ]
}
```

### filters.json

Filter configurations for entry, scoring, and exit.

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

### instruments.json

Trading universe - list of symbols to trade.

```json
[
  { "symbol": "CRUDEOIL", "token": "472789", "exchange": "MCX" },
  { "symbol": "CRUDEOILM", "token": "472790", "exchange": "MCX" },
  { "symbol": "NATURALGAS", "token": "475111", "exchange": "MCX" },
  { "symbol": "GOLD", "token": "454818", "exchange": "MCX" }
]
```

> **Token Source:** Use `python -m orbiter.utils.mcx.update_mcx_config --full` to fetch latest tokens from Shoonya API.

---

## Data Files

### data/mcx_futures_map.json

MCX futures token mappings with expiry dates. Symbol keys (not numeric tokens).

```json
{
  "CRUDEOIL": [
    "CRUDEOIL",
    "CRUDEOIL19MAR26",
    100,
    "19Mar26"
  ],
  "CRUDEOILM": [
    "CRUDEOILM",
    "CRUDEOILM19MAR26",
    10,
    "19Mar26"
  ]
}
```

Format: `[symbol, trading_symbol, lot_size, expiry_date]`

---

## Environment Variables

| Variable | Values | Description |
|----------|--------|-------------|
| `ORBITER_STRATEGY` | Strategy name | Override strategy selection |
| `ORBITER_SIMULATE_MARKET_HOURS` | true/false | Run outside market hours |
| `ORBITER_LOG_LEVEL` | TRACE/DEBUG/INFO/WARNING/ERROR | Logging level |
| `ORBITER_2FA` | TOTP code | Override 2FA token |

---

## Fact Definitions

### rules/fact_definitions.json

Defines available facts for rules and scoring.

```json
{
  "facts": {
    "market.adx": {
      "provider": "talib",
      "method": "ADX",
      "params": { "time_period": 14 },
      "inputs": ["high", "low", "close"]
    },
    "filter.supertrend": {
      "provider": "custom",
      "module": "orbiter.filters.entry.f4_supertrend",
      "method": "supertrend_filter"
    }
  }
}
```

### Provider Types

| Provider | Description |
|----------|-------------|
| `talib` | Technical analysis from TA-Lib |
| `custom` | Custom filter functions (F1-F11) |
| `derived` | Computed from other facts |
