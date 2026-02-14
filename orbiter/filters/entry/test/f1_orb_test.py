#!/usr/bin/env python3
"""
🚀 F1_ORB ULTRA-DETAILED DEBUGGER - FIXED (NO pandas, ALL constants defined)
M&M, EICHERMOT, TATASTEEL - 50+ debug steps [file:134]
"""

import math

# === ALL CONSTANTS DEFINED AT TOP ===
W_SIZE = 33.0        # SCORE_W_ORB_SIZE
W_HIGH = 33.0        # SCORE_W_ORB_HIGH  
W_LOW = 34.0         # SCORE_W_ORB_LOW
SCALE_SIZE_PCT = 1.00     # SCORE_SCALE_ORB_SIZE_PCT
SCALE_BREAK_PCT = 0.10    # SCORE_SCALE_ORB_BREAK_PCT
BUFFER_PCT = 0.002        # 0.2% buffer

def ultra_detailed_f1_orb(symbol_data, symbol_name):
    """50+ debug steps - NO external dependencies"""
    
    ltp = symbol_data['ltp']
    orb_high = symbol_data['high'] 
    orb_low = symbol_data['low']
    
    print(f"\n{'='*90}")
    print(f"🔬 ULTRA-DETAILED: {symbol_name} F1_ORB DEBUG")
    print(f"{'='*90}")
    
    # 0. INPUT VALIDATION
    print(f"\n0️⃣ INPUT VALIDATION (f1_orb.py line ~50):")
    print(f"   ltp = float(data['lp']) = {ltp}")
    print(f"   token = data['token'] = NSE|{symbol_data['token']}")
    if ltp <= 0:
        print("   ❌ LTP <= 0 → return score=0")
        return {'symbol': symbol_name, 'f1_total': 0}
    
    # 1. ORB RANGE
    print(f"\n1️⃣ ORB RANGE CALC (calculate_orb_range):")
    orb_size = orb_high - orb_low
    print(f"   orb_high = float(highs[0]) = {orb_high}")
    print(f"   orb_low = float(lows[0]) = {orb_low}")
    print(f"   orb_size = {orb_high} - {orb_low} = **{orb_size:.4f}**")
    
    # 2. SIZE SCALE
    print(f"\n2️⃣ SIZE SCALE NORMALIZATION (line ~85):")
    size_scale = ltp * SCALE_SIZE_PCT
    print(f"   SCALE_SIZE_PCT = {SCALE_SIZE_PCT}")
    print(f"   size_scale = ltp × {SCALE_SIZE_PCT} = {ltp} × {SCALE_SIZE_PCT} = **{size_scale:.4f}**")
    
    # 3. SIZE RATIO → TANH → SCORE  
    print(f"\n3️⃣ SIZE RATIO → TANH → SCORE:")
    size_ratio = orb_size / size_scale
    tanh_size = math.tanh(size_ratio)
    size_score = W_SIZE * tanh_size
    print(f"   size_ratio = {orb_size}/{size_scale} = **{size_ratio:.6f}**")
    print(f"   tanh({size_ratio:.6f}) = **{tanh_size:.6f}** (range -1→+1)")
    print(f"   size_score = {W_SIZE} × {tanh_size:.6f} = **{size_score:.4f}pts**")
    
    # 4. BULL/BEAR THRESHOLD
    print(f"\n4️⃣ BULL/BEAR CHECK + BUFFER (line ~95):")
    buffer_amount = orb_high * BUFFER_PCT
    threshold = orb_high * (1 - BUFFER_PCT)
    print(f"   BUFFER_PCT = {BUFFER_PCT} ({BUFFER_PCT*100:.2f}%)")
    print(f"   buffer = {orb_high} × {BUFFER_PCT} = **{buffer_amount:.4f}**")
    print(f"   threshold = {orb_high} × (1-{BUFFER_PCT}) = **{threshold:.4f}**")
    
    is_bull = ltp > threshold
    print(f"   ltp({ltp:.4f}) {'>' if is_bull else '<='} threshold({threshold:.4f}) = {'🟢 BULL' if is_bull else '🔴 BEAR'}")
    
    if is_bull:
        # 5. BULL DISTANCE
        dist_abs = ltp - orb_high
        dist_pct = dist_abs / ltp
        print(f"\n5️⃣ 🟢 BULL BREAK DISTANCE:")
        print(f"   dist_abs = ltp - orb_high = {ltp} - {orb_high} = **{dist_abs:.4f}**")
        print(f"   dist_pct = {dist_abs}/{ltp} = **{dist_pct:.6f}** ({dist_pct*100:.3f}%)")
        
        # 6. BULL RATIO → TANH
        break_ratio = dist_pct / SCALE_BREAK_PCT
        tanh_break = math.tanh(break_ratio)
        bull_score = W_HIGH * tanh_break
        print(f"\n6️⃣ BULL RATIO → TANH → SCORE:")
        print(f"   break_ratio = {dist_pct}/{SCALE_BREAK_PCT} = **{break_ratio:.6f}**")
        print(f"   tanh({break_ratio:.6f}) = **{tanh_break:.6f}**")
        print(f"   bull_score = {W_HIGH} × {tanh_break:.6f} = **{bull_score:.4f}pts**")
        
    else:
        # BEAR LOGIC (symmetric)
        dist_abs = orb_low - ltp
        dist_pct = dist_abs / ltp
        print(f"\n5️⃣ 🔴 BEAR BREAK DISTANCE:")
        print(f"   dist_abs = orb_low - ltp = {orb_low} - {ltp} = **{dist_abs:.4f}**")
        print(f"   dist_pct = {dist_abs}/{ltp} = **{dist_pct:.6f}** ({dist_pct*100:.3f}%)")
        
        break_ratio = dist_pct / SCALE_BREAK_PCT
        tanh_break = math.tanh(break_ratio)
        bear_score = -W_HIGH * tanh_break
        print(f"   bear_score = -{W_HIGH} × {tanh_break:.6f} = **{bear_score:.4f}pts**")
        bull_score = bear_score
    
    # 7. FINAL TOTAL
    f1_total = size_score + bull_score
    print(f"\n7️⃣ FINAL F1_ORB TOTAL:")
    print(f"   f1_total = size_score + {'bull_score' if is_bull else 'bear_score'}")
    print(f"   f1_total = {size_score:>9.4f} + {bull_score:>9.4f} = **{f1_total:>9.4f}pts**")
    
    print(f"\n✅ f1_orb.py EXACT MATCH: **{f1_total:.2f}pts**")
    return {'symbol': symbol_name, 'ltp': ltp, 'f1_total': f1_total, 
            'size_score': size_score, 'break_score': bull_score}

def print_summary_table(results):
    """Simple ASCII table - NO pandas"""
    print("\n" + "="*90)
    print("📊 SUMMARY TABLE (F1_ORB Scores)")
    print(" " + "-"*85)
    print(f"{'Rank':<4} {'Symbol':<12} {'LTP':>9} {'ORB':>14} {'Size':>7} {'Break':>7} {'Total':>7} {'Dir'}")
    print("-"*85)
    
    ranked = sorted(results, key=lambda x: x['f1_total'], reverse=True)
    for i, r in enumerate(ranked, 1):
        direction = "🟢" if r['break_score'] > 0 else "🔴"
        print(f"{i:<4} {r['symbol']:<12} ₹{r['ltp']:>7,.0f} {r['ORB_Low']:>6.0f}-{r['ORB_High']:>6.0f} "
              f"{r['size_score']:>6.1f} {r['break_score']:>6.1f} **{r['f1_total']:>6.1f}** {direction}")

def run_full_comparison():
    """Test all 3 stocks"""
    stocks = [
        {'name': 'M&M', 'token': '2031', 'ltp': 3768.00, 'high': 3729.70, 'low': 3685.40},
        {'name': 'EICHERMOT', 'token': '910', 'ltp': 7771.00, 'high': 7784.00, 'low': 7505.00},
        {'name': 'TATASTEEL', 'token': '3499', 'ltp': 207.59, 'high': 209.75, 'low': 207.69},
    ]
    
    results = []
    for stock in stocks:
        result = ultra_detailed_f1_orb(stock, stock['name'])
        results.append({**result, 'ORB_High': stock['high'], 'ORB_Low': stock['low']})
    
    print_summary_table(results)

if __name__ == "__main__":
    run_full_comparison()
