def evaluate_hybrid_exit(
    side, 
    ltp, 
    ema5_15m, 
    ema9_15m, 
    struct_level, 
    current_pnl_rs, 
    max_pnl_rs, 
    tsl_activation=500, 
    retracement_pct=30
):
    """
    Generic Utility to evaluate the Hybrid Exit Logic.
    
    Parameters:
    - side: 'LONG' or 'SHORT'
    - ltp: Current 1-minute Close price
    - ema5_15m: Latest 15-minute EMA 5 value
    - ema9_15m: Latest 15-minute EMA 9 value
    - struct_level: High/Low of previous two 15m candles
    - current_pnl_rs: Real-time profit/loss in Rupees
    - max_pnl_rs: Peak profit reached during this trade
    - tsl_activation: Profit threshold to activate structural/retracement guards
    - retracement_pct: % drop from peak profit allowed
    
    Returns: (exit_triggered: bool, reason: str)
    """
    
    # 1. 🛡️ 15-Minute Structural Reversal (Trend Change)
    if side == 'LONG' and ema5_15m < ema9_15m:
        return True, f"TREND_REVERSAL: 15m_EMA5({ema5_15m:.2f}) < 15m_EMA9({ema9_15m:.2f})"
    if side == 'SHORT' and ema5_15m > ema9_15m:
        return True, f"TREND_REVERSAL: 15m_EMA5({ema5_15m:.2f}) > 15m_EMA9({ema9_15m:.2f})"

    # 2. 🛡️ 1-Minute Structural TSL (If profit buffer reached)
    if max_pnl_rs >= tsl_activation:
        if side == 'LONG' and ltp < struct_level:
            return True, f"STRUCT_BREAK: LTP({ltp:.2f}) < 15m_Support({struct_level:.2f}) | Peak: Rs {max_pnl_rs:.0f}"
        if side == 'SHORT' and ltp > struct_level:
            return True, f"STRUCT_BREAK: LTP({ltp:.2f}) > 15m_Resistance({struct_level:.2f}) | Peak: Rs {max_pnl_rs:.0f}"

        # 3. 🛡️ 1-Minute Retracement Guard (Profit Protection)
        allowed_pnl = max_pnl_rs * (1 - retracement_pct / 100.0)
        if current_pnl_rs < allowed_pnl:
            return True, f"PROFIT_GUARD: Current(Rs {current_pnl_rs:.0f}) < {100-retracement_pct}% of Peak(Rs {max_pnl_rs:.0f})"

    return False, "HOLD"

# --- TEST CASE: The ICICIBANK Debacle ---
if __name__ == "__main__":
    # Scenaro at 11:51 AM (The point we should have exited)
    print("🧪 Debugging ICICIBANK at 11:51 AM...")
    
    result, reason = evaluate_hybrid_exit(
        side='SHORT',
        ltp=1349.00,
        ema5_15m=1348.6, # Still bearish trend
        ema9_15m=1353.5,
        struct_level=1348.50, # High of previous two 15m candles
        current_pnl_rs=-5320.0,
        max_pnl_rs=980.0,      # Profit hit 980 early on
        tsl_activation=500
    )
    
    print(f"Should Exit? {result}")
    print(f"Reason: {reason}")
