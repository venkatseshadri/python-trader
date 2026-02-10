#!/usr/bin/env python3
"""
ORBITER BrokerClient - Production Shoonya API Wrapper
VENKAT SESHADRI | FA333160 | LIVE Feb 2026
FIXED: All imports + symbol mapping ✅
"""

import sys
import os
import json
import requests
import zipfile
import io
import pandas as pd
import datetime
import calendar

# Add ShoonyaApi-py to path for api_helper import
shoonya_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ShoonyaApi-py')
sys.path.insert(0, shoonya_path)

from api_helper import ShoonyaApiPy
import yaml
import logging
from typing import Dict, Optional, Any
from NorenRestApiPy.NorenApi import position
from config.config import VERBOSE_LOGS

class BrokerClient:
    def __init__(self, config_path: str = '../cred.yml'):
        self.api = ShoonyaApiPy()
        self.socket_opened = False
        self.SYMBOLDICT: Dict[str, Dict[str, Any]] = {}
        self.TOKEN_TO_SYMBOL: Dict[str, str] = {}
        self.SYMBOL_TO_TOKEN: Dict[str, str] = {}
        self.TOKEN_TO_COMPANY: Dict[str, str] = {}  # ✅ Add company name mapping
        self.NFO_OPTIONS = []
        self.NFO_OPTIONS_LOADED = False
        self.span_cache_path = None
        self.span_cache = None
        
        # Load credentials
        # client.py is at: python-trader/orbiter/core/client.py
        # We need to find python-trader root (3 levels up)
        orbiter_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = os.path.abspath(os.path.join(orbiter_root, config_path))
        with open(self.config_file) as f:
            self.cred = yaml.load(f, Loader=yaml.FullLoader)
            
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("websocket").setLevel(logging.WARNING)
        print(f"🚀 BrokerClient initialized: {self.cred['user']}")
        self.verbose_logs = VERBOSE_LOGS

        self.trade_log_path = os.path.join(orbiter_root, 'logs', 'trade_calls.log')
        os.makedirs(os.path.dirname(self.trade_log_path), exist_ok=True)
        self.trade_logger = logging.getLogger("trade_calls")
        self.trade_logger.setLevel(logging.INFO)
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == self.trade_log_path for h in self.trade_logger.handlers):
            handler = logging.FileHandler(self.trade_log_path)
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            self.trade_logger.addHandler(handler)
        
        # 🔥 CRITICAL: Load FULL symbol mapping
        self.load_symbol_mapping()

    def set_span_cache_path(self, path: str):
        self.span_cache_path = path

    def load_span_cache(self):
        if not self.span_cache_path:
            return
        if self.span_cache is not None:
            return
        try:
            if os.path.exists(self.span_cache_path):
                with open(self.span_cache_path, 'r') as f:
                    self.span_cache = json.load(f)
            else:
                self.span_cache = {}
        except Exception:
            self.span_cache = {}

    def save_span_cache(self):
        if not self.span_cache_path or self.span_cache is None:
            return
        try:
            os.makedirs(os.path.dirname(self.span_cache_path), exist_ok=True)
            with open(self.span_cache_path, 'w') as f:
                json.dump(self.span_cache, f)
        except Exception:
            pass

    def _parse_expiry_date(self, raw: str) -> Optional[datetime.date]:
        if not raw:
            return None
        for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None

    def _is_last_thursday(self, d: datetime.date) -> bool:
        last_day = calendar.monthrange(d.year, d.month)[1]
        last_date = datetime.date(d.year, d.month, last_day)
        while last_date.weekday() != 3:
            last_date -= datetime.timedelta(days=1)
        return d == last_date

    def load_nfo_symbol_mapping(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_file = os.path.join(base_dir, 'data', 'nfo_symbol_map.json')

        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                self.NFO_OPTIONS = data.get('options', [])
                self.NFO_OPTIONS_LOADED = True
                print(f"✅ Loaded {len(self.NFO_OPTIONS):,} NFO option symbols")
                return
            except Exception as e:
                print(f"⚠️ NFO cache invalid: {e}")

        print("📥 DOWNLOADING NFO SYMBOLS...")
        self.download_nfo_scrip_master()

    def download_nfo_scrip_master(self):
        print("📥 Downloading NFO_symbols.txt.zip...")
        options = []
        try:
            r = requests.get("https://api.shoonya.com/NFO_symbols.txt.zip", timeout=10)
            r.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open("NFO_symbols.txt") as f:
                    lines = f.readlines()
                    headers = lines[0].decode().strip().rstrip(',').split(',')

                    # Column indexes (fallback to None if not present)
                    def col_idx(name: str) -> Optional[int]:
                        return headers.index(name) if name in headers else None

                    exch_i = col_idx("Exchange")
                    token_i = col_idx("Token")
                    lot_i = col_idx("LotSize")
                    sym_i = col_idx("Symbol")
                    tsym_i = col_idx("TradingSymbol")
                    inst_i = col_idx("Instrument")
                    exp_i = col_idx("Expiry")
                    strike_i = col_idx("StrikePrice")
                    opt_i = col_idx("OptionType")

                    for line in lines[1:]:
                        parts = line.decode().strip().rstrip(',').split(',')
                        if not parts or len(parts) <= max(filter(None, [sym_i, tsym_i, inst_i])):
                            continue

                        instrument = parts[inst_i].strip() if inst_i is not None else ''
                        if instrument not in ("OPTSTK", "OPTIDX"):
                            continue

                        symbol = parts[sym_i].strip() if sym_i is not None else ''
                        tsym = parts[tsym_i].strip() if tsym_i is not None else ''
                        expiry_raw = parts[exp_i].strip() if exp_i is not None else ''
                        expiry = self._parse_expiry_date(expiry_raw)
                        strike_raw = parts[strike_i].strip() if strike_i is not None else ''
                        opt_type = parts[opt_i].strip() if opt_i is not None else ''
                        lot_raw = parts[lot_i].strip() if lot_i is not None else '0'

                        try:
                            strike = float(strike_raw) if strike_raw else 0.0
                            lot_size = int(float(lot_raw)) if lot_raw else 0
                        except ValueError:
                            continue

                        if not symbol or not tsym or not expiry or strike <= 0 or opt_type not in ("PE", "CE"):
                            continue

                        options.append({
                            'symbol': symbol,
                            'tradingsymbol': tsym,
                            'instrument': instrument,
                            'expiry': expiry.isoformat(),
                            'strike': strike,
                            'option_type': opt_type,
                            'lot_size': lot_size,
                            'token': parts[token_i].strip() if token_i is not None else ''
                        })

            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, 'data')
            os.makedirs(data_dir, exist_ok=True)
            cache_file = os.path.join(data_dir, 'nfo_symbol_map.json')
            with open(cache_file, 'w') as f:
                json.dump({'options': options}, f)

            self.NFO_OPTIONS = options
            self.NFO_OPTIONS_LOADED = True
            print(f"✅ Cached {len(options):,} NFO option symbols at {cache_file}")

        except Exception as e:
            print(f"⚠️ NFO download failed: {e}")

    def _get_option_rows(self, symbol: str, expiry: datetime.date, instrument: str = "OPTSTK"):
        if not self.NFO_OPTIONS_LOADED:
            self.load_nfo_symbol_mapping()

        expiry_str = expiry.isoformat()
        return [
            row for row in self.NFO_OPTIONS
            if row.get('symbol') == symbol and row.get('instrument') == instrument and row.get('expiry') == expiry_str
        ]

    def _select_expiry(self, symbol: str, expiry_type: str = "monthly", instrument: str = "OPTSTK") -> Optional[datetime.date]:
        if not self.NFO_OPTIONS_LOADED:
            self.load_nfo_symbol_mapping()

        expiries = set()
        for row in self.NFO_OPTIONS:
            if row.get('symbol') != symbol or row.get('instrument') != instrument:
                continue
            exp = self._parse_expiry_date(row.get('expiry'))
            if exp:
                expiries.add(exp)

        if not expiries:
            return None

        today = datetime.date.today()
        valid = sorted(d for d in expiries if d >= today)
        if not valid:
            return None

        if expiry_type == "monthly":
            monthly = [d for d in valid if self._is_last_thursday(d)]
            return monthly[0] if monthly else valid[0]

        return valid[0]

    def _get_atm_strike(self, symbol: str, expiry: datetime.date, ltp: float, instrument: str = "OPTSTK") -> Optional[float]:
        rows = self._get_option_rows(symbol, expiry, instrument=instrument)
        strikes = sorted({row.get('strike') for row in rows if row.get('strike')})
        if not strikes:
            return None
        return min(strikes, key=lambda s: abs(s - ltp))

    def _get_strike_step(self, strikes):
        if not strikes or len(strikes) < 2:
            return None
        diffs = sorted({round(strikes[i + 1] - strikes[i], 2) for i in range(len(strikes) - 1) if strikes[i + 1] > strikes[i]})
        return diffs[0] if diffs else None

    def _find_option_symbol(self, symbol: str, expiry: datetime.date, strike: float, option_type: str, instrument: str = "OPTSTK"):
        rows = self._get_option_rows(symbol, expiry, instrument=instrument)
        for row in rows:
            if row.get('strike') == strike and row.get('option_type') == option_type:
                return row
        return None

    def get_credit_spread_contracts(self, symbol: str, ltp: float, side: str,
                                    hedge_steps: int = 4, expiry_type: str = "monthly",
                                    instrument: str = "OPTSTK") -> Dict[str, Any]:
        """Resolve contract symbols for a credit spread without placing orders."""
        if not self.NFO_OPTIONS_LOADED:
            self.load_nfo_symbol_mapping()

        expiry = self._select_expiry(symbol, expiry_type=expiry_type, instrument=instrument)
        if not expiry:
            return {'ok': False, 'reason': 'no_expiry'}

        rows = self._get_option_rows(symbol, expiry, instrument=instrument)
        strikes = sorted({row.get('strike') for row in rows if row.get('strike')})
        if not strikes:
            return {'ok': False, 'reason': 'no_strikes'}

        atm_strike = self._get_atm_strike(symbol, expiry, ltp, instrument=instrument)
        step = self._get_strike_step(strikes)
        if atm_strike is None or not step:
            return {'ok': False, 'reason': 'no_atm_or_step'}

        side_key = side.upper()
        if side_key == 'PUT':
            hedge_strike = round(atm_strike - hedge_steps * step, 2)
            hedge_row = self._find_option_symbol(symbol, expiry, hedge_strike, 'PE', instrument=instrument)
            atm_row = self._find_option_symbol(symbol, expiry, atm_strike, 'PE', instrument=instrument)
        else:
            hedge_strike = round(atm_strike + hedge_steps * step, 2)
            hedge_row = self._find_option_symbol(symbol, expiry, hedge_strike, 'CE', instrument=instrument)
            atm_row = self._find_option_symbol(symbol, expiry, atm_strike, 'CE', instrument=instrument)

        if not hedge_row or not atm_row:
            return {'ok': False, 'reason': 'option_symbol_not_found'}

        lot_size = int(atm_row.get('lot_size') or 0)
        if lot_size <= 0:
            return {'ok': False, 'reason': 'invalid_lot_size'}

        return {
            'ok': True,
            'expiry': expiry.isoformat(),
            'atm_strike': atm_strike,
            'hedge_strike': hedge_strike,
            'lot_size': lot_size,
            'atm_symbol': atm_row['tradingsymbol'],
            'hedge_symbol': hedge_row['tradingsymbol'],
            'side': side_key
        }

    def _find_option_by_tradingsymbol(self, tradingsymbol: str) -> Optional[Dict[str, Any]]:
        if not self.NFO_OPTIONS_LOADED:
            self.load_nfo_symbol_mapping()
        for row in self.NFO_OPTIONS:
            if row.get('tradingsymbol') == tradingsymbol:
                return row
        return None

    def calculate_span_for_spread(self, spread: Dict[str, Any], product_type: str = "I", haircut: float = 0.20) -> Dict[str, Any]:
        """Calculate SPAN/exposure margin for a 2-leg spread using Shoonya span_calculator."""
        atm_symbol = spread.get('atm_symbol')
        hedge_symbol = spread.get('hedge_symbol')
        lot_size = spread.get('lot_size')

        if not atm_symbol or not hedge_symbol or not lot_size:
            return {'ok': False, 'reason': 'missing_spread_details'}

        atm_row = self._find_option_by_tradingsymbol(atm_symbol)
        hedge_row = self._find_option_by_tradingsymbol(hedge_symbol)
        if not atm_row or not hedge_row:
            return {'ok': False, 'reason': 'option_symbol_not_found'}

        def _format_span_expiry(raw: Optional[str]) -> str:
            if not raw:
                return ""
            try:
                parsed = self._parse_expiry_date(raw)
                if parsed:
                    return parsed.strftime("%d-%b-%Y").upper()
            except Exception:
                pass
            return str(raw).strip()

        def _format_span_strike(raw: Any) -> str:
            if raw is None:
                return ""
            try:
                strike = float(raw)
                if strike.is_integer():
                    return str(int(strike))
                return str(strike)
            except Exception:
                return str(raw).strip()

        def _pos_from_row(row: Dict[str, Any], side: str) -> position:
            pos = position()
            pos.prd = "M" if product_type == "I" else product_type
            pos.exch = "NFO"
            pos.instname = row.get('instrument') or "OPTSTK"
            pos.symname = row.get('symbol')
            pos.exd = _format_span_expiry(row.get('expiry'))
            pos.optt = row.get('option_type')
            pos.strprc = _format_span_strike(row.get('strike'))
            qty = int(lot_size)
            if side == "B":
                pos.buyqty = qty
                pos.sellqty = 0
                pos.netqty = qty
            else:
                pos.buyqty = 0
                pos.sellqty = qty
                pos.netqty = -qty
            return pos

        positionlist = [
            _pos_from_row(hedge_row, "B"),
            _pos_from_row(atm_row, "S"),
        ]

        actid = self.cred.get('user')
        try:
            ret = self.api.span_calculator(actid, positionlist)
        except Exception as exc:
            return {'ok': False, 'reason': f'span_error:{exc}'}

        if not isinstance(ret, dict):
            return {'ok': False, 'reason': 'span_invalid_response'}
        if ret.get('stat') and ret.get('stat') != 'Ok':
            return {'ok': False, 'reason': f"span_not_ok:{ret.get('emsg', '')}"}

        span = float(ret.get('span', 0.0) or 0.0)
        expo = float(ret.get('expo', 0.0) or 0.0)
        if span == 0.0 and expo == 0.0:
            return {'ok': False, 'reason': 'span_zero'}
        total_margin = span + expo
        pledged_required = total_margin / (1.0 - haircut) if total_margin else 0.0

        return {
            'ok': True,
            'span': span,
            'expo': expo,
            'total_margin': total_margin,
            'haircut': haircut,
            'pledged_required': pledged_required
        }

    def place_put_credit_spread(self, symbol: str, ltp: float, hedge_steps: int = 4,
                                expiry_type: str = "monthly", execute: bool = False,
                                product_type: str = "I", price_type: str = "MKT",
                                instrument: str = "OPTSTK") -> Dict[str, Any]:
        if not self.NFO_OPTIONS_LOADED:
            self.load_nfo_symbol_mapping()

        expiry = self._select_expiry(symbol, expiry_type=expiry_type, instrument=instrument)
        if not expiry:
            return {'ok': False, 'reason': 'no_expiry'}

        rows = self._get_option_rows(symbol, expiry, instrument=instrument)
        strikes = sorted({row.get('strike') for row in rows if row.get('strike')})
        if not strikes:
            return {'ok': False, 'reason': 'no_strikes'}

        atm_strike = self._get_atm_strike(symbol, expiry, ltp, instrument=instrument)
        step = self._get_strike_step(strikes)
        if atm_strike is None or not step:
            return {'ok': False, 'reason': 'no_atm_or_step'}

        hedge_strike = round(atm_strike - hedge_steps * step, 2)
        hedge_row = self._find_option_symbol(symbol, expiry, hedge_strike, 'PE', instrument=instrument)
        atm_row = self._find_option_symbol(symbol, expiry, atm_strike, 'PE', instrument=instrument)

        if not hedge_row or not atm_row:
            return {'ok': False, 'reason': 'option_symbol_not_found'}

        lot_size = int(atm_row.get('lot_size') or 0)
        if lot_size <= 0:
            return {'ok': False, 'reason': 'invalid_lot_size'}

        if not execute:
            # Dry-run mode: skip live orders, return resolved contract details for logging.
            self.trade_logger.info(
                "sim_order side=B exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_put_spread_hedge",
                hedge_row['tradingsymbol'], lot_size, product_type, price_type
            )
            self.trade_logger.info(
                "sim_order side=S exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_put_spread_sell",
                atm_row['tradingsymbol'], lot_size, product_type, price_type
            )
            return {
                'ok': True,
                'expiry': expiry.isoformat(),
                'atm_strike': atm_strike,
                'hedge_strike': hedge_strike,
                'lot_size': lot_size,
                'atm_symbol': atm_row['tradingsymbol'],
                'hedge_symbol': hedge_row['tradingsymbol'],
                'dry_run': True
            }

        self.trade_logger.info(
            "sim_order side=B exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_put_spread_hedge",
            hedge_row['tradingsymbol'], lot_size, product_type, price_type
        )
        self.trade_logger.info(
            "sim_order side=S exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_put_spread_sell",
            atm_row['tradingsymbol'], lot_size, product_type, price_type
        )

        # Buy hedge first
        buy_resp = self.api.place_order(
            buy_or_sell='B',
            product_type=product_type,
            exchange='NFO',
            tradingsymbol=hedge_row['tradingsymbol'],
            quantity=lot_size,
            discloseqty=0,
            price_type=price_type,
            price=0,
            trigger_price=None,
            retention='DAY',
            remarks='orb_put_spread_hedge'
        )
        self.trade_logger.info(
            "order_call side=B exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_put_spread_hedge resp=%s",
            hedge_row['tradingsymbol'], lot_size, product_type, price_type, buy_resp
        )

        if not buy_resp or buy_resp.get('stat') != 'Ok':
            return {'ok': False, 'reason': 'hedge_order_failed', 'buy_resp': buy_resp}

        sell_resp = self.api.place_order(
            buy_or_sell='S',
            product_type=product_type,
            exchange='NFO',
            tradingsymbol=atm_row['tradingsymbol'],
            quantity=lot_size,
            discloseqty=0,
            price_type=price_type,
            price=0,
            trigger_price=None,
            retention='DAY',
            remarks='orb_put_spread_sell'
        )
        self.trade_logger.info(
            "order_call side=S exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_put_spread_sell resp=%s",
            atm_row['tradingsymbol'], lot_size, product_type, price_type, sell_resp
        )

        if not sell_resp or sell_resp.get('stat') != 'Ok':
            return {'ok': False, 'reason': 'sell_order_failed', 'buy_resp': buy_resp, 'sell_resp': sell_resp}

        return {
            'ok': True,
            'expiry': expiry.isoformat(),
            'atm_strike': atm_strike,
            'hedge_strike': hedge_strike,
            'lot_size': lot_size,
            'buy_resp': buy_resp,
            'sell_resp': sell_resp,
            'atm_symbol': atm_row['tradingsymbol'],
            'hedge_symbol': hedge_row['tradingsymbol']
        }

    def place_call_credit_spread(self, symbol: str, ltp: float, hedge_steps: int = 4,
                                 expiry_type: str = "monthly", execute: bool = False,
                                 product_type: str = "I", price_type: str = "MKT",
                                 instrument: str = "OPTSTK") -> Dict[str, Any]:
        if not self.NFO_OPTIONS_LOADED:
            self.load_nfo_symbol_mapping()

        expiry = self._select_expiry(symbol, expiry_type=expiry_type, instrument=instrument)
        if not expiry:
            return {'ok': False, 'reason': 'no_expiry'}

        rows = self._get_option_rows(symbol, expiry, instrument=instrument)
        strikes = sorted({row.get('strike') for row in rows if row.get('strike')})
        if not strikes:
            return {'ok': False, 'reason': 'no_strikes'}

        atm_strike = self._get_atm_strike(symbol, expiry, ltp, instrument=instrument)
        step = self._get_strike_step(strikes)
        if atm_strike is None or not step:
            return {'ok': False, 'reason': 'no_atm_or_step'}

        hedge_strike = round(atm_strike + hedge_steps * step, 2)
        hedge_row = self._find_option_symbol(symbol, expiry, hedge_strike, 'CE', instrument=instrument)
        atm_row = self._find_option_symbol(symbol, expiry, atm_strike, 'CE', instrument=instrument)

        if not hedge_row or not atm_row:
            return {'ok': False, 'reason': 'option_symbol_not_found'}

        lot_size = int(atm_row.get('lot_size') or 0)
        if lot_size <= 0:
            return {'ok': False, 'reason': 'invalid_lot_size'}

        if not execute:
            self.trade_logger.info(
                "sim_order side=B exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_call_spread_hedge",
                hedge_row['tradingsymbol'], lot_size, product_type, price_type
            )
            self.trade_logger.info(
                "sim_order side=S exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_call_spread_sell",
                atm_row['tradingsymbol'], lot_size, product_type, price_type
            )
            return {
                'ok': True,
                'expiry': expiry.isoformat(),
                'atm_strike': atm_strike,
                'hedge_strike': hedge_strike,
                'lot_size': lot_size,
                'atm_symbol': atm_row['tradingsymbol'],
                'hedge_symbol': hedge_row['tradingsymbol'],
                'dry_run': True
            }

        self.trade_logger.info(
            "sim_order side=B exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_call_spread_hedge",
            hedge_row['tradingsymbol'], lot_size, product_type, price_type
        )
        self.trade_logger.info(
            "sim_order side=S exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_call_spread_sell",
            atm_row['tradingsymbol'], lot_size, product_type, price_type
        )

        buy_resp = self.api.place_order(
            buy_or_sell='B',
            product_type=product_type,
            exchange='NFO',
            tradingsymbol=hedge_row['tradingsymbol'],
            quantity=lot_size,
            discloseqty=0,
            price_type=price_type,
            price=0,
            trigger_price=None,
            retention='DAY',
            remarks='orb_call_spread_hedge'
        )
        self.trade_logger.info(
            "order_call side=B exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_call_spread_hedge resp=%s",
            hedge_row['tradingsymbol'], lot_size, product_type, price_type, buy_resp
        )

        if not buy_resp or buy_resp.get('stat') != 'Ok':
            return {'ok': False, 'reason': 'hedge_order_failed', 'buy_resp': buy_resp}

        sell_resp = self.api.place_order(
            buy_or_sell='S',
            product_type=product_type,
            exchange='NFO',
            tradingsymbol=atm_row['tradingsymbol'],
            quantity=lot_size,
            discloseqty=0,
            price_type=price_type,
            price=0,
            trigger_price=None,
            retention='DAY',
            remarks='orb_call_spread_sell'
        )
        self.trade_logger.info(
            "order_call side=S exchange=NFO symbol=%s qty=%s product=%s price_type=%s price=0 remarks=orb_call_spread_sell resp=%s",
            atm_row['tradingsymbol'], lot_size, product_type, price_type, sell_resp
        )

        if not sell_resp or sell_resp.get('stat') != 'Ok':
            return {'ok': False, 'reason': 'sell_order_failed', 'buy_resp': buy_resp, 'sell_resp': sell_resp}

        return {
            'ok': True,
            'expiry': expiry.isoformat(),
            'atm_strike': atm_strike,
            'hedge_strike': hedge_strike,
            'lot_size': lot_size,
            'buy_resp': buy_resp,
            'sell_resp': sell_resp,
            'atm_symbol': atm_row['tradingsymbol'],
            'hedge_symbol': hedge_row['tradingsymbol']
        }
    
    def login(self, factor2_override: Optional[str] = None) -> bool:
        print("🔐 Authenticating...")
        # Prompt for fresh 2FA every run and persist it to cred.yml
        try:
            current = self.cred.get('factor2', '')
            new2 = (factor2_override or "").strip()
            if not new2:
                new2 = input(f"Enter 2FA (current: {current}) or press Enter to keep: ").strip()
            if new2:
                self.cred['factor2'] = new2
                try:
                    with open(self.config_file, 'w') as f:
                        yaml.dump(self.cred, f)
                    print(f"🔒 Updated 2FA in {self.config_file}")
                except Exception as e:
                    print(f"⚠️ Failed to save credentials: {e}")
        except Exception:
            # non-interactive environment: proceed with existing value
            pass
        ret = self.api.login(
            userid=self.cred['user'],
            password=self.cred['pwd'],
            twoFA=self.cred['factor2'],
            vendor_code=self.cred['vc'],
            api_secret=self.cred['apikey'],
            imei=self.cred['imei']
        )
        if not ret or str(ret.get('stat', '')).lower() != 'ok':
            reason = ''
            if isinstance(ret, dict):
                reason = ret.get('emsg') or ret.get('reason') or ''
            print(f"❌ Login failed{': ' + reason if reason else ''}")
            return False
        # 🔥 CRITICAL: Ensure symbol mapping is loaded before WebSocket data
        if not self.TOKEN_TO_SYMBOL:
            print("📥 Symbol mapping not loaded, loading now...")
            self.load_symbol_mapping()
        return True
    
    def start_live_feed(self, symbols: list):
        """🚀 PRODUCTION WEBSOCKET - FULLY WORKING"""
        print(f"🚀 Starting WS for {len(symbols)} symbols...")
        self.symbols = symbols  # 🔥 FIXED: Store symbols
        
        def on_tick(message):
            if 'lp' not in message: return
            token = str(message.get('tk', ''))
            exch = message.get('e', 'NSE')
            key = f"{exch}|{token}"
            
            symbol = self.get_symbol(token)
            self.SYMBOLDICT[key] = {
                **message,
                'symbol': symbol,
                't': symbol,  # ✅ Add 't' field for company name (used by safe_ltp)
                'company_name': self.get_company_name(token),  # ✅ Full company name
                'token': token,
                'exchange': exch,
                'ltp': float(message['lp']),
                'high': float(message.get('h', 0)),
                'low': float(message.get('l', 0)),
                'volume': int(message.get('v', 0))
            }
            
            symbol = self.get_symbol(token)
            if self.verbose_logs:
                print(f"📊 LIVE: {symbol} ({token}): ₹{message['lp']}")
        
        def on_open():
            self.socket_opened = True
            print("🚀 WEBSOCKET LIVE!")
            self.api.subscribe(self.symbols, feed_type='d')  # ✅ symbols defined
        
        self.api.start_websocket(
            subscribe_callback=on_tick,
            socket_open_callback=on_open,
            order_update_callback=lambda x: print("📋 ORDER:", x)
        )
    
    def get_ltp(self, exch_token: str) -> Optional[float]:
        """🔥 FIXED: Use 'ltp' not 'lp'"""
        data = self.SYMBOLDICT.get(exch_token, {})
        return data.get('ltp') if data else None

    def get_option_ltp_by_symbol(self, tradingsymbol: str) -> Optional[float]:
        """Fetch option LTP using NFO token resolved from tradingsymbol."""
        if not tradingsymbol:
            return None
        row = self._find_option_by_tradingsymbol(tradingsymbol)
        token = row.get('token') if row else None
        if not token:
            return None
        try:
            quote = self.api.get_quotes(exchange='NFO', token=token)
        except Exception:
            return None
        if not quote:
            return None
        raw = quote.get('lp') or quote.get('ltp')
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    
    def get_dk_levels(self, exch_token: str) -> Dict[str, float]:
        """🎯 Day's Key Levels for ORB"""
        data = self.SYMBOLDICT.get(exch_token, {})
        return {
            'ltp': data.get('ltp', 0),
            'high': data.get('high', 0),
            'low': data.get('low', 0)
        }
    
    def close(self):
        if self.socket_opened:
            self.api.close_websocket()
            print("🔌 Connection closed")

    # 🔥 SYMBOL MAPPING (unchanged - perfect)
    def load_symbol_mapping(self):
        # ✅ Use absolute path based on script location
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_file = os.path.join(base_dir, 'data', 'nse_token_map.json')
        
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    self.TOKEN_TO_SYMBOL = data['token_to_symbol']
                    self.SYMBOL_TO_TOKEN = data['symbol_to_token']
                    self.TOKEN_TO_COMPANY = data.get('token_to_company', {})  # ✅ Load company names
                    
                    if self.verbose_logs:
                        print("🔍 SAMPLE MAPPING:")
                        for token in ['1394', '1660', '3045']:
                            symbol = self.TOKEN_TO_SYMBOL.get(token, 'MISSING')
                            company = self.TOKEN_TO_COMPANY.get(token, symbol)
                            print(f"   NSE|{token} → {symbol} ({company})")
                    
                    print(f"✅ Loaded {len(self.TOKEN_TO_SYMBOL):,} symbols")
                    return
            except Exception as e:
                print(f"⚠️ Cache invalid: {e}")
        
        print("📥 DOWNLOADING FRESH SYMBOLS...")
        self.download_scrip_master()
    
    def download_scrip_master(self):
        """🔥 FIXED: Handle Shoonya NSE_symbols.txt CSV format (comma-separated, not pipes!)"""
        print("📥 Downloading NSE_symbols.txt.zip...")
        try:
            r = requests.get("https://api.shoonya.com/NSE_symbols.txt.zip", timeout=10)
            r.raise_for_status()
            
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open("NSE_symbols.txt") as f:
                    # 🔥 CSV FORMAT: Exchange,Token,LotSize,Symbol,TradingSymbol,Instrument,TickSize,...
                    lines = f.readlines()
                    headers = lines[0].decode().strip().rstrip(',').split(',')  # ✅ COMMA-separated!
                    
                    if self.verbose_logs:
                        print(f"🔍 DEBUG: Found {len(headers)} columns")
                    
                    # CSV columns: [Exchange, Token, LotSize, Symbol, TradingSymbol, Instrument, TickSize, ...]
                    token_idx = 1  # Token is column 1
                    symbol_idx = 3  # Symbol (company name) is column 3
                    tsym_idx = 4    # TradingSymbol is column 4
                    
                    self.TOKEN_TO_SYMBOL = {}
                    self.SYMBOL_TO_TOKEN = {}
                    token_to_company = {}  # ✅ Track company names
                    
                    for i, line in enumerate(lines[1:]):  # Skip header
                        parts = line.decode().strip().rstrip(',').split(',')
                        if len(parts) > max(token_idx, symbol_idx, tsym_idx):
                            try:
                                token = str(int(parts[token_idx].strip()))
                                company_name = parts[symbol_idx].strip()  # e.g., "RELIANCE"
                                tsym = parts[tsym_idx].strip()  # e.g., "RELIANCE-EQ"
                                
                                # Extract clean symbol (remove -EQ suffixes)
                                symbol = company_name.replace(' ', '')  # Use company name as symbol
                                
                                self.TOKEN_TO_SYMBOL[token] = symbol
                                self.SYMBOL_TO_TOKEN[symbol] = token
                                
                                # For company name, use the full trading symbol or company
                                if company_name:
                                    token_to_company[token] = company_name
                                
                                # 🔍 DEBUG: Show first few extracted
                                if self.verbose_logs and i < 5:
                                    print(f"🔍 Row {i}: token={token}, symbol={symbol}, company={company_name}")
                            except (ValueError, IndexError) as e:
                                continue  # Skip bad rows
                    
            # ✅ Use absolute path for saving
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, 'data')
            os.makedirs(data_dir, exist_ok=True)
            cache_file = os.path.join(data_dir, 'nse_token_map.json')
            
            cache_data = {
                'token_to_symbol': self.TOKEN_TO_SYMBOL,
                'symbol_to_token': self.SYMBOL_TO_TOKEN,
                'token_to_company': token_to_company
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            print(f"✅ Cached {len(self.TOKEN_TO_SYMBOL):,} symbols at {cache_file}")
            
        except Exception as e:
            print(f"⚠️ Download failed: {e}, using fallback mapping...")
            self.TOKEN_TO_SYMBOL = self.get_fallback_mapping()
  
    def get_fallback_mapping(self) -> Dict[str, str]:
        """✅ Comprehensive fallback with company names - from login watchlist data"""
        fallback = {
            '2885': 'RELIANCE',
            '11630': 'NTPC', 
            '3045': 'SBIN',
            '317': 'BAJFINANCE', 
            '1333': 'HDFCBANK', 
            '1660': 'ITC',
            '1394': 'HINDUNILVR',
            '9819': 'HAVELLS',
            '2475': 'ONGC',
            '14977': 'POWERGRID',
            '17881': 'DBCORP',
            '759084': 'URBANCO',
            '3703': 'VIPIND',
            '15355': 'RECLTD',
            '14299': 'PFC',
            '383': 'BEL',
            '526': 'EXIDEIND',
        }
        
        # ✅ Create TOKEN_TO_COMPANY mapping
        self.TOKEN_TO_COMPANY = {
            '2885': 'RELIANCE INDUSTRIES LTD',
            '11630': 'NTPC LTD',
            '3045': 'STATE BANK OF INDIA',
            '317': 'BAJAJ FINANCE LIMITED',
            '1333': 'HDFC BANK LTD',
            '1660': 'ITC LTD',
            '1394': 'HINDUSTAN UNILEVER LTD.',
            '9819': 'HAVELLS INDIA LIMITED',
            '2475': 'OIL AND NATURAL GAS CORP.',
            '14977': 'POWER GRID CORP. LTD.',
            '17881': 'D.B.CORP LTD',
            '759084': 'URBAN COMPANY LIMITED',
            '3703': 'VIP INDUSTRIES LTD',
            '15355': 'REC LIMITED',
            '14299': 'POWER FIN CORP LTD.',
            '383': 'BHARAT ELECTRONICS LTD',
            '526': 'EXIDE INDUSTRIES LIMITED',
        }
        
        self.SYMBOL_TO_TOKEN.update({v: k for k, v in fallback.items()})
        return fallback
    
    def get_symbol(self, token: str) -> str:
        return self.TOKEN_TO_SYMBOL.get(token, f"NSE|{token}")
    
    def get_company_name(self, token: str) -> str:
        """✅ Get company name for token, fallback to symbol"""
        return self.TOKEN_TO_COMPANY.get(token, self.get_symbol(token))
    
    def get_token(self, symbol: str) -> str:
        return self.SYMBOL_TO_TOKEN.get(symbol.upper(), symbol)
