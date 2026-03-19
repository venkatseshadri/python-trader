# Gold Only Audit Results

**Date:** 2026-03-18

## All Gold Contracts Found

```
Trading Symbol       | Token ID   | Expiry
--------------------------------------------------
GOLD02APR26          | 454818     | 02-APR-2026
GOLD05AUG26          | 466583     | 05-AUG-2026
GOLD05JUN26          | 459277     | 05-JUN-2026
GOLDGUINEA29MAY26    | 488785     | 29-MAY-2026
GOLDGUINEA30APR26    | 487664     | 30-APR-2026
GOLDGUINEA30JUN26    | 510465     | 30-JUN-2026
GOLDGUINEA31AUG26    | 562055     | 31-AUG-2026
GOLDGUINEA31JUL26    | 552720     | 31-JUL-2026
GOLDGUINEA31MAR26    | 477174     | 31-MAR-2026
GOLDM03APR26         | 477904     | 03-APR-2026
GOLDM03JUL26         | 510764     | 03-JUL-2026
GOLDM05AUG26         | 555922     | 05-AUG-2026
GOLDM05JUN26         | 491727     | 05-JUN-2026
GOLDM05MAY26         | 487819     | 05-MAY-2026
GOLDTEN29MAY26       | 488787     | 29-MAY-2026
GOLDTEN30APR26       | 487666     | 30-APR-2026
GOLDTEN30JUN26       | 510463     | 30-JUN-2026
GOLDTEN31JUL26       | 552722     | 31-JUL-2026
GOLDTEN31MAR26       | 477176     | 31-MAR-2026
```

## ADX Audit (GOLDM, GOLDGUINEA)

```
Symbol               | LTP        | ADX    | Status
--------------------------------------------------
GOLDGUINEA29MAY26    | 129416.00  | 38.06  | 🔥
GOLDGUINEA30APR26    | 127371.00  | 43.51  | 🔥
GOLDGUINEA30JUN26    | 131720.00  | 39.90  | 🔥
GOLDGUINEA31AUG26    | 135300.00  | 43.82  | 🔥
GOLDGUINEA31JUL26    | 133271.00  | 38.75  | 🔥
GOLDGUINEA31MAR26    | 125172.00  | 45.86  | 🔥
GOLDM03APR26         | 153050.00  | 36.47  | 🔥
GOLDM03JUL26         | 159980.00  | 44.18  | 🔥
GOLDM05AUG26         | 162392.00  | 36.71  | 🔥
GOLDM05JUN26         | 157442.00  | 37.85  | 🔥
GOLDM05MAY26         | 155364.00  | 43.13  | 🔥
```

## Key Finding

**GOLDPETAL is NOT available in the broker API!**

The broker has:
- GOLDM (Mini Gold) - 1 lot = 100g
- GOLDGUINEA (Gold Guinea) - 1 lot = 1g
- GOLDTEN (Gold Ten) - 1 lot = 10g
- But NOT GOLDPETAL (Gold Petal) - which was supposed to be 1g

This explains why GOLDPETAL is never found - it doesn't exist in the Shoonya/MCX instrument list.
