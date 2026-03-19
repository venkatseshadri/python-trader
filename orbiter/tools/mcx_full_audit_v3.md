# MCX Full Audit V3 Results

**Date:** 2026-03-18

**Note:** This version searches with "26" appended which doesn't work well for most symbols.

```
Symbol             | Token    | LTP      | Spread % | ADX    | Status
------------------------------------------------------------------------------------------
CRUDEOILM          | -        | -        | -        | -      | ⚪ NOT FOUND
NATGASMINI26MAR26  | 475112   | 284.30   | 0.070   % | 15.55  | 🟢 💤
SILVERMIC          | -        | -        | -        | -      | ⚪ NOT FOUND
SILVERM26MAR26C101250 | 463245   | NO DATA  | -        | -      | ❌ INACTIVE
GOLDPETAL          | -        | -        | -        | -      | ⚪ NOT FOUND
GOLDM26MAR26C119000 | 554640   | NO DATA  | -        | -      | ❌ INACTIVE
ALUMINI            | -        | -        | -        | -      | ⚪ NOT FOUND
ZINCMINI           | -        | -        | -        | -      | ⚪ NOT FOUND
LEADMINI           | -        | -        | -        | -      | ⚪ NOT FOUND
```

## Issues
- Searching with "26" appended finds option contracts instead of futures
- V2 version works better (searches without "26")

## Recommendation
Use v2 script instead of v3.
