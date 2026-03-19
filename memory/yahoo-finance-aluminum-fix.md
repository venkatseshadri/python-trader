# Yahoo Finance Aluminum Fix

## Issue
Aluminum commodity data was not fetching correctly using the old Yahoo Finance ticker `ALU=F`.

## Solution
Changed the Yahoo Finance ticker from `ALU=F` to `ALI=F` in the MCX symbol mappings.

## File Changed
- `orbiter/core/engine/rule/fact_calculator.py`

## Change Details
```python
# Before:
'ALUMINIUM': 'ALU=F',
'ALUMINI': 'ALU=F',

# After:
'ALUMINIUM': 'ALI=F',
'ALUMINI': 'ALI=F',
```

## Test
Verify Aluminum data fetches correctly with ALI=F ticker.
