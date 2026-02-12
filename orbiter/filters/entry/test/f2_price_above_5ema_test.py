#!/usr/bin/env python3
"""
🚀 F2_5EMA_SIMPLIFIED TEST - 10 Stocks (ORB-STYLE %pts)
Feb 11, 2026 - LTP vs EMA5 only, NO ratio/clamping
EXACTLY like F1_ORB: Distance_% = (LTP - EMA5) / LTP × 100
"""

def f2_5ema_simple(ltp, ema5, symbol):
    """ORB-STYLE: Direct % distance from EMA5"""
    
    print(f"\n{'='*70}")
    print(f"🔬 F2_5EMA SIMPLE: {symbol}")
    print(f"{'='*70}")
    
    # 1️⃣ DISTANCE RAW
    print(f"1️⃣ LTP  = ₹{ltp:>8,.2f}")
    print(f"   EMA5 = ₹{ema5:>8,.2f}")
    dist_raw = ltp - ema5
    print(f"   dist = {ltp:>8.2f} - {ema5:>8.2f} = **₹{dist_raw:>8.2f}**")
    
    # 2️⃣ DISTANCE % (ORB-STYLE)
    dist_pct = (ltp - ema5) / ltp
    dist_pct_2dp = round(dist_pct * 100, 2)
    print(f"\n2️⃣ dist_pct = {dist_raw:>7.2f} / {ltp:>8.2f} = {dist_pct:>8.4f}")
    print(f"   F2_SCORE = **{dist_pct_2dp:>6.2f}%pts**")
    
    # 3️⃣ DIRECTION
    if ltp > ema5:
        direction = "🟢 BULL"
        print(f"3️⃣ {ltp:>8.2f} > {ema5:>8.2f} → {direction}")
    elif ltp < ema5:
        direction = "🔴 BEAR" 
        print(f"3️⃣ {ltp:>8.2f} < {ema5:>8.2f} → {direction}")
    else:
        direction = "➖ FLAT"
        print(f"3️⃣ {ltp:>8.2f} = {ema5:>8.2f} → {direction}")
    
    print(f"\n✅ FINAL F2_5EMA = **{dist_pct_2dp:>6.2f}pts** {direction}")
    return {
        'symbol': symbol, 'ltp': ltp, 'ema5': ema5, 
        'dist_raw': round(dist_raw, 2), 'f2_score': dist_pct_2dp, 'direction': direction
    }

# LIVE DATA (your console)
stocks = [
    {"symbol": "EICHERMOT", "ltp": 7771.00, "ema5": 7217.51},
    {"symbol": "MAXHEALTH", "ltp": 1055.15, "ema5": 1012.38},
    {"symbol": "APOLLOHOSP", "ltp": 7507.00, "ema5": 7247.13},
    {"symbol": "ETERNAL", "ltp": 300.70, "ema5": 291.53},
    {"symbol": "SBIN", "ltp": 1182.90, "ema5": 1147.48},
    {"symbol": "MARUTI", "ltp": 15412.00, "ema5": 15001.93},
    {"symbol": "TATASTEEL", "ltp": 207.59, "ema5": 202.42},
    {"symbol": "BAJAJ-AUTO", "ltp": 9869.50, "ema5": 9637.42},
    {"symbol": "HCLTECH", "ltp": 1551.60, "ema5": 1590.13},
    {"symbol": "COALINDIA", "ltp": 423.25, "ema5": 432.18},
]

def run_f2_test():
    """Test all 10 stocks"""
    results = []
    
    print("🎯 F2_5EMA SIMPLIFIED TEST (ORB-STYLE %pts)")
    print("=" * 70)
    
    for stock in stocks:
        result = f2_5ema_simple(stock['ltp'], stock['ema5'], stock['symbol'])
        results.append(result)
    
    # SUMMARY TABLE
    print("\n" + "="*90)
    print("📊 F2_5EMA SUMMARY (Ranked by Score)")
    print("-"*89)
    print(f"{'#':<3} {'Symbol':<12} {'LTP':>9} {'EMA5':>9} {'Dist₹':>8} {'F2':>6} {'Status'}")
    print("-"*89)
    
    # RANK + TABLE
    ranked = sorted(results, key=lambda x: x['f2_score'], reverse=True)
    for i, r in enumerate(ranked, 1):
        status = r['direction'][:1]
        star = "⭐" if abs(r['f2_score']) > 3 else ""
        print(f"{i:<3} {r['symbol']:<12} ₹{r['ltp']:>7,.0f} ₹{r['ema5']:>7,.0f} "
              f"₹{r['dist_raw']:>+6.0f} {r['f2_score']:>+6.2f} {status}{star}")

if __name__ == "__main__":
    run_f2_test()
