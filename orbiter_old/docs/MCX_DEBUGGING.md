# MCX Orbiter Debugging Guide

## Problem: Scores always 0.00

### Root Cause Analysis (2026-03-04)

**Issue:** Scoring rules not loading for MCX strategy

### Key Files & Paths

1. **Strategy config:** `/home/trading_ceo/python-trader/orbiter/strategies/mcx_trend_follower/`
   - `strategy.json` - Main strategy config
   - `rules.json` - Contains scoring_rules AND strategies
   - `instruments.json` - 8 MCX instruments
   - `filters.json` - 3 filter groups

2. **System rules:** `/home/trading_ceo/python-trader/orbiter/rules/system.json`
   - Contains system lifecycle rules (6 strategies)
   - Also has scoring_rules section (added manually)

3. **Code locations:**
   - `orbiter/core/engine/session/session_manager.py` - Loads strategy bundle
   - `orbiter/core/engine/rule/rule_manager.py` - Loads & compiles rules
   - `orbiter/core/app.py` - Creates main RuleManager (uses system.json)
   - `orbiter/core/engine/runtime/core_engine.py` - Creates its own RuleManager

### Known Issues

1. **Path Bug:** strategy.json had `orbiter/strategies/` prefix causing double path (`orbiter/orbiter/strategies/`)
   - Fixed in session_manager.py to check for `orbiter/` prefix in rel_path

2. **Scoring Rules Not Loading:**
   - System creates TWO RuleManagers:
     - One in app.py (loads system.json) - has scoring rules
     - One in core_engine.py (loads strategy rules.json) - scoring_rules_count=0
   - The core_engine uses ITS OWN RuleManager which doesn't have scoring rules!

### Debug Commands

```bash
# Check scoring rules loaded
grep 'scoring_rules' /tmp/mcx.log

# Check scores
grep 'Score' /tmp/mcx.log

# Check universe
grep 'Universe' /tmp/mcx.log

# Check facts being passed
grep 'FACTS' /tmp/mcx.log

# Full restart
pkill -f main.py; rm -f /home/trading_ceo/python-trader/orbiter/.orbiter.lock
cd /home/trading_ceo/python-trader/orbiter && python3 main.py --paper-trade
```

### Debug Logs Added

1. **rule_manager.py:**
   - `SCORE_EVAL` - When evaluate_score is called
   - `FACTS_IN` - Extra facts passed to scoring
   - `FACTS_COMMON` - Common facts from _get_common_facts
   - `FACTS_AFTER_MERGE` - All facts after merging

2. **core_engine.py:**
   - `SCORING` - When scoring starts for a symbol
   - `SCORED` - After score is calculated

3. **session_manager.py:**
   - `RULES_FILE` - Which rules file is being used

### Scoring Expression

From mcx_trend_follower/rules.json:
```
market_adx * filters_scoring_combined_score_weight_adx + 
(market_ema_fast - market_ema_slow) / market_ema_slow * 100 * filters_scoring_combined_score_weight_ema_slope + 
filter_supertrend_direction_numeric * filters_scoring_combined_score_weight_supertrend
```

### Required Facts

- `market_adx` - ADX indicator value
- `market_ema_fast` - Fast EMA
- `market_ema_slow` - Slow EMA
- `filter_supertrend_direction_numeric` - SuperTrend direction (1 or -1)
- `filters_scoring_combined_score_weight_*` - Filter weights from filters.json
