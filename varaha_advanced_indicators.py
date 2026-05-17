"""
Varaha Advanced Indicators Module
==================================

Comprehensive research indicators for multi-strategy trading:
1. IV Rank / IV Term Structure (volatility regime)
2. Historical Volatility (HV-20, HV-60)
3. Greeks by expiry (delta, gamma, vega, theta)
4. Multi-day pivot clusters (support/resistance)
5. Session phase detection (early/mid/late)
6. Put-Call Ratio (market sentiment)
7. Open Interest analysis by strike

Usage:
  In data_capture_v3_duckdb.py:

  from varaha_advanced_indicators import compute_advanced_indicators

  # In capture_once(), after SMC calculation:
  advanced = compute_advanced_indicators(
    db, ds, timestamp, date_str, spot,
    buf, prev_day_data, atm_strike, indices_vix
  )
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
import numpy as np


# ============================================================================
# SECTION 1: IV RANK & IV TERM STRUCTURE
# ============================================================================


def compute_iv_rank(db, index: str, current_vix: Optional[float]) -> Dict:
    """
    Calculate IV Rank (percentile of current IV vs 252-day history).

    IV Rank = (Current IV - 52w Low) / (52w High - 52w Low) * 100

    Returns:
        {
            'iv_current': float,
            'iv_52w_high': float,
            'iv_52w_low': float,
            'iv_rank': float (0-100),
            'iv_regime': str ('low' | 'mid' | 'high')
        }
    """
    if not current_vix or current_vix <= 0:
        return {
            "iv_current": None,
            "iv_52w_high": None,
            "iv_52w_low": None,
            "iv_rank": None,
            "iv_regime": None,
        }

    try:
        # Get 252-day IV history from DuckDB
        cutoff_date = datetime.now().date() - timedelta(days=252)
        rows = db.execute(f"""
            SELECT india_vix
            FROM market_data
            WHERE date >= '{cutoff_date}'
              AND index_name = '{index}'
              AND india_vix IS NOT NULL
            ORDER BY timestamp
        """).fetchall()

        if not rows or len(rows) < 10:
            return {
                "iv_current": current_vix,
                "iv_52w_high": None,
                "iv_52w_low": None,
                "iv_rank": None,
                "iv_regime": None,
            }

        vix_values = [r[0] for r in rows]
        vix_high = max(vix_values)
        vix_low = min(vix_values)

        # Calculate IV Rank
        if vix_high == vix_low:
            iv_rank = 50.0
        else:
            iv_rank = ((current_vix - vix_low) / (vix_high - vix_low)) * 100
            iv_rank = max(0, min(100, iv_rank))  # Clamp to 0-100

        # Determine regime
        if iv_rank < 33:
            regime = "low"
        elif iv_rank < 67:
            regime = "mid"
        else:
            regime = "high"

        return {
            "iv_current": round(current_vix, 2),
            "iv_52w_high": round(vix_high, 2),
            "iv_52w_low": round(vix_low, 2),
            "iv_rank": round(iv_rank, 1),
            "iv_regime": regime,
        }
    except Exception:
        return {
            "iv_current": current_vix,
            "iv_52w_high": None,
            "iv_52w_low": None,
            "iv_rank": None,
            "iv_regime": None,
        }


def compute_iv_term_structure(
    db, index: str, expiry_weekly: str, expiry_monthly: str
) -> Dict:
    """
    IV term structure: compare short-term vs long-term IV.

    Used to detect volatility slope (contango vs backwardation).
    """
    try:
        # Get avg IV for each expiry from option snapshots
        weekly_iv = db.execute(f"""
            SELECT AVG(iv) FROM option_snapshots
            WHERE expiry_date = '{expiry_weekly}'
              AND option_type = 'CE'
              AND iv IS NOT NULL
        """).fetchone()[0]

        monthly_iv = db.execute(f"""
            SELECT AVG(iv) FROM option_snapshots
            WHERE expiry_date = '{expiry_monthly}'
              AND option_type = 'CE'
              AND iv IS NOT NULL
        """).fetchone()[0]

        if not weekly_iv or not monthly_iv:
            return {"iv_short": None, "iv_long": None, "iv_slope": None}

        # IV slope: positive = contango (normal), negative = backwardation
        slope = monthly_iv - weekly_iv

        return {
            "iv_short": round(weekly_iv, 2),
            "iv_long": round(monthly_iv, 2),
            "iv_slope": round(slope, 2),
        }
    except Exception:
        return {"iv_short": None, "iv_long": None, "iv_slope": None}


# ============================================================================
# SECTION 2: HISTORICAL VOLATILITY
# ============================================================================


def compute_historical_volatility(buf: "IndicatorBuffer") -> Dict:
    """
    Calculate historical volatility (annualized std dev of log returns).
    HV-20: 20-day rolling
    HV-60: 60-day rolling (from database)
    """
    result = {"hv_20": None, "hv_60": None}

    if len(buf.buf) < 5:
        return result

    try:
        closes = [b["close"] for b in list(buf.buf)[-min(100, len(buf.buf)) :]]

        if len(closes) < 2:
            return result

        # Log returns
        log_returns = [
            math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))
        ]

        # HV-20 (if we have 20+ bars)
        if len(log_returns) >= 20:
            hv_20_std = np.std(log_returns[-20:])
            result["hv_20"] = round(hv_20_std * math.sqrt(252) * 100, 2)

        # HV-60 (if we have 60+ bars)
        if len(log_returns) >= 60:
            hv_60_std = np.std(log_returns[-60:])
            result["hv_60"] = round(hv_60_std * math.sqrt(252) * 100, 2)
        elif len(log_returns) >= 20:
            hv_60_std = np.std(log_returns)
            result["hv_60"] = round(hv_60_std * math.sqrt(252) * 100, 2)

        return result
    except Exception:
        return result


# ============================================================================
# SECTION 3: GREEKS CALCULATION (Black-Scholes)
# ============================================================================


def _black_scholes_greeks(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "C"
) -> Dict:
    """
    Calculate Greeks using Black-Scholes model.

    Args:
        S: Spot price
        K: Strike price
        T: Time to expiry (years)
        r: Risk-free rate (0.06 for 6%)
        sigma: Implied volatility (as decimal, e.g. 0.25 for 25%)
        option_type: 'C' for call, 'P' for put

    Returns:
        {'delta': float, 'gamma': float, 'vega': float, 'theta': float}
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {"delta": 0, "gamma": 0, "vega": 0, "theta": 0}

    try:
        from scipy.stats import norm

        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)

        nd1 = norm.pdf(d1)
        Nd1 = norm.cdf(d1)
        Nd2 = norm.cdf(d2)

        if option_type == "C":
            delta = Nd1
            theta = (
                -S * nd1 * sigma / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * Nd2
            ) / 365
        else:  # Put
            delta = Nd1 - 1
            theta = (
                -S * nd1 * sigma / (2 * math.sqrt(T))
                + r * K * math.exp(-r * T) * (1 - Nd2)
            ) / 365

        gamma = nd1 / (S * sigma * math.sqrt(T))
        vega = S * nd1 * math.sqrt(T) / 100  # Per 1% IV change

        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "vega": round(vega, 4),
            "theta": round(theta, 4),
        }
    except ImportError:
        # Fallback if scipy not available
        return {"delta": 0, "gamma": 0, "vega": 0, "theta": 0}
    except Exception:
        return {"delta": 0, "gamma": 0, "vega": 0, "theta": 0}


def compute_aggregate_greeks(
    db, spot: float, expiry: str, atm_strike: int, vix: Optional[float]
) -> Dict:
    """
    Calculate aggregate Greeks for iron fly wings (5 OTM calls, 5 OTM puts).

    Returns:
        {
            'agg_delta': float,      # Net directional exposure
            'agg_gamma': float,      # Curvature risk (negative for short)
            'agg_vega': float,       # IV sensitivity (negative for short)
            'agg_theta': float,      # Time decay (positive for short)
            'wings_delta': float,    # Wings delta (hedge)
            'body_delta': float      # Body (ATM straddle) delta
        }
    """
    if not vix or vix <= 0:
        return {
            "agg_delta": None,
            "agg_gamma": None,
            "agg_vega": None,
            "agg_theta": None,
            "wings_delta": None,
            "body_delta": None,
        }

    try:
        r = 0.06  # 6% risk-free rate
        sigma = vix / 100  # Convert VIX to decimal

        # Days to expiry (format: '05-MAY-2026')
        exp_date = datetime.strptime(expiry, "%d-%b-%Y").date()
        days_to_exp = (exp_date - datetime.now().date()).days
        T = days_to_exp / 365 if days_to_exp > 0 else 0.001

        wings_delta = 0
        wings_gamma = 0
        wings_vega = 0
        wings_theta = 0

        # Iron fly wings: +5 OTM calls, +5 OTM puts (long hedge)
        step = 50
        for i in range(1, 6):
            # Long OTM call
            call_strike = atm_strike + (i * step)
            call_greeks = _black_scholes_greeks(spot, call_strike, T, r, sigma, "C")
            wings_delta += call_greeks["delta"]
            wings_gamma += call_greeks["gamma"]
            wings_vega += call_greeks["vega"]
            wings_theta += call_greeks["theta"]

            # Long OTM put
            put_strike = atm_strike - (i * step)
            put_greeks = _black_scholes_greeks(spot, put_strike, T, r, sigma, "P")
            wings_delta += put_greeks["delta"]
            wings_gamma += put_greeks["gamma"]
            wings_vega += put_greeks["vega"]
            wings_theta += put_greeks["theta"]

        # Body: short ATM straddle (short call + short put)
        atm_call = _black_scholes_greeks(spot, atm_strike, T, r, sigma, "C")
        atm_put = _black_scholes_greeks(spot, atm_strike, T, r, sigma, "P")

        body_delta = -(atm_call["delta"] + atm_put["delta"])
        body_gamma = -(atm_call["gamma"] + atm_put["gamma"])
        body_vega = -(atm_call["vega"] + atm_put["vega"])
        body_theta = -(atm_call["theta"] + atm_put["theta"])

        # Aggregate (wings long + body short)
        agg_delta = wings_delta + body_delta
        agg_gamma = wings_gamma + body_gamma
        agg_vega = wings_vega + body_vega
        agg_theta = wings_theta + body_theta

        return {
            "agg_delta": round(agg_delta, 4),
            "agg_gamma": round(agg_gamma, 6),
            "agg_vega": round(agg_vega, 4),
            "agg_theta": round(agg_theta, 4),
            "wings_delta": round(wings_delta, 4),
            "body_delta": round(body_delta, 4),
        }
    except Exception:
        return {
            "agg_delta": None,
            "agg_gamma": None,
            "agg_vega": None,
            "agg_theta": None,
            "wings_delta": None,
            "body_delta": None,
        }


# ============================================================================
# SECTION 4: MULTI-DAY PIVOT CLUSTERS
# ============================================================================


def compute_pivot_clusters(db, index: str) -> Dict:
    """
    Find support/resistance clusters from last 5 days of pivot points.

    Clusters are levels where 2+ daily pivots are within 1 ATR of each other.
    """
    try:
        # Get last 5 days of pivot data
        rows = db.execute(f"""
            SELECT date, spot, pivot_pp, pivot_r1, pivot_r2, pivot_s1, pivot_s2, atr
            FROM market_data
            WHERE index_name = '{index}'
              AND pivot_pp IS NOT NULL
              AND CAST(date AS DATE) >= DATE(CURRENT_DATE - INTERVAL 5 DAY)
            ORDER BY date DESC
            LIMIT 1440
        """).fetchall()

        if not rows or len(rows) < 5:
            return {
                "cluster_support": None,
                "cluster_resistance": None,
                "distance_to_support": None,
                "distance_to_resistance": None,
            }

        # Collect all pivot levels
        levels = []
        atr = rows[0][7] if rows[0][7] else 100

        for row in rows:
            if row[2]:  # pivot_pp
                levels.append(row[2])
            if row[3]:  # pivot_r1
                levels.append(row[3])
            if row[5]:  # pivot_s1
                levels.append(row[5])

        if not levels:
            return {
                "cluster_support": None,
                "cluster_resistance": None,
                "distance_to_support": None,
                "distance_to_resistance": None,
            }

        levels.sort()

        # Find clusters (2+ levels within 1 ATR)
        clusters = []
        current_cluster = [levels[0]]

        for i in range(1, len(levels)):
            if abs(levels[i] - current_cluster[-1]) <= atr:
                current_cluster.append(levels[i])
            else:
                if len(current_cluster) >= 2:
                    clusters.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [levels[i]]

        if len(current_cluster) >= 2:
            clusters.append(sum(current_cluster) / len(current_cluster))

        current_spot = rows[0][1]  # Latest actual spot price

        # Find nearest support and resistance
        support = [c for c in clusters if c < current_spot]
        resistance = [c for c in clusters if c > current_spot]

        nearest_support = max(support) if support else None
        nearest_resistance = min(resistance) if resistance else None

        return {
            "cluster_support": round(nearest_support, 2) if nearest_support else None,
            "cluster_resistance": round(nearest_resistance, 2)
            if nearest_resistance
            else None,
            "distance_to_support": round(current_spot - nearest_support, 2)
            if nearest_support
            else None,
            "distance_to_resistance": round(nearest_resistance - current_spot, 2)
            if nearest_resistance
            else None,
        }
    except Exception:
        return {
            "cluster_support": None,
            "cluster_resistance": None,
            "distance_to_support": None,
            "distance_to_resistance": None,
        }


# ============================================================================
# SECTION 5: SESSION PHASE & MARKET STRUCTURE
# ============================================================================


def compute_session_metrics(
    spot: float,
    open_price: Optional[float],
    prev_close: Optional[float],
    atm_strike: Optional[int],
    pivot_pp: Optional[float],
    pivot_r1: Optional[float],
    pivot_s1: Optional[float],
) -> Dict:
    """
    Detect session phase (early/mid/late) and proximity to key levels.
    """
    now = datetime.now()
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

    # Session phase based on time
    if now < market_open:
        phase = "pre"
    elif now < market_open + timedelta(minutes=90):
        phase = "early"
    elif now > market_close - timedelta(minutes=60):
        phase = "late"
    else:
        phase = "mid"

    # Distance to levels (for breakout detection)
    dist_to_pivot = None
    dist_to_r1 = None
    dist_to_s1 = None

    if spot and pivot_pp:
        dist_to_pivot = round(((spot - pivot_pp) / pivot_pp) * 100, 3)  # %
    if spot and pivot_r1:
        dist_to_r1 = round(((spot - pivot_r1) / pivot_r1) * 100, 3)
    if spot and pivot_s1:
        dist_to_s1 = round(((spot - pivot_s1) / pivot_s1) * 100, 3)

    # Open-to-current range %
    open_to_current_pct = None
    if spot and open_price and open_price > 0:
        open_to_current_pct = round(((spot - open_price) / open_price) * 100, 3)

    return {
        "session_phase": phase,
        "open_to_current_pct": open_to_current_pct,
        "distance_to_pivot_pct": dist_to_pivot,
        "distance_to_r1_pct": dist_to_r1,
        "distance_to_s1_pct": dist_to_s1,
    }


# ============================================================================
# SECTION 6: PUT-CALL RATIO (SENTIMENT)
# ============================================================================


def compute_pcr(db, expiry: str, atm_strike: int) -> Dict:
    """
    Put-Call Ratio for sentiment analysis.

    PCR > 1.0 = bearish (more puts open), PCR < 0.8 = bullish (more calls open)
    """
    try:
        # Get total OI for calls and puts
        calls_oi = db.execute(f"""
            SELECT SUM(oi) FROM option_snapshots
            WHERE expiry_date = '{expiry}'
              AND option_type = 'CE'
              AND oi IS NOT NULL
        """).fetchone()[0]

        puts_oi = db.execute(f"""
            SELECT SUM(oi) FROM option_snapshots
            WHERE expiry_date = '{expiry}'
              AND option_type = 'PE'
              AND oi IS NOT NULL
        """).fetchone()[0]

        if not calls_oi or calls_oi <= 0 or not puts_oi:
            return {"pcr_total": None, "pcr_atm": None, "sentiment": None}

        # Total PCR
        pcr_total = puts_oi / calls_oi

        # ATM PCR (±2 strikes around ATM)
        step = 50
        atm_strikes = [atm_strike - step, atm_strike, atm_strike + step]

        atm_calls_oi = db.execute(f"""
            SELECT SUM(oi) FROM option_snapshots
            WHERE expiry_date = '{expiry}'
              AND option_type = 'CE'
              AND strike IN ({",".join(map(str, atm_strikes))})
              AND oi IS NOT NULL
        """).fetchone()[0]

        atm_puts_oi = db.execute(f"""
            SELECT SUM(oi) FROM option_snapshots
            WHERE expiry_date = '{expiry}'
              AND option_type = 'PE'
              AND strike IN ({",".join(map(str, atm_strikes))})
              AND oi IS NOT NULL
        """).fetchone()[0]

        pcr_atm = None
        if atm_calls_oi and atm_calls_oi > 0 and atm_puts_oi:
            pcr_atm = atm_puts_oi / atm_calls_oi

        # Sentiment
        if pcr_total > 1.0:
            sentiment = "bearish"
        elif pcr_total > 0.8:
            sentiment = "neutral"
        else:
            sentiment = "bullish"

        return {
            "pcr_total": round(pcr_total, 3),
            "pcr_atm": round(pcr_atm, 3) if pcr_atm else None,
            "sentiment": sentiment,
        }
    except Exception:
        return {"pcr_total": None, "pcr_atm": None, "sentiment": None}


# ============================================================================
# SECTION 7: OPEN INTEREST ANALYSIS
# ============================================================================


def compute_oi_analysis(db, expiry: str, atm_strike: int) -> Dict:
    """
    OI-weighted strike analysis and gamma zones.
    """
    try:
        step = 50

        # Get OI distribution around ATM
        rows = db.execute(f"""
            SELECT strike, option_type, SUM(oi) as total_oi
            FROM option_snapshots
            WHERE expiry_date = '{expiry}'
              AND oi IS NOT NULL
              AND ABS(strike - {atm_strike}) <= 250
            GROUP BY strike, option_type
            ORDER BY strike
        """).fetchall()

        if not rows:
            return {
                "max_pain_strike": None,
                "call_oi_concentration": None,
                "put_oi_concentration": None,
                "oi_skew": None,
            }

        # Find max OI level (max pain)
        max_oi = 0
        max_oi_strike = atm_strike

        for strike in range(atm_strike - 250, atm_strike + 251, step):
            total_oi = sum(r[2] for r in rows if r[0] == strike)
            if total_oi > max_oi:
                max_oi = total_oi
                max_oi_strike = strike

        # Call vs Put OI concentration
        total_call_oi = sum(r[2] for r in rows if r[1] == "CE")
        total_put_oi = sum(r[2] for r in rows if r[1] == "PE")

        call_concentration = None
        put_concentration = None

        if total_call_oi > 0 or total_put_oi > 0:
            total = total_call_oi + total_put_oi
            if total > 0:
                call_concentration = round((total_call_oi / total) * 100, 1)
                put_concentration = round((total_put_oi / total) * 100, 1)

        oi_skew = None
        if total_call_oi > 0:
            oi_skew = round((total_put_oi / total_call_oi), 2)

        return {
            "max_pain_strike": max_oi_strike,
            "call_oi_concentration": call_concentration,
            "put_oi_concentration": put_concentration,
            "oi_skew": oi_skew,
        }
    except Exception:
        return {
            "max_pain_strike": None,
            "call_oi_concentration": None,
            "put_oi_concentration": None,
            "oi_skew": None,
        }


# ============================================================================
# MAIN FUNCTION: COMPUTE ALL ADVANCED INDICATORS
# ============================================================================


def compute_advanced_indicators(
    db,
    ds,
    timestamp: str,
    date_str: str,
    spot: Optional[float],
    buf,
    prev_day_data: Optional[Dict],
    atm_strike: Optional[int],
    india_vix: Optional[float],
    open_price: Optional[float],
    pivot_pp: Optional[float],
    pivot_r1: Optional[float],
    pivot_s1: Optional[float],
    expiry_weekly: Optional[str],
    expiry_monthly: Optional[str],
    index: str = "NIFTY",
) -> Dict:
    """
    Compute all advanced research indicators in one call.

    Returns dictionary with all computed metrics ready for database insertion.
    """
    result = {}

    # 1. IV Rank
    iv_rank_data = compute_iv_rank(db, index, india_vix)
    result.update(iv_rank_data)

    # 2. IV Term Structure
    if expiry_weekly and expiry_monthly:
        iv_term = compute_iv_term_structure(db, index, expiry_weekly, expiry_monthly)
        result.update(iv_term)
    else:
        result.update({"iv_short": None, "iv_long": None, "iv_slope": None})

    # 3. Historical Volatility
    hv_data = compute_historical_volatility(buf)
    result.update(hv_data)

    # 4. Greeks (for weekly expiry)
    if expiry_weekly and spot and atm_strike and india_vix:
        greeks = compute_aggregate_greeks(
            db, spot, expiry_weekly, atm_strike, india_vix
        )
        result.update(greeks)
    else:
        result.update(
            {
                "agg_delta": None,
                "agg_gamma": None,
                "agg_vega": None,
                "agg_theta": None,
                "wings_delta": None,
                "body_delta": None,
            }
        )

    # 5. Multi-day Pivot Clusters
    clusters = compute_pivot_clusters(db, index)
    result.update(clusters)

    # 6. Session Metrics
    session = compute_session_metrics(
        spot,
        open_price,
        prev_day_data.get("close") if prev_day_data else None,
        atm_strike,
        pivot_pp,
        pivot_r1,
        pivot_s1,
    )
    result.update(session)

    # 7. PCR (for weekly expiry)
    if expiry_weekly and atm_strike:
        pcr = compute_pcr(db, expiry_weekly, atm_strike)
        result.update(pcr)
    else:
        result.update({"pcr_total": None, "pcr_atm": None, "sentiment": None})

    # 8. OI Analysis (for weekly expiry)
    if expiry_weekly and atm_strike:
        oi = compute_oi_analysis(db, expiry_weekly, atm_strike)
        result.update(oi)
    else:
        result.update(
            {
                "max_pain_strike": None,
                "call_oi_concentration": None,
                "put_oi_concentration": None,
                "oi_skew": None,
            }
        )

    return result
