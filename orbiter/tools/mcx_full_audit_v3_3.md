# MCX Full Audit V3.3 Results

**Date:** 2026-03-18

```
Symbol             | Token    | LTP      | Spread % | ADX    | Status
--------------------------------------------------------------------------------------------
CRUDEOILM19MAR26   | 472790   | 9098.00  | 0.044   % | 43.30  | 🟢 🔥
NATGASMINI26MAR26  | 475112   | 284.50   | 0.035   % | 22.64  | 🟢 💤
SILVERMIC30APR26   | 466029   | 253519.00 | 0.023   % | 36.38  | 🟢 🔥
SILVERM30APR26     | 457533   | 253220.00 | 0.034   % | 33.53  | 🟢 🔥
GOLDPETAL          | -        | -        | -        | -      | ⚪ NOT FOUND
GOLDM03APR26       | 477904   | 153122.00 | 0.015   % | 34.77  | 🟢 🔥
ALUMINI31MAR26     | 487655   | 341.60   | 0.059   % | 27.88  | 🟢 🔥
ZINCMINI31MAR26    | 487663   | 314.60   | 0.048   % | 36.56  | 🟢 🔥
LEADMINI31MAR26    | 487659   | 187.95   | 0.080   % | 11.85  | 🟢 💤
```

## Summary
- **8/9 symbols found** (GOLDPETAL not found)

## Trending (ADX > 25) 🔥
| Symbol | ADX |
|--------|-----|
| CRUDEOILM | 43.30 |
| ZINCMINI | 36.56 |
| SILVERMIC | 36.38 |
| GOLDM | 34.77 |
| SILVERM | 33.53 |
| ALUMINI | 27.88 |

## Choppy (ADX < 25) 💤
| Symbol | ADX |
|--------|-----|
| NATGASMINI | 22.64 |
| LEADMINI | 11.85 |

## Key Improvement
Filtering by `exd` (expiry date) ensures we get proper futures contracts with valid data, not stale system tokens.
