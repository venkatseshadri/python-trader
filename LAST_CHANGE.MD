# Last Technical Change: v3.12.6 Filter Context Compatibility Fix

**Date:** 2026-02-23
**Status:** COMPLETED (Build: `v3.12.6`)

## 1. Strategic Outcomes
Ensured system-wide compatibility for state-aware filters. This fix allows the new **Ratio Raider** and future intelligent filters to access global engine state without causing execution errors during live trading.

## 2. Technical Adjustments

### A. Filter Signature Refactor (`filters/entry/f1-f11`)
- Updated all entry filter function signatures to use `**kwargs`.
- Standardized parameter extraction (`token`, `weight`, `state`) within each filter.
- This resolves the `TypeError: filter() got an unexpected keyword argument 'state'` observed during the v3.12.5 deployment.

### B. Deployment Integrity
- Verified that `Evaluator` can now safely pass `state` and `token` context to any registered filter.

## 3. Mission Status
- **Goal Status:** **Filter Architecture Stabilized.**
- **RPi Environment:** Deploying fix to resume MCX session observation.
- **Next Step:** Confirm stable initialization and observe Ratio Raider signals on Gold/Silver.
