# ⚡ Research Design: Score Velocity (The Momentum Trend)

**Date:** 2026-02-20  
**Status:** Tracking Active (Commit `aefb075`)  
**Objective:** Differentiate between "Fading Peaks" and "Building Momentum" by tracking the delta between morning baseline and current signal strength.

---

## 1. The Concept: "The Score delta"
A static score threshold (e.g., > 0.5) is a binary gate. However, the **direction** of the score is a leading indicator of trend health.

| Scenario | Score | Trend | Verdict |
| :--- | :--- | :--- | :--- |
| **A: The Runner** | 1.25 | **+0.20** | Momentum is building. Volume is likely increasing. |
| **B: The Fader** | 1.25 | **-0.30** | Momentum is dying. Institutional support is withdrawing. |

---

## 2. Technical Implementation
1.  **Opening Snap:** Capture the first non-zero score (`abs(score) > 0.1`) as the daily baseline.
2.  **Velocity Calculation:** `Velocity = Current_Score - Opening_Score`.
3.  **Persistent Storage:** baseline is saved in `session_state.json['opening_scores']`.

---

## 3. Future Filter Application (Hypothesis)
We can implement a **"Velocity Guard"**:
- **Law:** Block entries if `Velocity < -0.20`, even if the total score is still above the threshold.
- **Reasoning:** Avoids buying the "tail end" of a move where the bot is the last one to the party.

---

## 4. Current Log Format
`🔍 Evaluated 50 symbols. Top Signal: [SYMBOL] Score: [CURRENT] ([DELTA])`
