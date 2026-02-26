# Dynamic Strategy Selection - Technical Specification

## Overview

This document describes the implementation of **Dynamic Strategy Selection** feature that allows ORBITER to automatically choose between different trading strategies based on market conditions evaluated at a specific time each day.

**Feature Date**: 2026-02-26  
**Status**: Design Phase

---

## Problem Statement

Currently, ORBITER requires a fixed strategy to be specified at startup via CLI (`--strategyCode` or `--strategyId`). Users want the ability to:

1. Automatically select strategy based on market conditions (sideways vs trending)
2. Make the decision at a specific time (e.g., 10:00 AM)
3. Support both fixed and dynamic execution modes

---

## Design Decisions

### Q1: Where does this logic live?

**Decision**: In the argument parser layer

**Rationale**: 
- Simple to implement
- Decision happens before strategy loads
- No changes to core engine required
- Keeps concerns separated

---

### Q2: Configuration Structure

**Decision**: New file `orbiter/config/dynamic_strategy_rules.json`

**Rationale**:
- Keeps configuration clean and separate from system.json
- Easy to modify without touching core config
- Allows multiple dynamic rule sets per exchange

---

### Q3: Time-based condition

**Decision**: User configurable via `dynamic_strategy_check_time` in config

**Details**:
- Default: "10:00"
- Format: HH:MM (24-hour format, IST)
- Check happens after market open + priming period

---

### Q4: CLI Override Conflict

**Decision**: Error if both `--strategyCode` and `--strategyExecution=dynamic` are provided

**Rationale**:
- Prevents ambiguous configuration
- Forces user to choose one mode or the other

---

### Q5: Fallback Behavior

**Decision**: Use ADX (existing in system) as the market condition evaluator

**Details**:
- ADX < 25 → Sideways → Use straddle strategy
- ADX >= 25 → Trending → Use top-n directional strategy

---

### Q6: Strategy Selection with ADX Filter

**Decision**: Option C - Keep ADX filter in rules.json + dynamic selection

**Rationale**:
- Dynamic selection picks the strategy at 10:00
- ADX < 25 filter in rules.json provides additional safety
- Both layers work together

---

## Configuration Schema

### New File: `dynamic_strategy_rules.json`

```json
{
  "version": "1.0",
  "enabled": true,
  "check_time": "10:00",
  "check_time_buffer_minutes": 5,
  "strategies": {
    "sideways": {
      "strategyId": "sensex_bfo_expiry_day_short_straddle",
      "strategyCode": "s2"
    },
    "trending": {
      "strategyId": "bsensex_bfo_topn_trend", 
      "strategyCode": "s1"
    }
  },
  "condition": {
    "fact": "market.adx",
    "operator": "less_than",
    "value": 25,
    "timeframe": "15m"
  },
  "fallback": {
    "action": "use_default",
    "default_strategy": "s1"
  }
}
```

### Schema Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Config version (for future compatibility) |
| `enabled` | boolean | Yes | Enable/disable dynamic selection |
| `check_time` | string | Yes | Time to evaluate condition (HH:MM) |
| `check_time_buffer_minutes` | int | No | Buffer around check_time (default: 5) |
| `strategies.sideways` | object | Yes | Strategy to use when condition is true |
| `strategies.trending` | object | Yes | Strategy to use when condition is false |
| `condition.fact` | string | Yes | Fact to evaluate (e.g., `market.adx`) |
| `condition.operator` | string | Yes | Operator: `less_than`, `greater_than`, `equals` |
| `condition.value` | number | Yes | Threshold value |
| `condition.timeframe` | string | No | Timeframe for calculation (default: 15m) |
| `fallback.action` | string | No | Action if check fails: `use_default`, `skip`, `error` |
| `fallback.default_strategy` | string | Conditional | Strategy to use on fallback |

---

## CLI Changes

### New Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `--strategyExecution` | string | Mode: `fixed` or `dynamic` (default: `fixed`) |

### Existing Arguments (unchanged)

| Argument | Type | Description |
|----------|------|-------------|
| `--strategyCode` | string | Strategy short code (e.g., `s1`, `m1`) |
| `--strategyId` | string | Full strategy ID |

### Behavior Matrix

| `--strategyExecution` | `--strategyCode` | `--strategyId` | Behavior |
|----------------------|------------------|----------------|---------|
| `fixed` | provided | - | Use fixed strategy from code |
| `fixed` | - | provided | Use fixed strategy from ID |
| `fixed` | provided | provided | Use strategyCode |
| `dynamic` | - | - | Use dynamic_strategy_rules.json |
| `dynamic` | provided | - | **ERROR** |
| `dynamic` | provided | provided | **ERROR** |

---

## Implementation Plan

### Phase 1: Configuration & Schema
- [ ] Create `dynamic_strategy_rules.json` schema
- [ ] Add schema validation
- [ ] Create sample config files per exchange

### Phase 2: Argument Parser Updates
- [ ] Add `--strategyExecution` argument
- [ ] Implement conflict detection
- [ ] Add dynamic mode flow

### Phase 3: Dynamic Strategy Selector
- [ ] Create `DynamicStrategySelector` class
- [ ] Implement ADX evaluation at check_time
- [ ] Implement strategy resolution
- [ ] Add fallback handling

### Phase 4: Integration
- [ ] Integrate with OrbiterApp bootstrap
- [ ] Add logging for strategy selection
- [ ] Update Telegram notifications

### Phase 5: Testing
- [ ] Unit tests for selector logic
- [ ] Integration tests with mock data
- [ ] End-to-end test with simulation

---

## Testing Strategy

### Unit Tests to Create

```python
# test_dynamic_strategy_selector.py
class TestDynamicStrategySelector:
    def test_loads_config_correctly()
    def test_evaluates_adx_condition_less_than()
    def test_evaluates_adx_condition_greater_than()
    def test_resolves_sideways_strategy()
    def test_resolves_trending_strategy()
    def test_fallback_to_default()
    def test_skip_on_failure()
    def test_error_on_invalid_config()
```

### Integration Tests

```python
# test_dynamic_strategy_integration.py
class TestDynamicStrategyIntegration:
    def test_selects_straddle_when_adx_below_threshold()
    def test_selects_topn_when_adx_above_threshold()
    def test_respects_check_time()
    def test_logs_selection_decision()
```

---

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `orbiter/utils/argument_parser.py` | Modify | Add `--strategyExecution` arg |
| `orbiter/config/dynamic_strategy_rules.json` | New | Dynamic rules config |
| `orbiter/utils/dynamic_strategy_selector.py` | New | Selector class |
| `orbiter/core/app.py` | Modify | Integrate selector |
| `tests/unit/test_dynamic_strategy_selector.py` | New | Unit tests |

---

## Backward Compatibility

- Default `strategyExecution=fixed` maintains existing behavior
- Existing `--strategyCode` and `--strategyId` work unchanged
- Only affects users who explicitly enable dynamic mode

---

## Related Documents

- [Architecture Overview](../ARCHITECTURE.md)
- [Rules Engine Documentation](../RULES_ENGINE.md)
- [Testing Guide](./testing.md)

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-02-26 | Initial design document | opencode |
