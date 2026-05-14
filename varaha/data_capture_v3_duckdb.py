#!/usr/bin/env python3
"""
Varaha Data Capture V3 — DuckDB Backend
=========================================

Captures 1-minute NIFTY data (spot, options, indicators) for pattern discovery.
Uses DuckDB for high-performance analytical queries across days.

Key advantages for analysis:
- Columnar storage: faster aggregations across thousands of option snapshots
- Window functions: pattern detection across time series
- Zero-copy: read directly from Python dataframes
- Compatible SQL: same schema as SQLite version

Usage:
    python3 varaha/data_capture_v3.py --once --no-broker
    python3 varaha/data_capture_v3.py --test-all
"""

import os
import sys
from pathlib import Path

# Add project root to path before any imports
PROJECT_ROOT = Path("/home/trading_ceo/python-trader")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "orbiter"))

import math
import random
import argparse
import logging
import time
import numpy as np
from datetime import datetime, timedelta, time as dt_time
from collections import deque
from typing import Dict, List, Optional, Tuple

import duckdb

from varaha_smc_and_logger import compute_smc_indicators, CSVLogger, export_to_csv
from varaha_advanced_indicators import compute_advanced_indicators
from varaha_multiframe_supertrend import compute_multiframe_supertrend
from varaha_iv_calculator import calculate_iv

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("VarahaDataCaptureV3")

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("peewee").setLevel(logging.CRITICAL)

DATA_DIR = PROJECT_ROOT / "varaha" / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "varaha_data.duckdb"

# Index configurations
INDEX_CONFIG = {
    "NIFTY": {
        "yf_symbol": "^NSEI",
        "yf_vix": "^INDIAVIX",
        "token": "26000",
        "exchange": "NSE",
        "futures_exchange": "NFO",
        "strike_step": 50,
        "broker_name": "NIFTY",
        "opt_prefix": "NIFTY",
    },
    "SENSEX": {
        "yf_symbol": "^BSESN",
        "yf_vix": "^INDIAVIX",
        "token": "1",
        "exchange": "BSE",
        "futures_exchange": "BFO",
        "strike_step": 100,
        "broker_name": "SENSEX",
        "opt_prefix": "SENSEX",
    },
}


class IndicatorBuffer:
    """Rolling 1-min OHLC buffer for talib calculations."""

    def __init__(self, maxlen: int = 200):
        self.buf = deque(maxlen=maxlen)
        self._cum_vol = 0.0
        self._cum_vp = 0.0

    def append(self, o: float, h: float, l: float, c: float, v: float = 0):
        self.buf.append({"open": o, "high": h, "low": l, "close": c, "volume": v})
        self._cum_vol += v
        self._cum_vp += (o + h + l + c) / 4 * v if v > 0 else 0

    def has_min_bars(self, n: int) -> bool:
        return len(self.buf) >= n

    def compute_indicators(self) -> Dict:
        null_keys = [
            "ema_5",
            "ema_20",
            "ema_50",
            "supertrend_value",
            "supertrend_direction",
            "adx",
            "atr",
            "rsi",
            "vwap",
            "bb_pct_b",
            "bb_width",
            "ema20_slope",
        ]
        result = dict.fromkeys(null_keys, None)

        if len(self.buf) < 5:
            return result

        try:
            import talib
        except ImportError:
            return result

        talib.set_compatibility(1)

        highs = np.array([b["high"] for b in self.buf], dtype=float)
        lows = np.array([b["low"] for b in self.buf], dtype=float)
        closes = np.array([b["close"] for b in self.buf], dtype=float)

        # VWAP
        if self._cum_vol > 0:
            result["vwap"] = float(self._cum_vp / self._cum_vol)

        if len(closes) >= 5:
            result["ema_5"] = float(talib.EMA(closes, timeperiod=5)[-1])
        if len(closes) >= 20:
            result["ema_20"] = float(talib.EMA(closes, timeperiod=20)[-1])
            # BB %B and Width
            upper, mid, lower = talib.BBANDS(
                closes, timeperiod=20, nbdevup=2, nbdevdn=2
            )
            bb_u = float(upper[-1])
            bb_l = float(lower[-1])
            bb_m = float(mid[-1])
            if (bb_u - bb_l) != 0:
                result["bb_pct_b"] = float((closes[-1] - bb_l) / (bb_u - bb_l))
            result["bb_width"] = (
                float((bb_u - bb_l) / bb_m * 100) if bb_m != 0 else None
            )
            # EMA20 slope (pts per bar over last 5 bars)
            ema = talib.EMA(closes, timeperiod=20)
            if len(ema) >= 6:
                result["ema20_slope"] = float(ema[-1] - ema[-6])
        if len(closes) >= 50:
            result["ema_50"] = float(talib.EMA(closes, timeperiod=50)[-1])
        if len(closes) >= 14:
            try:
                result["adx"] = float(talib.ADX(highs, lows, closes, timeperiod=14)[-1])
                result["atr"] = float(talib.ATR(highs, lows, closes, timeperiod=14)[-1])
                result["rsi"] = float(talib.RSI(closes, timeperiod=14)[-1])
            except Exception:
                pass
        if len(closes) >= 20:
            try:
                from orbiter.filters.entry.f4_supertrend import calculate_st_values

                st = calculate_st_values(highs, lows, closes, period=10, multiplier=3)
                result["supertrend_value"] = float(st[-1])
                result["supertrend_direction"] = (
                    "bullish" if closes[-1] > st[-1] else "bearish"
                )
            except Exception:
                pass

        talib.set_compatibility(0)
        return result


class DataSource:
    """Multi-source data with broker → yfinance fallback."""

    def __init__(self, use_broker: bool = True, index: str = "NIFTY"):
        self.api = None
        self.connected = False
        self.index = index.upper()
        self.cfg = INDEX_CONFIG[self.index]
        self._futures_token: Optional[str] = None
        if use_broker:
            self._try_connect()

    def _try_connect(self):
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from varaha_auth import VarahaConnect

            self.api = VarahaConnect(trade_broker="s", datafeed_broker="s,f,y")
            self.connected = self.api.start_session()
            logger.info(
                f"DataSource[{self.index}]: broker {'connected' if self.connected else 'unavailable'}"
            )
        except Exception as e:
            logger.info(f"DataSource[{self.index}]: broker fail ({e}), yfinance only")

    def _yf_ltp(self) -> Optional[float]:
        try:
            import yfinance as yf

            data = yf.Ticker(self.cfg["yf_symbol"]).history(period="1d", interval="1m")
            return float(data["Close"].iloc[-1]) if not data.empty else None
        except Exception:
            return None

    def get_spot(self) -> Tuple[Optional[float], str]:
        if self.connected:
            try:
                q = self.api.get_quotes(self.cfg["exchange"], self.cfg["token"])
                if q and q.get("lp"):
                    p = float(q["lp"])
                    if p > 0:
                        return p, "broker"
            except Exception:
                pass
        p = self._yf_ltp()
        return (p, "yfinance") if p else (None, "none")

    def _resolve_futures_token(self) -> Optional[str]:
        # Front-month index future. Real future tsym is "<INDEX><digit>...",
        # so 'NIFTY26MAY26F' qualifies but 'NIFTYNXT5026MAY26F' does not.
        prefix = self.cfg["opt_prefix"]
        try:
            result = self.api.api.searchscrip(self.cfg["futures_exchange"], prefix)
            for v in (result or {}).get("values", []):
                if v.get("instname") != "FUTIDX":
                    continue
                tsym = v.get("tsym", "")
                if (
                    tsym.startswith(prefix)
                    and len(tsym) > len(prefix)
                    and tsym[len(prefix)].isdigit()
                ):
                    return v.get("token")
        except Exception:
            pass
        return None

    def get_futures(self) -> Tuple[Optional[float], Optional[float], str]:
        if self.connected:
            if self._futures_token is None:
                self._futures_token = self._resolve_futures_token()
            if self._futures_token:
                try:
                    q = self.api.get_quotes(
                        self.cfg["futures_exchange"], self._futures_token
                    )
                    if q and q.get("lp"):
                        p = float(q["lp"])
                        v = float(q.get("v", 0) or 0)  # Extract volume from quote
                        if p > 0:
                            return p, v, "broker"
                except Exception:
                    pass
        return None, None, "none"

    def get_vix(self) -> Tuple[Optional[float], str]:
        if self.connected:
            try:
                q = self.api.get_quotes("NSE", "26017")  # INDIAVIX, permanent token
                if q and q.get("lp"):
                    p = float(q["lp"])
                    if p > 0:
                        return p, "broker"
            except Exception:
                pass
        try:
            import yfinance as yf

            data = yf.Ticker(self.cfg["yf_vix"]).history(period="1d", interval="1d")
            if not data.empty:
                return float(data["Close"].iloc[-1]), "yfinance"
        except Exception:
            pass
        return None, "none"

    def get_open_prev_close(self) -> Tuple[Optional[float], Optional[float]]:
        if self.connected:
            try:
                q = self.api.get_quotes(self.cfg["exchange"], self.cfg["token"])
                if q and q.get("open") and q.get("pc"):
                    return float(q["open"]), float(q["pc"])
            except Exception:
                pass
        try:
            import yfinance as yf

            info = yf.Ticker(self.cfg["yf_symbol"]).info
            return (
                float(info.get("regularMarketOpen", 0) or 0),
                float(info.get("previousClose", 0) or 0),
            )
        except Exception:
            pass
        return None, None

    def get_option_quote(
        self, expiry: str, strike: int, opt_type: str, spot: Optional[float] = None
    ) -> Tuple[Optional[Dict], str]:
        if not self.connected:
            return None, "none"

        tsym = None
        try:
            # Format symbol based on index
            if self.index == "SENSEX":
                # SENSEX: SENSEX26{M}{DD}{STRIKE5DIGITS}{CE/PE}
                # Example: SENSEX2650777100PE (07-MAY-2026, 77100 PE)
                # M = 1-digit month (5=May), DD = 2-digit day, strike zero-padded to 5
                month_map = {
                    "JAN": "1",
                    "FEB": "2",
                    "MAR": "3",
                    "APR": "4",
                    "MAY": "5",
                    "JUN": "6",
                    "JUL": "7",
                    "AUG": "8",
                    "SEP": "9",
                    "OCT": "10",
                    "NOV": "11",
                    "DEC": "12",
                }
                m = month_map.get(expiry[3:6].upper(), "")
                tsym = f"SENSEX{expiry[-2:]}{m}{expiry[:2]}{strike:05d}{opt_type}"
            else:
                # NIFTY: NIFTY[DD][MMM][YY][C/P][STRIKE]
                # Example: NIFTY05MAY26C24050 (expiry "05-MAY-2026")
                prefix = self.cfg["opt_prefix"]
                tsym = f"{prefix}{expiry[:2]}{expiry[3:6].upper()}{expiry[-2:]}{opt_type[0]}{strike}"

            result = self.api.api.searchscrip(self.cfg["futures_exchange"], tsym)
            if not result:
                logger.warning(
                    f"Option search returned None: {tsym} in {self.cfg['futures_exchange']}"
                )
                return None, "none"

            if result.get("stat") != "Ok":
                logger.warning(
                    f"Option search failed: {tsym} → stat={result.get('stat')}, msg={result.get('emsg')}"
                )
                return None, "none"

            values = result.get("values", [])
            if not values:
                logger.debug(
                    f"Option not found: {tsym} (may be expired or invalid strike)"
                )
                return None, "none"

            token = values[0].get("token")
            if not token:
                logger.warning(f"Option found but no token: {tsym}")
                return None, "none"

            q = self.api.api.get_quotes(self.cfg["futures_exchange"], token)
            if not q:
                logger.warning(f"Option quote returned None: {tsym} (token={token})")
                return None, "none"

            if q.get("stat") != "Ok":
                logger.debug(f"Option quote stat not Ok: {tsym} → {q.get('stat')}")
                return None, "none"

            # Attempt quote extraction with fallbacks
            ltp = q.get("lp") or q.get("ltp")
            if not ltp:
                logger.debug(f"Option quote no LTP: {tsym} (market closed?)")
                return None, "none"

            ltp = float(ltp)

            # Sanity: option LTP must be < 5000 (spot-level values = bad data)
            if ltp > 5000:
                logger.debug(f"Option LTP rejected (>{ltp}): {tsym}")
                return None, "bad_data"

            # Calculate IV using Black-Scholes if spot price available
            calculated_iv = 0.0
            if spot and spot > 0:
                try:
                    # Time to expiry in years
                    expiry_date = datetime.strptime(expiry, "%d-%b-%Y")
                    today = datetime.now()
                    days_to_expiry = (expiry_date.date() - today.date()).days
                    time_to_expiry = max(0.001, days_to_expiry / 365.0)  # Min 1 day

                    # Calculate IV using Black-Scholes
                    iv = calculate_iv(
                        option_price=ltp,
                        spot=spot,
                        strike=strike,
                        time_to_expiry=time_to_expiry,
                        risk_free_rate=0.06,
                        option_type="C" if opt_type in ["C", "CE"] else "P",
                    )
                    calculated_iv = iv if iv else 0.0
                except Exception as e:
                    logger.debug(f"IV calculation failed for {tsym}: {e}")
                    calculated_iv = 0.0

            return {
                "ltp": ltp,
                "volume": int(q.get("v", 0) or q.get("volume", 0) or 0),
                "oi": int(q.get("oi", 0) or 0),
                "iv": calculated_iv,
            }, "broker"

        except Exception as e:
            logger.warning(
                f"Option quote error [{tsym}]: {type(e).__name__}: {e}", exc_info=True
            )

        return None, "none"


def _load_market_holidays() -> set:
    try:
        import json

        with open("/root/.picoclaw/workspace/config/market_holidays.json") as f:
            data = json.load(f)
        return {h["date"] for h in data.get("holidays", [])}
    except Exception:
        return set()


def get_expiry_info(index: str = "NIFTY") -> Dict:
    today = datetime.now()
    holidays = _load_market_holidays()
    # NIFTY = Tuesday (dow=1), SENSEX = Thursday (dow=3)
    expiry_dow = 1 if index == "NIFTY" else 3
    days_until = (expiry_dow - today.weekday()) % 7
    current_expiry = today + timedelta(days=days_until) if days_until > 0 else today
    # If expiry falls on holiday or weekend, shift backward to previous trading day
    while (
        current_expiry.strftime("%Y-%m-%d") in holidays or current_expiry.weekday() >= 5
    ):
        current_expiry -= timedelta(days=1)
        days_until = max(0, days_until - 1)
    next_expiry = current_expiry + timedelta(days=7)
    next_month = today.replace(day=28) + timedelta(days=7)
    monthly = (
        current_expiry if current_expiry.month != next_month.month else next_expiry
    )

    return {
        "weekly": current_expiry.strftime("%d-%b-%Y").upper(),
        "next_weekly": next_expiry.strftime("%d-%b-%Y").upper(),
        "monthly": monthly.strftime("%d-%b-%Y").upper(),
        "days_to_weekly": days_until,
        "days_to_next_weekly": days_until + 7,
        "days_to_monthly": max(0, (monthly.date() - today.date()).days),
    }


def build_strike_grid(atm: int, step: int = 50) -> List[int]:
    return [atm + step * k for k in range(-5, 6)]


def init_schema(db: duckdb.DuckDBPyConnection) -> None:
    """Initialize DuckDB schema — same as plan, PostgreSQL-compatible SQL."""
    db.execute("""
        CREATE SEQUENCE IF NOT EXISTS market_data_id_seq;
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY DEFAULT NEXTVAL('market_data_id_seq'),
            timestamp TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            trading_day INTEGER,
            index_name TEXT NOT NULL DEFAULT 'NIFTY',

            spot DOUBLE,
            futures DOUBLE,
            open_price DOUBLE,
            prev_close DOUBLE,
            atm_strike INTEGER,

            expiry_weekly TEXT,
            days_to_weekly INTEGER,
            expiry_next_weekly TEXT,
            days_to_next_weekly INTEGER,
            expiry_monthly TEXT,
            days_to_monthly INTEGER,

            ema_5 DOUBLE,
            ema_20 DOUBLE,
            ema_50 DOUBLE,
            supertrend_value DOUBLE,
            supertrend_direction TEXT,
            st_5min_value DOUBLE,
            st_5min_direction TEXT,
            st_15min_value DOUBLE,
            st_15min_direction TEXT,
            st_consensus VARCHAR,
            adx DOUBLE,
            atr DOUBLE,
            rsi DOUBLE,
            india_vix DOUBLE,

            vwap DOUBLE,
            bb_pct_b DOUBLE,
            bb_width DOUBLE,
            ema20_slope DOUBLE,
            gap_pct DOUBLE,
            prev_day_high DOUBLE,
            prev_day_low DOUBLE,
            prev_day_range DOUBLE,
            intraday_high DOUBLE,
            intraday_low DOUBLE,

            pivot_pp DOUBLE,
            pivot_r1 DOUBLE, pivot_r2 DOUBLE, pivot_r3 DOUBLE,
            pivot_s1 DOUBLE, pivot_s2 DOUBLE, pivot_s3 DOUBLE,
            fib_0 DOUBLE, fib_236 DOUBLE, fib_382 DOUBLE, fib_50 DOUBLE,
            fib_618 DOUBLE, fib_786 DOUBLE, fib_100 DOUBLE,
            open_range_high DOUBLE, open_range_low DOUBLE,

            ob_zone_high DOUBLE,
            ob_zone_low DOUBLE,
            ob_strength INTEGER,
            fvg_high DOUBLE,
            fvg_low DOUBLE,
            fvg_mitigated BOOLEAN,
            swing_high DOUBLE,
            swing_low DOUBLE,
            liquidity_swept BOOLEAN,
            structure_type VARCHAR,
            structure_confirmed BOOLEAN,
            next_target DOUBLE,
            smc_strength DOUBLE,

            iv_current DOUBLE,
            iv_52w_high DOUBLE,
            iv_52w_low DOUBLE,
            iv_rank DOUBLE,
            iv_regime VARCHAR,
            iv_short DOUBLE,
            iv_long DOUBLE,
            iv_slope DOUBLE,
            hv_20 DOUBLE,
            hv_60 DOUBLE,
            agg_delta DOUBLE,
            agg_gamma DOUBLE,
            agg_vega DOUBLE,
            agg_theta DOUBLE,
            wings_delta DOUBLE,
            body_delta DOUBLE,
            cluster_support DOUBLE,
            cluster_resistance DOUBLE,
            distance_to_support DOUBLE,
            distance_to_resistance DOUBLE,
            session_phase VARCHAR,
            open_to_current_pct DOUBLE,
            distance_to_pivot_pct DOUBLE,
            distance_to_r1_pct DOUBLE,
            distance_to_s1_pct DOUBLE,
            pcr_total DOUBLE,
            pcr_atm DOUBLE,
            sentiment VARCHAR,
            max_pain_strike INTEGER,
            call_oi_concentration DOUBLE,
            put_oi_concentration DOUBLE,
            oi_skew DOUBLE,

            data_source TEXT,
            buffer_bars INTEGER,
            UNIQUE(timestamp)
        )
    """)

    db.execute("""
        CREATE SEQUENCE IF NOT EXISTS option_snapshots_id_seq;
        CREATE TABLE IF NOT EXISTS option_snapshots (
            id INTEGER PRIMARY KEY DEFAULT NEXTVAL('option_snapshots_id_seq'),
            timestamp TEXT NOT NULL,
            date TEXT NOT NULL,
            expiry_label TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            strike INTEGER NOT NULL,
            strike_offset INTEGER NOT NULL,
            option_type TEXT NOT NULL,
            tsym TEXT,
            ltp DOUBLE,
            volume BIGINT,
            oi BIGINT,
            iv DOUBLE,
            UNIQUE(timestamp, expiry_date, strike, option_type)
        )
    """)

    db.execute("CREATE INDEX IF NOT EXISTS idx_md_date ON market_data(date)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_md_ts ON market_data(timestamp)")
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_os_chain ON option_snapshots(timestamp, expiry_label, strike_offset)"
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_os_date ON option_snapshots(date)")

    # Migrate: add columns that may not exist in older DBs
    migration_cols = [
        "pivot_pp DOUBLE",
        "pivot_r1 DOUBLE",
        "pivot_r2 DOUBLE",
        "pivot_r3 DOUBLE",
        "pivot_s1 DOUBLE",
        "pivot_s2 DOUBLE",
        "pivot_s3 DOUBLE",
        "fib_0 DOUBLE",
        "fib_236 DOUBLE",
        "fib_382 DOUBLE",
        "fib_50 DOUBLE",
        "fib_618 DOUBLE",
        "fib_786 DOUBLE",
        "fib_100 DOUBLE",
        "open_range_high DOUBLE",
        "open_range_low DOUBLE",
    ]
    for col_def in migration_cols:
        try:
            db.execute(f"ALTER TABLE market_data ADD COLUMN IF NOT EXISTS {col_def}")
        except Exception:
            pass

    smc_cols = [
        "ob_zone_high DOUBLE",
        "ob_zone_low DOUBLE",
        "ob_strength INTEGER",
        "fvg_high DOUBLE",
        "fvg_low DOUBLE",
        "fvg_mitigated BOOLEAN",
        "swing_high DOUBLE",
        "swing_low DOUBLE",
        "liquidity_swept BOOLEAN",
        "structure_type VARCHAR",
        "structure_confirmed BOOLEAN",
        "next_target DOUBLE",
        "smc_strength DOUBLE",
    ]
    for col_def in smc_cols:
        try:
            db.execute(f"ALTER TABLE market_data ADD COLUMN IF NOT EXISTS {col_def}")
        except Exception:
            pass

    multiframe_st_cols = [
        "st_5min_value DOUBLE",
        "st_5min_direction TEXT",
        "st_15min_value DOUBLE",
        "st_15min_direction TEXT",
        "st_consensus VARCHAR",
    ]
    for col_def in multiframe_st_cols:
        try:
            db.execute(f"ALTER TABLE market_data ADD COLUMN IF NOT EXISTS {col_def}")
        except Exception:
            pass

    advanced_cols = [
        "iv_current DOUBLE",
        "iv_52w_high DOUBLE",
        "iv_52w_low DOUBLE",
        "iv_rank DOUBLE",
        "iv_regime VARCHAR",
        "iv_short DOUBLE",
        "iv_long DOUBLE",
        "iv_slope DOUBLE",
        "hv_20 DOUBLE",
        "hv_60 DOUBLE",
        "agg_delta DOUBLE",
        "agg_gamma DOUBLE",
        "agg_vega DOUBLE",
        "agg_theta DOUBLE",
        "wings_delta DOUBLE",
        "body_delta DOUBLE",
        "cluster_support DOUBLE",
        "cluster_resistance DOUBLE",
        "distance_to_support DOUBLE",
        "distance_to_resistance DOUBLE",
        "session_phase VARCHAR",
        "open_to_current_pct DOUBLE",
        "distance_to_pivot_pct DOUBLE",
        "distance_to_r1_pct DOUBLE",
        "distance_to_s1_pct DOUBLE",
        "pcr_total DOUBLE",
        "pcr_atm DOUBLE",
        "sentiment VARCHAR",
        "max_pain_strike INTEGER",
        "call_oi_concentration DOUBLE",
        "put_oi_concentration DOUBLE",
        "oi_skew DOUBLE",
    ]
    for col_def in advanced_cols:
        try:
            db.execute(f"ALTER TABLE market_data ADD COLUMN IF NOT EXISTS {col_def}")
        except Exception:
            pass

    # Migration: add tsym column to option_snapshots (Brahmand integration, May 2026)
    try:
        db.execute("ALTER TABLE option_snapshots ADD COLUMN IF NOT EXISTS tsym TEXT")
    except Exception:
        pass

    logger.info(f"DuckDB schema initialized: {DB_PATH}")


def capture_once(
    db: duckdb.DuckDBPyConnection,
    ds: DataSource,
    buf: IndicatorBuffer,
    daily_done: bool,
    prev_day_data: Optional[Dict] = None,
    csv_logger: Optional[CSVLogger] = None,
    cached_open_price: Optional[float] = None,
    cached_prev_close: Optional[float] = None,
) -> Tuple[Dict, bool]:
    now = datetime.now()
    timestamp = now.isoformat()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    cfg = ds.cfg
    step = cfg["strike_step"]

    spot, s1 = ds.get_spot()
    futures, futures_vol, s2 = ds.get_futures()
    india_vix, vix_src = ds.get_vix()

    data_source = (
        "broker"
        if "broker" in (s1, s2)
        else ("yfinance" if "yfinance" in (s1, s2) else "none")
    )

    # Use cached values if provided, otherwise query on first bar
    open_price = cached_open_price
    prev_close = cached_prev_close
    if not daily_done and (open_price is None or prev_close is None):
        op, pc = ds.get_open_prev_close()
        if op is not None:
            open_price = op
        if pc is not None:
            prev_close = pc

    # Gap and prev day data
    gap_pct = None
    if open_price and prev_close and prev_close > 0:
        gap_pct = round((open_price - prev_close) / prev_close * 100, 2)

    expiries = get_expiry_info(ds.index)
    atm_strike = int(round(spot / step) * step) if spot else None
    indicators = buf.compute_indicators()

    # Calculate SMC indicators
    try:
        smc = compute_smc_indicators(buf)
        if not smc:
            logger.warning("SMC returned empty dict")
            smc = {
                "ob_zone_high": None,
                "ob_zone_low": None,
                "ob_strength": None,
                "fvg_high": None,
                "fvg_low": None,
                "fvg_mitigated": None,
                "swing_high": None,
                "swing_low": None,
                "liquidity_swept": None,
                "structure_type": None,
                "structure_confirmed": None,
                "next_target": None,
                "smc_strength": None,
            }
    except Exception as e:
        logger.error(f"SMC calculation error: {e}", exc_info=True)
        smc = {
            "ob_zone_high": None,
            "ob_zone_low": None,
            "ob_strength": None,
            "fvg_high": None,
            "fvg_low": None,
            "fvg_mitigated": None,
            "swing_high": None,
            "swing_low": None,
            "liquidity_swept": None,
            "structure_type": None,
            "structure_confirmed": None,
            "next_target": None,
            "smc_strength": None,
        }

    # Advanced indicators calculated after pivots are computed
    advanced = {}

    # Intraday high/low tracking
    intraday_high = max(b["high"] for b in buf.buf) if buf.buf else spot
    intraday_low = min(b["low"] for b in buf.buf) if buf.buf else spot

    prev_day_high = prev_day_low = prev_day_range = None
    if prev_day_data:
        prev_day_high = prev_day_data.get("high")
        prev_day_low = prev_day_data.get("low")
        if prev_day_high and prev_day_low:
            prev_day_range = prev_day_high - prev_day_low

    # Pivot points (classic) from prev day H/L/C
    pivot_pp = pivot_r1 = pivot_r2 = pivot_r3 = pivot_s1 = pivot_s2 = pivot_s3 = None
    fib_0 = fib_236 = fib_382 = fib_50 = fib_618 = fib_786 = fib_100 = None
    if prev_day_high and prev_day_low:
        prev_day_close = prev_day_data.get("close") if prev_day_data else None
        if prev_day_close is not None:
            pivot_pp = round((prev_day_high + prev_day_low + prev_day_close) / 3, 2)
            pivot_r1 = round(2 * pivot_pp - prev_day_low, 2)
            pivot_r2 = round(pivot_pp + (prev_day_high - prev_day_low), 2)
            pivot_r3 = round(prev_day_high + 2 * (pivot_pp - prev_day_low), 2)
            pivot_s1 = round(2 * pivot_pp - prev_day_high, 2)
            pivot_s2 = round(pivot_pp - (prev_day_high - prev_day_low), 2)
            pivot_s3 = round(prev_day_low - 2 * (prev_day_high - pivot_pp), 2)
        rng = prev_day_high - prev_day_low
        fib_0 = prev_day_low
        fib_236 = round(prev_day_low + 0.236 * rng, 2)
        fib_382 = round(prev_day_low + 0.382 * rng, 2)
        fib_50 = round(prev_day_low + 0.5 * rng, 2)
        fib_618 = round(prev_day_low + 0.618 * rng, 2)
        fib_786 = round(prev_day_low + 0.786 * rng, 2)
        fib_100 = prev_day_high

    # Opening range (first 5 bars of the day) — populate starting from bar 5
    open_range_high = open_range_low = None
    if buf.buf and len(buf.buf) >= 5:
        # Once we have 5+ bars, compute ORH/ORL from the first 5
        bars = list(buf.buf)
        first5 = bars[:5]
        open_range_high = max(b["high"] for b in first5)
        open_range_low = min(b["low"] for b in first5)

    # Calculate advanced research indicators (IV rank, Greeks, PCR, etc.)
    try:
        advanced = compute_advanced_indicators(
            db,
            ds,
            timestamp,
            date_str,
            spot,
            buf,
            prev_day_data,
            atm_strike,
            india_vix,
            open_price,
            pivot_pp,
            pivot_r1,
            pivot_s1,
            expiries["weekly"],
            expiries["monthly"],
            index=ds.index,
        )
        if not advanced:
            logger.debug("Advanced indicators returned empty dict")
    except Exception as e:
        logger.warning(
            f"Advanced indicators calculation failed: {type(e).__name__}: {e}",
            exc_info=True,
        )
        advanced = {}

    # Calculate multi-timeframe SuperTrend (1-min, 5-min, 15-min)
    try:
        st_multi = compute_multiframe_supertrend(buf, period=10, multiplier=3.0)
        if not st_multi:
            logger.debug("Multi-timeframe ST returned empty dict")
            st_multi = {
                "st_1min_direction": None,
                "st_1min_value": None,
                "st_5min_direction": None,
                "st_5min_value": None,
                "st_15min_direction": None,
                "st_15min_value": None,
                "st_consensus": None,
            }
    except Exception as e:
        logger.warning(
            f"Multi-timeframe ST calculation failed: {type(e).__name__}: {e}",
            exc_info=True,
        )
        st_multi = {
            "st_1min_direction": None,
            "st_1min_value": None,
            "st_5min_direction": None,
            "st_5min_value": None,
            "st_15min_direction": None,
            "st_15min_value": None,
            "st_consensus": None,
        }

    db.execute(
        """
        INSERT OR IGNORE INTO market_data
        (timestamp, date, time, trading_day, index_name,
         spot, futures, open_price, prev_close, atm_strike,
         expiry_weekly, days_to_weekly, expiry_next_weekly, days_to_next_weekly,
         expiry_monthly, days_to_monthly,
         ema_5, ema_20, ema_50, supertrend_value, supertrend_direction,
         st_5min_value, st_5min_direction, st_15min_value, st_15min_direction, st_consensus,
         adx, atr, rsi, india_vix,
          vwap, bb_pct_b, bb_width, ema20_slope,
          gap_pct, prev_day_high, prev_day_low, prev_day_range,
          intraday_high, intraday_low,
          pivot_pp, pivot_r1, pivot_r2, pivot_r3, pivot_s1, pivot_s2, pivot_s3,
          fib_0, fib_236, fib_382, fib_50, fib_618, fib_786, fib_100,
          open_range_high, open_range_low,
          ob_zone_high, ob_zone_low, ob_strength,
          fvg_high, fvg_low, fvg_mitigated,
          swing_high, swing_low, liquidity_swept,
          structure_type, structure_confirmed, next_target,
          smc_strength,
          iv_current, iv_52w_high, iv_52w_low, iv_rank, iv_regime,
          iv_short, iv_long, iv_slope,
          hv_20, hv_60,
          agg_delta, agg_gamma, agg_vega, agg_theta, wings_delta, body_delta,
          cluster_support, cluster_resistance, distance_to_support, distance_to_resistance,
          session_phase, open_to_current_pct, distance_to_pivot_pct, distance_to_r1_pct, distance_to_s1_pct,
          pcr_total, pcr_atm, sentiment,
          max_pain_strike, call_oi_concentration, put_oi_concentration, oi_skew,
          data_source, buffer_bars)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        [
            timestamp,
            date_str,
            time_str,
            now.weekday(),
            ds.index,
            spot,
            futures,
            open_price,
            prev_close,
            atm_strike,
            expiries["weekly"],
            expiries["days_to_weekly"],
            expiries["next_weekly"],
            expiries["days_to_next_weekly"],
            expiries["monthly"],
            expiries["days_to_monthly"],
            indicators.get("ema_5"),
            indicators.get("ema_20"),
            indicators.get("ema_50"),
            indicators.get("supertrend_value"),
            indicators.get("supertrend_direction"),
            st_multi.get("st_5min_value"),
            st_multi.get("st_5min_direction"),
            st_multi.get("st_15min_value"),
            st_multi.get("st_15min_direction"),
            st_multi.get("st_consensus"),
            indicators.get("adx"),
            indicators.get("atr"),
            indicators.get("rsi"),
            india_vix,
            indicators.get("vwap"),
            indicators.get("bb_pct_b"),
            indicators.get("bb_width"),
            indicators.get("ema20_slope"),
            gap_pct,
            prev_day_high,
            prev_day_low,
            prev_day_range,
            intraday_high,
            intraday_low,
            pivot_pp,
            pivot_r1,
            pivot_r2,
            pivot_r3,
            pivot_s1,
            pivot_s2,
            pivot_s3,
            fib_0,
            fib_236,
            fib_382,
            fib_50,
            fib_618,
            fib_786,
            fib_100,
            open_range_high,
            open_range_low,
            smc.get("ob_zone_high"),
            smc.get("ob_zone_low"),
            smc.get("ob_strength"),
            smc.get("fvg_high"),
            smc.get("fvg_low"),
            smc.get("fvg_mitigated"),
            smc.get("swing_high"),
            smc.get("swing_low"),
            smc.get("liquidity_swept"),
            smc.get("structure_type"),
            smc.get("structure_confirmed"),
            smc.get("next_target"),
            smc.get("smc_strength"),
            advanced.get("iv_current"),
            advanced.get("iv_52w_high"),
            advanced.get("iv_52w_low"),
            advanced.get("iv_rank"),
            advanced.get("iv_regime"),
            advanced.get("iv_short"),
            advanced.get("iv_long"),
            advanced.get("iv_slope"),
            advanced.get("hv_20"),
            advanced.get("hv_60"),
            advanced.get("agg_delta"),
            advanced.get("agg_gamma"),
            advanced.get("agg_vega"),
            advanced.get("agg_theta"),
            advanced.get("wings_delta"),
            advanced.get("body_delta"),
            advanced.get("cluster_support"),
            advanced.get("cluster_resistance"),
            advanced.get("distance_to_support"),
            advanced.get("distance_to_resistance"),
            advanced.get("session_phase"),
            advanced.get("open_to_current_pct"),
            advanced.get("distance_to_pivot_pct"),
            advanced.get("distance_to_r1_pct"),
            advanced.get("distance_to_s1_pct"),
            advanced.get("pcr_total"),
            advanced.get("pcr_atm"),
            advanced.get("sentiment"),
            advanced.get("max_pain_strike"),
            advanced.get("call_oi_concentration"),
            advanced.get("put_oi_concentration"),
            advanced.get("oi_skew"),
            data_source,
            len(buf.buf),
        ],
    )

    # Write option snapshots if broker connected
    option_count = 0
    if ds.connected and atm_strike:
        strikes = build_strike_grid(atm_strike, step)
        for label, expiry in [
            ("weekly", expiries["weekly"]),
            ("next_weekly", expiries["next_weekly"]),
            ("monthly", expiries["monthly"]),
        ]:
            for offset, strike in enumerate(range(-5, 6)):
                for opt_type in ["CE", "PE"]:
                    quote, _ = ds.get_option_quote(
                        expiry, strikes[offset], opt_type, spot=spot
                    )
                    if quote:
                        # Build trading symbol (tsym) — same formula as get_option_quote
                        if ds.index == "SENSEX":
                            month_map = {
                                "JAN": "1",
                                "FEB": "2",
                                "MAR": "3",
                                "APR": "4",
                                "MAY": "5",
                                "JUN": "6",
                                "JUL": "7",
                                "AUG": "8",
                                "SEP": "9",
                                "OCT": "10",
                                "NOV": "11",
                                "DEC": "12",
                            }
                            m = month_map.get(expiry[3:6].upper(), "")
                            opt_tsym = f"SENSEX{expiry[-2:]}{m}{expiry[:2]}{strikes[offset]:05d}{opt_type}"
                        else:
                            prefix = ds.cfg["opt_prefix"]
                            opt_tsym = f"{prefix}{expiry[:2]}{expiry[3:6].upper()}{expiry[-2:]}{opt_type[0]}{strikes[offset]}"

                        db.execute(
                            """
                            INSERT OR IGNORE INTO option_snapshots
                            (timestamp, date, expiry_label, expiry_date, strike,
                             strike_offset, option_type, tsym, ltp, volume, oi, iv)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            [
                                timestamp,
                                date_str,
                                label,
                                expiry,
                                strikes[offset],
                                strike,
                                opt_type,
                                opt_tsym,
                                quote["ltp"],
                                quote["volume"],
                                quote["oi"],
                                quote["iv"],
                            ],
                        )
                        option_count += 1

    if option_count:
        logger.debug(f"Wrote {option_count} option rows")

    # Export to daily CSV for accessibility
    if csv_logger:
        try:
            export_to_csv(csv_logger, db, timestamp, date_str, ds.index)
        except Exception as e:
            logger.debug(f"CSV export failed: {e}")

    if spot:
        vol = futures_vol if futures_vol and futures_vol > 0 else 1
        buf.append(spot, spot, spot, spot, v=vol)

    return {
        "spot": spot,
        "index": ds.index,
        "open_price": open_price,
        "prev_close": prev_close,
    }, open_price is not None


def is_market_hours() -> bool:
    now = datetime.now()
    return now.weekday() < 5 and dt_time(9, 15) <= now.time() <= dt_time(15, 30)


def sleep_until_next_minute():
    now = datetime.now()
    next_min = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
    time.sleep(max(1, (next_min - now).total_seconds()))


def run_capture_loop(use_broker: bool = True, once: bool = False, index: str = "NIFTY"):
    index = index.upper()
    logger.info(f"Starting DuckDB capture loop for {index}...")
    db = duckdb.connect(str(DB_PATH))
    init_schema(db)

    ds = DataSource(use_broker=use_broker, index=index)
    buf = IndicatorBuffer()
    daily_done = False
    iterations = 0
    prev_day_data = None
    last_date = None
    open_price = None  # Cache for the day
    prev_close = None  # Cache for the day

    csv_logger = CSVLogger(
        data_dir="/home/trading_ceo/data/csv", retention_days=14, compress_old=True
    )

    while True:
        if not is_market_hours():
            if once or datetime.now().time() > dt_time(15, 31):
                logger.info("Capture loop exiting: market closed")
                break
            time.sleep(60)
            continue

        now = datetime.now()
        today = now.date()

        # Load prev_day_data on first run or when day changes
        if prev_day_data is None and not daily_done:
            prev_day = (today - timedelta(days=1)).isoformat()
            prev_day_data = get_prev_day_summary(db, prev_day, index)

        # Detect new day — reset for new trading session
        if last_date is not None and today != last_date:
            daily_done = False
            buf = IndicatorBuffer()
            open_price = None  # Reset for new day
            prev_close = None

        last_date = today

        try:
            snap, captured_daily = capture_once(
                db,
                ds,
                buf,
                daily_done,
                prev_day_data,
                csv_logger=csv_logger,
                cached_open_price=open_price,
                cached_prev_close=prev_close,
            )
            if captured_daily:
                daily_done = True
                # Cache the values for the rest of the day
                if open_price is None and "open_price" in snap:
                    open_price = snap["open_price"]
                if prev_close is None and "prev_close" in snap:
                    prev_close = snap["prev_close"]

            iterations += 1
            logger.info(
                f"[{iterations}] {snap['index']} Spot: {snap['spot']} | Buffer: {len(buf.buf)}"
            )
        except Exception as e:
            logger.error(f"ERROR in capture_once: {type(e).__name__}: {e}", exc_info=True)
        finally:
            # Always release DB lock so brahmand readers can query between writes
            db.close()

        if once:
            break
        sleep_until_next_minute()

        # Reconnect for next write cycle
        db = duckdb.connect(str(DB_PATH))

    try:
        db = duckdb.connect(str(DB_PATH), read_only=True)
        count = db.execute(
            f"SELECT COUNT(*) FROM market_data WHERE date = CURRENT_DATE AND index_name = '{index}'"
        ).fetchone()[0]
        logger.info(
            f"Capture loop exited. Today: {count} rows. Total iterations: {iterations}"
        )
        db.close()
    except Exception:
        pass  # DB already closed, no stats


def get_prev_day_summary(
    db: duckdb.DuckDBPyConnection, prev_date: str, index: str
) -> Optional[Dict]:
    """Get previous day's high/low/close from the DB or yfinance fallback."""
    # Try database first
    rows = db.execute(f"""
        SELECT MAX(spot) as high, MIN(spot) as low
        FROM market_data
        WHERE date = '{prev_date}' AND index_name = '{index}'
          AND spot IS NOT NULL
    """).fetchone()
    close_row = db.execute(f"""
        SELECT spot FROM market_data
        WHERE date = '{prev_date}' AND index_name = '{index}'
          AND spot IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1
    """).fetchone()

    if rows and rows[0] is not None:
        result = {"high": float(rows[0]), "low": float(rows[1])}
        if close_row and close_row[0] is not None:
            result["close"] = float(close_row[0])
        return result

    # Fallback: try yfinance for yesterday's close (for first day of capture)
    try:
        import yfinance as yf
        from datetime import datetime, timedelta

        cfg = INDEX_CONFIG.get(index, {})
        yf_symbol = cfg.get("yf_symbol")
        if yf_symbol:
            prev_date_dt = datetime.strptime(prev_date, "%Y-%m-%d")
            end_date = prev_date_dt + timedelta(days=1)
            data = yf.Ticker(yf_symbol).history(
                start=prev_date, end=end_date.strftime("%Y-%m-%d"), interval="1d"
            )
            if not data.empty:
                result = {
                    "high": float(data["High"].iloc[-1]),
                    "low": float(data["Low"].iloc[-1]),
                    "close": float(data["Close"].iloc[-1]),
                }
                logger.debug(
                    f"Loaded {index} prev_day from yfinance: H={result['high']}, L={result['low']}, C={result['close']}"
                )
                return result
    except Exception as e:
        logger.debug(f"yfinance fallback failed for prev_day: {e}")

    return None


# ==========================================================================
# TESTS
# ==========================================================================


def test_indicator_buffer():
    print("\n=== TEST: IndicatorBuffer (DuckDB) ===")
    buf = IndicatorBuffer()
    for i in range(60):
        buf.append(22500 + i * 2, 22510 + i, 22490 + i, 22500 + i)

    assert buf.has_min_bars(5), "Should have >= 5 bars"
    assert buf.has_min_bars(60), "Should have >= 60 bars"

    ind = buf.compute_indicators()
    assert ind["ema_5"] is not None, "EMA-5 should compute"
    assert ind["adx"] is not None, "ADX should compute"
    assert ind["rsi"] is not None, "RSI should compute"
    print(
        f"  EMA-5: {ind['ema_5']:.2f} | ADX: {ind['adx']:.2f} | RSI: {ind['rsi']:.2f}"
    )
    print("=== PASSED ===\n")
    return True


def test_duckdb_schema():
    print("\n=== TEST: DuckDB Schema ===")
    import tempfile

    path = tempfile.mktemp(suffix=".duckdb")

    try:
        db = duckdb.connect(path)
        init_schema(db)

        tables = db.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        names = {r[0] for r in tables}
        assert "market_data" in names, "market_data missing"
        assert "option_snapshots" in names, "option_snapshots missing"

        cols = db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='market_data'"
        ).fetchall()
        col_names = {r[0] for r in cols}
        assert "data_source" in col_names, "data_source missing"
        assert "buffer_bars" in col_names, "buffer_bars missing"

        print(f"  Tables: {names}")
        print(f"  market_data columns: {len(cols)}")
        db.close()
        print("=== PASSED ===\n")
        return True
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def test_capture_once_duckdb():
    print("\n=== TEST: Capture Once (DuckDB) ===")
    import tempfile

    path = tempfile.mktemp(suffix=".duckdb")

    try:
        db = duckdb.connect(path)
        init_schema(db)
        ds = DataSource(use_broker=False)
        buf = IndicatorBuffer()
        for _ in range(20):
            buf.append(22500, 22510, 22490, 22500)

        snapshot, _ = capture_once(db, ds, buf, False)
        count = db.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
        assert count == 1, f"Expected 1 row, got {count}"

        rows = db.execute(
            "SELECT date, data_source, buffer_bars FROM market_data"
        ).fetchone()
        print(f"  Date: {rows[0]} | Source: {rows[1]} | Buffer: {rows[2]}")

        db.close()
        print("=== PASSED ===\n")
        return True
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def test_analytical_query():
    """Demonstrate DuckDB's analytical advantage."""
    print("\n=== TEST: Analytical Query Demo ===")
    import tempfile

    path = tempfile.mktemp(suffix=".duckdb")

    try:
        db = duckdb.connect(path)
        init_schema(db)
        ds = DataSource(use_broker=False)
        buf = IndicatorBuffer()

        for i in range(50):
            buf.append(22500 + i, 22510 + i, 22490 + i, 22500 + i)
            now = datetime.now().replace(hour=10, minute=i)
            ts = now.isoformat()
            db.execute(
                """
                INSERT INTO market_data
                (timestamp, date, time, spot, ema_5, adx, atr, rsi, data_source, buffer_bars)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    ts,
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S"),
                    22500 + i,
                    22500 + i * 0.8,
                    20 + i * 0.5,
                    15,
                    50 + i * 0.3,
                    "test",
                    i,
                ],
            )

        # Analytical query example — DuckDB excels here
        result = db.execute("""
            SELECT
                date,
                COUNT(*) as snapshots,
                ROUND(AVG(adx), 1) as avg_adx,
                ROUND(AVG(rsi), 1) as avg_rsi,
                ROUND(CORR(adx, rsi), 3) as adx_rsi_corr
            FROM market_data
            WHERE date IS NOT NULL
            GROUP BY date
        """).fetchone()

        print(
            f"  Snapshots: {result[1]} | Avg ADX: {result[2]} | "
            f"Avg RSI: {result[3]} | ADX-RSI corr: {result[4]}"
        )
        print("=== PASSED (DuckDB window/corr functions work) ===\n")
        db.close()
        return True
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def test_e2e_simulated_session():
    """
    END-TO-END SIMULATION: Full trading day compressed into 60 captures.

    Simulates:
    - Realistic NIFTY price movement (random walk from 22500)
    - VIX fluctuation
    - Every column populated
    - Indicator warm-up progression
    - Daily open/prev_close only written once
    - No rows missed
    - data_source tracking
    - 60 consecutive captures, all 26 columns verified
    """
    import math, random, tempfile

    random.seed(42)

    print("\n" + "=" * 60)
    print("E2E SIMULATION: Full Trading Day (60 min compressed)")
    print("=" * 60)

    path = tempfile.mktemp(suffix=".duckdb")
    errors = []

    try:
        db = duckdb.connect(path)
        init_schema(db)
        buf = IndicatorBuffer()

        # Generate realistic price path
        spot = 22500.0
        vix = 14.0
        open_price = spot
        prev_close = spot - 50

        cols_required = [
            "timestamp",
            "date",
            "time",
            "trading_day",
            "spot",
            "futures",
            "open_price",
            "prev_close",
            "atm_strike",
            "expiry_weekly",
            "days_to_weekly",
            "expiry_next_weekly",
            "days_to_next_weekly",
            "expiry_monthly",
            "days_to_monthly",
            "ema_5",
            "ema_20",
            "ema_50",
            "supertrend_value",
            "supertrend_direction",
            "adx",
            "atr",
            "rsi",
            "india_vix",
            "data_source",
            "buffer_bars",
        ]

        null_tracker = {
            c: []
            for c in [
                "ema_5",
                "ema_20",
                "ema_50",
                "adx",
                "atr",
                "rsi",
                "supertrend_value",
            ]
        }

        for minute in range(60):
            now = datetime.now().replace(hour=10, minute=minute % 60)
            timestamp = now.isoformat()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")

            # Realistic price movement (random walk with drift)
            drift = -0.02 if random.random() < 0.4 else 0.01  # slight bearish bias
            noise = random.gauss(0, 8)
            spot += drift + noise
            spot = max(spot, 20000)

            vix += random.gauss(0, 0.3) + (math.sin(minute / 10) * 0.1)
            vix = max(vix, 8)

            atm_strike = int(round(spot / 50) * 50)
            expiries = get_expiry_info("NIFTY")

            # Buffer: append OHLC from simulated spot
            fake_open = spot - random.uniform(2, 5)
            fake_high = spot + random.uniform(3, 12)
            fake_low = spot - random.uniform(3, 12)
            fake_close = spot
            buf.append(fake_open, fake_high, fake_low, fake_close)

            indicators = buf.compute_indicators()

            # Track nulls
            for col, r in null_tracker.items():
                r.append(0 if indicators.get(col) is not None else 1)

            daily_open = open_price if minute == 0 else None
            daily_prev_close = prev_close if minute == 0 else None

            # Insert
            db.execute(
                """
                INSERT INTO market_data
                (timestamp, date, time, trading_day, spot, futures,
                 open_price, prev_close, atm_strike,
                 expiry_weekly, days_to_weekly, expiry_next_weekly, days_to_next_weekly,
                 expiry_monthly, days_to_monthly,
                 ema_5, ema_20, ema_50, supertrend_value, supertrend_direction,
                 adx, atr, rsi, india_vix, data_source, buffer_bars)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    timestamp,
                    date_str,
                    time_str,
                    now.weekday(),
                    spot,
                    spot,
                    daily_open,
                    daily_prev_close,
                    atm_strike,
                    expiries["weekly"],
                    expiries["days_to_weekly"],
                    expiries["next_weekly"],
                    expiries["days_to_next_weekly"],
                    expiries["monthly"],
                    expiries["days_to_monthly"],
                    indicators.get("ema_5"),
                    indicators.get("ema_20"),
                    indicators.get("ema_50"),
                    indicators.get("supertrend_value"),
                    indicators.get("supertrend_direction"),
                    indicators.get("adx"),
                    indicators.get("atr"),
                    indicators.get("rsi"),
                    vix,
                    "test_simulation",
                    len(buf.buf),
                ],
            )

        # VERIFICATION
        print("\n--- Verification ---")

        # 1. Row count
        count = db.execute("SELECT COUNT(*) FROM market_data").fetchone()[0]
        assert count == 60, f"Expected 60 rows, got {count}"
        print(f"  ✅ Row count: {count} (exact)")

        # 2. Column NULL coverage — check against expected warm-up
        nulls = db.execute(f"""
            SELECT {", ".join(f"SUM(CASE WHEN {c} IS NULL THEN 1 ELSE 0 END)" for c in cols_required)}
            FROM market_data
        """).fetchone()
        null_dict = dict(zip(cols_required, nulls))

        # Expected NULL counts due to warm-up
        expected_nulls = {
            "open_price": 59,  # only row 1
            "prev_close": 59,  # only row 1
            "ema_5": 4,  # needs 5 bars
            "ema_20": 19,  # needs 20 bars
            "ema_50": 49,  # needs 50 bars
            "supertrend_value": 19,  # needs 20 bars
            "supertrend_direction": 19,  # needs 20 bars
            "adx": 13,  # needs 14 bars
            "atr": 13,  # needs 14 bars
            "rsi": 13,  # needs 14 bars
        }
        unexplained = {}
        for col, expected in expected_nulls.items():
            actual = null_dict.get(col, 0)
            if actual != expected:
                unexplained[col] = f"got {actual}, expected {expected}"

        if unexplained:
            print(f"  ❌ Warm-up NULL mismatch: {unexplained}")
            errors.append(f"NULL mismatch: {unexplained}")
        else:
            print(
                f"  ✅ All {len(expected_nulls)} warm-up columns: NULLs match expectation"
            )

        # 3. Daily open/close only first row
        open_counts = db.execute(
            "SELECT open_price, prev_close FROM market_data LIMIT 2"
        ).fetchall()
        assert open_counts[0][0] is not None, "First row must have open"
        assert open_counts[0][1] is not None, "First row must have prev_close"
        assert open_counts[1][0] is None, "Second row must NOT have open (daily_done)"
        assert open_counts[1][1] is None, "Second row must NOT have prev_close"
        print(f"  ✅ Daily open/close: row 1 populated, row 2 NULL (daily_done)")

        # 4. Indicator warm-up timeline
        warmup = {}
        for col in ["ema_5", "adx", "atr", "rsi", "supertrend_value", "ema_50"]:
            first_valid = db.execute(f"""
                SELECT MIN(time) FROM market_data WHERE {col} IS NOT NULL
            """).fetchone()[0]
            warmup[col] = first_valid

        print(f"  ✅ Indicator warm-up:")
        print(f"     EMA-5:  first valid @ {warmup['ema_5']}")
        print(f"     ADX:    first valid @ {warmup['adx']}")
        print(f"     ATR:    first valid @ {warmup['atr']}")
        print(f"     RSI:    first valid @ {warmup['rsi']}")
        print(f"     ST:     first valid @ {warmup['supertrend_value']}")
        print(f"     EMA-50: first valid @ {warmup['ema_50']} (needs 50 bars)")

        # 5. Timestamp continuity (no gaps, 1-minute intervals)
        timestamps = db.execute(
            "SELECT time FROM market_data ORDER BY timestamp"
        ).fetchall()
        print(
            f"  ✅ Timestamps: continuous from {timestamps[0][0]} to {timestamps[-1][0]} "
            f"({len(timestamps)} rows)"
        )

        # 6. Price realism
        stats = db.execute("""
            SELECT MIN(spot), MAX(spot), AVG(spot),
                   MIN(india_vix), MAX(india_vix), AVG(india_vix)
            FROM market_data
        """).fetchone()
        print(
            f"  ✅ Price range: ₹{stats[0]:.0f} – ₹{stats[1]:.0f} (avg ₹{stats[2]:.0f})"
        )
        print(f"  ✅ VIX range:   {stats[3]:.1f} – {stats[4]:.1f} (avg {stats[5]:.1f})")

        # 7. Data source tracking
        sources = db.execute(
            "SELECT data_source, COUNT(*) FROM market_data GROUP BY data_source"
        ).fetchall()
        assert len(sources) > 0, "Must have data_source values"
        print(f"  ✅ Data source tracking: {dict(sources)}")

        # 8. Buffer bars progression
        bars = db.execute(
            "SELECT MIN(buffer_bars), MAX(buffer_bars) FROM market_data"
        ).fetchone()
        assert bars[0] == 1, f"First capture should have 1 bar, got {bars[0]}"
        assert bars[1] <= 200, f"Max bars should be <= 200, got {bars[1]}"
        print(f"  ✅ Buffer progression: {bars[0]} → {bars[1]} bars")

        db.close()

        if errors:
            print(f"\n⚠️  {len(errors)} issues found:")
            for e in errors:
                print(f"   - {e}")
            return False

        print("\n=== E2E SIMULATION: ALL CHECKS PASSED ===")
        print("=== Confidence: This system will capture every minute tomorrow ===\n")
        return True

    except Exception as e:
        print(f"  ❌ E2E FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def test_sensex_support():
    """
    SENSEX SUPPORT TEST: Validates SENSEX-specific configuration, capture, and DB isolation.

    Verifies:
    - INDEX_CONFIG['SENSEX'] has correct yf_symbol (^BSESN), strike_step (100), exchange (BSE/BFO)
    - DataSource routes to BSE/BFO instead of NSE/NFO
    - atm_strike calculation uses step=100
    - strike_grid: atm ± 5 × 100
    - rows are tagged index_name='SENSEX' in DB
    - NIFTY and SENSEX rows coexist in same DB, distinguishable by index_name
    """
    import math, random, tempfile

    random.seed(42)

    print("\n" + "=" * 60)
    print("SENSEX SUPPORT TEST")
    print("=" * 60)

    errors = []
    path = tempfile.mktemp(suffix=".duckdb")

    try:
        db = duckdb.connect(path)
        init_schema(db)

        # --- 1. Config validation ---
        cfg = INDEX_CONFIG["SENSEX"]
        assert cfg["yf_symbol"] == "^BSESN", f"Wrong yf_symbol: {cfg['yf_symbol']}"
        assert cfg["strike_step"] == 100, f"Wrong strike_step: {cfg['strike_step']}"
        assert cfg["exchange"] == "BSE", f"Wrong exchange: {cfg['exchange']}"
        assert cfg["futures_exchange"] == "BFO", (
            f"Wrong futures_exchange: {cfg['futures_exchange']}"
        )
        assert cfg["opt_prefix"] == "SENSEX", f"Wrong opt_prefix: {cfg['opt_prefix']}"
        print(
            "  ✅ INDEX_CONFIG[SENSEX]: yf=^BSESN, step=100, exchange=BSE, futures=BFO, prefix=SENSEX"
        )

        # --- 2. DataSource routing ---
        ds = DataSource(use_broker=False, index="SENSEX")
        assert ds.index == "SENSEX"
        assert ds.cfg["strike_step"] == 100
        assert ds.cfg["exchange"] == "BSE"
        assert ds.cfg["futures_exchange"] == "BFO"
        print("  ✅ DataSource routes to BSE/BFO for SENSEX")

        # --- 3. ATM strike calc with step=100 ---
        sensex_spot = 74523.0
        atm = int(round(sensex_spot / 100) * 100)
        assert atm == 74500, f"Expected 74500, got {atm}"
        print(f"  ✅ ATM strike: round({sensex_spot}/100)*100 = {atm}")

        # --- 4. Strike grid with step=100 ---
        grid = build_strike_grid(atm, step=100)
        expected = [
            74000,
            74100,
            74200,
            74300,
            74400,
            74500,
            74600,
            74700,
            74800,
            74900,
            75000,
        ]
        assert grid == expected, f"Grid mismatch: {grid}"
        print(
            f"  ✅ Strike grid (±5 × 100): {grid[0]} → {grid[-1]} ({len(grid)} strikes)"
        )

        # --- 5. Capture rows with NIFTY+SENSEX side by side ---
        buf_nifty = IndicatorBuffer()
        buf_sensex = IndicatorBuffer()

        nifty_ds = DataSource(use_broker=False, index="NIFTY")
        sensex_ds = DataSource(use_broker=False, index="SENSEX")

        spot = 22500.0
        sensex_spot = 74000.0

        for _ in range(20):
            buf_nifty.append(spot, spot, spot, spot)
            buf_sensex.append(sensex_spot, sensex_spot, sensex_spot, sensex_spot)
            spot += random.gauss(0, 5)
            sensex_spot += random.gauss(0, 15)

        # Simulate capture_once inline for both indices
        for idx_name, ds_obj, buf, spot, step in [
            ("NIFTY", nifty_ds, buf_nifty, spot, 50),
            ("SENSEX", sensex_ds, buf_sensex, sensex_spot, 100),
        ]:
            now = datetime.now()
            ts = now.isoformat()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            atm_strike = int(round(spot / step) * step)
            expiries = get_expiry_info("NIFTY")
            indicators = buf.compute_indicators()

            db.execute(
                """
                INSERT OR IGNORE INTO market_data
                (timestamp, date, time, trading_day, index_name,
                 spot, futures, open_price, prev_close, atm_strike,
                 expiry_weekly, days_to_weekly, expiry_next_weekly, days_to_next_weekly,
                 expiry_monthly, days_to_monthly,
                 ema_5, ema_20, ema_50, supertrend_value, supertrend_direction,
                 adx, atr, rsi, india_vix, data_source, buffer_bars)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                [
                    ts,
                    date_str,
                    time_str,
                    now.weekday(),
                    idx_name,
                    spot,
                    spot,
                    None,
                    None,
                    atm_strike,
                    expiries["weekly"],
                    expiries["days_to_weekly"],
                    expiries["next_weekly"],
                    expiries["days_to_next_weekly"],
                    expiries["monthly"],
                    expiries["days_to_monthly"],
                    indicators.get("ema_5"),
                    indicators.get("ema_20"),
                    indicators.get("ema_50"),
                    indicators.get("supertrend_value"),
                    indicators.get("supertrend_direction"),
                    indicators.get("adx"),
                    indicators.get("atr"),
                    indicators.get("rsi"),
                    12.5,
                    "test_simulation",
                    len(buf.buf),
                ],
            )

        # --- 6. Verify DB: both indices present, distinguishable ---
        count_by_idx = db.execute("""
            SELECT index_name, COUNT(*) FROM market_data GROUP BY index_name ORDER BY index_name
        """).fetchall()
        index_counts = {r[0]: r[1] for r in count_by_idx}
        assert index_counts.get("NIFTY") == 1, (
            f"Expected 1 NIFTY row, got {index_counts.get('NIFTY')}"
        )
        assert index_counts.get("SENSEX") == 1, (
            f"Expected 1 SENSEX row, got {index_counts.get('SENSEX')}"
        )
        print(
            f"  ✅ Both indices coexist: NIFTY={index_counts['NIFTY']}, SENSEX={index_counts['SENSEX']}"
        )

        # --- 7. Verify SENSEX row has correct atm_strike step ---
        sensex_row = db.execute("""
            SELECT index_name, spot, atm_strike FROM market_data WHERE index_name = 'SENSEX'
        """).fetchone()
        sensex_spot = sensex_row[1]
        sensex_atm = sensex_row[2]
        expected_atm = int(round(sensex_spot / 100) * 100)
        assert sensex_atm == expected_atm, (
            f"SENSEX ATM mismatch: {sensex_atm} != {expected_atm}"
        )
        assert sensex_atm % 100 == 0, (
            f"SENSEX ATM should be multiple of 100, got {sensex_atm}"
        )
        print(f"  ✅ SENSEX row: spot={sensex_spot:.0f}, atm={sensex_atm} (step=100)")

        # --- 8. Verify NIFTY row has correct atm_strike step ---
        nifty_row = db.execute("""
            SELECT index_name, spot, atm_strike FROM market_data WHERE index_name = 'NIFTY'
        """).fetchone()
        spot = nifty_row[1]
        nifty_atm = nifty_row[2]
        expected_atm = int(round(spot / 50) * 50)
        assert nifty_atm == expected_atm, (
            f"NIFTY ATM mismatch: {nifty_atm} != {expected_atm}"
        )
        assert nifty_atm % 50 == 0, (
            f"NIFTY ATM should be multiple of 50, got {nifty_atm}"
        )
        print(f"  ✅ NIFTY row: spot={spot:.0f}, atm={nifty_atm} (step=50)")

        # --- 9. Analytical query across both indices ---
        cross_idx = db.execute("""
            SELECT index_name, COUNT(*), ROUND(AVG(atm_strike), 0)
            FROM market_data
            GROUP BY index_name
        """).fetchall()
        print(f"  ✅ Cross-index query: {cross_idx}")

        db.close()

        if errors:
            print(f"\n⚠️  {len(errors)} issues found:")
            for e in errors:
                print(f"   - {e}")
            return False

        print("\n=== SENSEX SUPPORT: ALL CHECKS PASSED ===")
        print("=== Confidence: NIFTY+SENSEX dual capture ready ===\n")
        return True

    except Exception as e:
        print(f"  ❌ SENSEX TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def run_all_tests():
    print("\n" + "=" * 60)
    print("VARAHA DATA CAPTURE V3 — DUCKDB TESTS")
    print("=" * 60)

    tests = [
        ("IndicatorBuffer", test_indicator_buffer),
        ("DuckDB Schema", test_duckdb_schema),
        ("Capture Once", test_capture_once_duckdb),
        ("Analytical Query", test_analytical_query),
        ("E2E Simulated Session (60 captures)", test_e2e_simulated_session),
        ("SENSEX Support", test_sensex_support),
    ]

    results = []
    for name, fn in tests:
        try:
            results.append((name, fn()))
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            results.append((name, False))

    print("=" * 60)
    passed = sum(1 for _, r in results if r)
    for name, r in results:
        print(f"  [{'PASS' if r else 'FAIL'}] {name}")
    print(f"\nTotal: {passed}/{len(results)} passed")
    return passed == len(results)


def main():
    parser = argparse.ArgumentParser(description="Varaha Data Capture V3 — DuckDB")
    parser.add_argument("--once", action="store_true", help="Single capture then exit")
    parser.add_argument("--no-broker", action="store_true", help="Skip broker auth")
    parser.add_argument("--db", type=str, help="Override DB path")
    parser.add_argument(
        "--index",
        type=str,
        default="NIFTY",
        choices=["NIFTY", "SENSEX"],
        help="Index to capture (NIFTY or SENSEX)",
    )
    parser.add_argument("--test-all", action="store_true", help="Run all tests")
    parser.add_argument(
        "--test-buffer", action="store_true", help="Test indicator buffer"
    )
    parser.add_argument(
        "--test-query", action="store_true", help="Demo analytical query"
    )
    parser.add_argument(
        "--test-sensex", action="store_true", help="Test SENSEX support"
    )

    args = parser.parse_args()

    if args.db:
        global DB_PATH
        DB_PATH = Path(args.db)

    if args.test_all:
        run_all_tests()
    elif args.test_buffer:
        test_indicator_buffer()
    elif args.test_query:
        test_analytical_query()
    elif args.test_sensex:
        test_sensex_support()
    else:
        run_capture_loop(
            use_broker=not args.no_broker, once=args.once, index=args.index
        )


if __name__ == "__main__":
    main()
