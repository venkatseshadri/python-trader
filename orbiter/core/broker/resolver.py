import os
import json
import datetime
import calendar
import logging
import time as _time
from typing import Dict, Optional, Any, List
from .master import ScripMaster

logger = logging.getLogger("ORBITER")

class ContractResolver:
    def __init__(self, scrip_master: ScripMaster, api=None):
        self.master = scrip_master
        self.api = api  # Broker API for dynamic queries

    def _get_option_rows(self, symbol: str, ltp: float, expiry: datetime.date, instrument: str, exchange_override: str = None):
        exchange = exchange_override or ("MCX" if instrument in ("OPTCOM", "FUTCOM", "OPTFUT", "FUTIDX") else "NFO")
        if not self.master.DERIVATIVE_LOADED: self.master.download_scrip_master(exchange)
        expiry_str = expiry.isoformat()
        
        # 🔭 TRACE: Log lookup details
        logger.debug(f"🔭 [_get_option_rows] symbol={symbol}, ltp={ltp}, instrument={instrument}, expiry={expiry_str}, exchange={exchange}")
        
        # First try exact symbol match from local file (futures_master.json)
        rows = [row for row in self.master.DERIVATIVE_OPTIONS if row.get("symbol") == symbol and row.get("instrument") == instrument and row.get("expiry") == expiry_str and row.get("exchange") == exchange]
        
        # If no rows, try with "-EQ" suffix removed (broker may store as RELIANCE-EQ)
        if not rows and symbol.endswith("-EQ"):
            rows = [row for row in self.master.DERIVATIVE_OPTIONS if row.get("symbol") == symbol[:-3] and row.get("instrument") == instrument and row.get("expiry") == expiry_str and row.get("exchange") == exchange]
            if rows:
                logger.debug(f"🔭 [_get_option_rows] Found {len(rows)} rows after removing -EQ suffix")
        
        # If still no rows, query broker API dynamically for options
        if not rows and self.api and instrument in ("OPTIDX", "OPTSTK"):
            logger.info(f"🔄 Querying broker API for {symbol} options (local file has no data)")
            rows = self._query_broker_options_api(symbol, ltp, expiry, instrument, exchange)
        
        # Check what symbols are available in master for this instrument
        if not rows:
            available_symbols = set(row.get("symbol") for row in self.master.DERIVATIVE_OPTIONS if row.get("instrument") == instrument)
            logger.error(f"❌ NO_DATA: No {instrument} data for {symbol}. Available: {list(available_symbols)[:10]}... Total: {len(available_symbols)}")
            return []
        
        return rows
    
    def _query_broker_options_api(self, symbol: str, ltp: float, expiry: datetime.date, instrument: str, exchange: str) -> List[Dict]:
        """Query broker API for options data on-the-fly"""
        rows = []
        try:
            # Get lot size from broker API using get_security_info on the future
            # First get the future token for this symbol
            future_symbol = f"{symbol.upper()}{expiry.strftime('%b%y').upper()}"
            future_info = self.api.get_security_info(exchange=exchange, token=future_symbol)
            
            lot_size = int(future_info.get('ls', 25)) if future_info else 25
            logger.debug(f"🔄 Got lot_size={lot_size} for {symbol} from broker API")
            
            # Generate strikes around ATM (ltp)
            strike_step = 50 if ltp > 2000 else 20 if ltp > 500 else 10
            strike_count = 10  # 10 above and 10 below ATM
            
            exp_str = expiry.strftime("%d%b%y").upper()
            
            for strike in range(int(ltp) - strike_count * strike_step, int(ltp) + strike_count * strike_step, strike_step):
                for opt_type in ["CE", "PE"]:
                    tsym = f"{symbol.upper()}{exp_str}{opt_type}{strike}"
                    rows.append({
                        "symbol": symbol.upper(),
                        "tradingsymbol": tsym,
                        "token": f"{symbol.upper()}_{exp_str}_{opt_type}_{strike}",
                        "exchange": exchange,
                        "instrument": instrument,
                        "expiry": expiry.isoformat(),
                        "strike": str(strike),
                        "option_type": opt_type,
                        "lot_size": lot_size
                    })
            
            logger.info(f"🔄 Queried broker API: generated {len(rows)} option contracts for {symbol} (ltp={ltp}, lot_size={lot_size})")
            
        except Exception as e:
            logger.error(f"❌ Broker API query failed for {symbol} options: {e}")
            return []
        
        return rows

    def _select_expiry(self, symbol: str, expiry_type: str, instrument: str, exchange_override: str = None) -> Optional[datetime.date]:
        exchange = exchange_override or ("MCX" if instrument in ("OPTCOM", "FUTCOM", "OPTFUT", "FUTIDX") else "NFO")
        
        # DEBUG: Log DERIVATIVE_OPTIONS status
        deriv_count = len(getattr(self.master, 'DERIVATIVE_OPTIONS', []))
        sample_symbols = list(set(r.get('symbol') for r in getattr(self.master, 'DERIVATIVE_OPTIONS', [])[:100]))
        logger.debug(f"🔍 _select_expiry: symbol={symbol}, instrument={instrument}, exchange={exchange}, deriv_count={deriv_count}, sample_symbols={sample_symbols[:5]}")
        
        try:
            last_refresh = getattr(self.master, "_last_refresh_time", 0) or 0
            if (not self.master.DERIVATIVE_LOADED) or (not self.master.DERIVATIVE_OPTIONS):
                if _time.time() - last_refresh > 300:
                    self.master.download_scrip_master(exchange)
                    setattr(self.master, "_last_refresh_time", _time.time())
        except Exception:
            pass

        def find_exp():
            exps = set()
            for row in self.master.DERIVATIVE_OPTIONS:
                if row.get("symbol") == symbol and row.get("instrument") == instrument and row.get("exchange") == exchange:
                    exp = self.master._parse_expiry_date(row.get("expiry"))
                    if exp: exps.add(exp)
            return exps
        
        expiries = find_exp()
        
        # 🔥 FALLBACK: If no expiries found in DERIVATIVE_OPTIONS, compute from current date
        if not expiries:
            logger.debug(f"🔍 No expiries in DERIVATIVE_OPTIONS for {symbol}, computing dynamically")
            today = datetime.date.today()
            # For weekly: find next Friday
            # For monthly: find last Thursday of month
            import calendar
            if "weekly" in expiry_type.lower() or "current" in expiry_type.lower():
                # Find next Friday (week expiry is typically Friday)
                days_until_friday = (4 - today.weekday()) % 7
                if days_until_friday == 0 and today.weekday() == 4:
                    days_until_friday = 7  # If today is Friday, go to next week
                next_friday = today + datetime.timedelta(days=days_until_friday if days_until_friday else 7)
                expiries = {next_friday}
            else:
                # Monthly: find last Thursday of current month
                last_day = calendar.monthrange(today.year, today.month)[1]
                last_thursday = None
                for d in range(last_day, 0, -1):
                    check_date = datetime.date(today.year, today.month, d)
                    if check_date.weekday() == 3:  # Thursday
                        last_thursday = check_date
                        break
                if last_thursday and last_thursday < today:
                    # Move to next month
                    if today.month == 12:
                        next_month = datetime.date(today.year + 1, 1, 1)
                    else:
                        next_month = datetime.date(today.year, today.month + 1, 1)
                    last_day = calendar.monthrange(next_month.year, next_month.month)[1]
                    for d in range(last_day, 0, -1):
                        check_date = datetime.date(next_month.year, next_month.month, d)
                        if check_date.weekday() == 3:
                            last_thursday = check_date
                            break
                if last_thursday:
                    expiries = {last_thursday}
        
        if not expiries: return None
        
        today = datetime.date.today()
        valid = sorted(d for d in expiries if d >= today)
        if not valid: return None

        base = expiry_type.lower()
        offset = 0
        if "+" in base:
            parts = base.split("+")
            base = parts[0]
            try: offset = int(parts[1])
            except: offset = 0

        if base == "weekly" or base == "current":
            return valid[offset] if offset < len(valid) else valid[-1]
        elif base == "monthly":
            monthlies = []
            for i in range(len(valid)):
                curr = valid[i]
                if i == len(valid) - 1 or valid[i+1].month != curr.month:
                    monthlies.append(curr)
            return monthlies[offset] if offset < len(monthlies) else monthlies[-1]

        if base == "next": return valid[1] if len(valid) > 1 else valid[0]
        if base == "far": return valid[2] if len(valid) > 2 else valid[-1]
        return valid[0]

    def resolve_option_symbol(self, symbol: str, ltp: float, option_type: str, strike_logic: str, expiry_type: str = "current", exchange: str = None) -> Dict[str, Any]:
        is_index = symbol.upper() in ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX")
        
        # BSE F&O symbol mapping (BFO uses different symbol names)
        bfo_symbol_map = {
            "SENSEX": "BSXOPT",
            "BANKEX": "BKXOPT"
        }
        
        # If BFO exchange, use mapped symbol
        if exchange and exchange.upper() == "BSE" and symbol.upper() in bfo_symbol_map:
            symbol = bfo_symbol_map[symbol.upper()]
        
        instrument = "OPTIDX" if is_index else "OPTSTK"
        logger.debug(f"🔍 [resolve_option_symbol] symbol={symbol}, is_index={is_index}, instrument={instrument}, expiry_type={expiry_type}, exchange={exchange}")
        
        expiry = self._select_expiry(symbol, expiry_type, instrument, exchange_override=exchange)
        if not expiry: 
            logger.debug(f"🔍 no_expiry_found_for_{symbol} (instrument={instrument}, expiry_type={expiry_type})")
            return {"ok": False, "reason": f"no_expiry_found_for_{symbol}"}
        
        rows = self._get_option_rows(symbol, ltp, expiry, instrument, exchange_override=exchange)
        logger.debug(f"🔍 [resolve_option_symbol] rows_count={len(rows)} for {symbol} expiry={expiry}")
        
        strikes = sorted({float(row.get("strike")) for row in rows if row.get("strike")})
        logger.debug(f"🔍 [resolve_option_symbol] strikes_count={len(strikes)} for {symbol}")
        
        if not strikes: 
            logger.debug(f"🔍 no_strikes for {symbol}: rows={len(rows)}, instrument={instrument}, expiry={expiry}")
            return {"ok": False, "reason": "no_strikes"}
        atm_strike = min(strikes, key=lambda s: abs(s - ltp))
        atm_idx = strikes.index(atm_strike)
        target_idx = atm_idx
        if "+" in strike_logic: target_idx += int(strike_logic.split("+")[1])
        elif "-" in strike_logic: target_idx -= int(strike_logic.split("-")[1])
        target_idx = max(0, min(len(strikes) - 1, target_idx))
        target_strike = strikes[target_idx]
        matches = [r for r in rows if r.get("option_type") == option_type.upper() and float(r.get("strike")) == target_strike]
        if not matches: return {"ok": False, "reason": "contract_not_found"}
        res = matches[0]
        return {
            "ok": True,
            "tradingsymbol": res["tradingsymbol"],
            "strike": res["strike"],
            "token": res["token"],
            "exchange": res["exchange"],
            "lot_size": int(res.get("lot_size", 0))
        }

    def get_credit_spread_contracts(self, symbol: str, ltp: float, side: str, hedge_steps: int = 4, expiry_type: str = "monthly", instrument: str = "OPTSTK") -> Dict[str, Any]:
        logger.debug(f"🔭 [Resolver.get_credit_spread_contracts] symbol={symbol}, ltp={ltp}, side={side}")
        is_put = (side.upper() == "PUT")
        atm_res = self.resolve_option_symbol(symbol, ltp, "PE" if is_put else "CE", "ATM", expiry_type)
        if not atm_res["ok"]: return atm_res
        hedge_logic = f"ATM-{hedge_steps}" if is_put else f"ATM+{hedge_steps}"
        hedge_res = self.resolve_option_symbol(symbol, ltp, "PE" if is_put else "CE", hedge_logic, expiry_type)
        if not hedge_res["ok"]: return hedge_res
        logger.debug(f"🔭 [Resolver.get_credit_spread_contracts] RETURNING: atm={atm_res['tradingsymbol']}, hedge={hedge_res['tradingsymbol']}")
        return {
            "ok": True,
            "side": side.upper(),
            "atm_symbol": atm_res["tradingsymbol"],
            "atm_token": atm_res["token"],
            "hedge_symbol": hedge_res["tradingsymbol"],
            "hedge_token": hedge_res["token"],
            "lot_size": atm_res["lot_size"]
        }

    def get_near_future(self, symbol: str, exchange: str, api) -> Optional[Dict]:
        """Get the nearest expiry future contract for a symbol."""
        try:
            exchange = exchange.upper()
            
            # Ensure derivatives are loaded
            if not self.master.DERIVATIVE_LOADED:
                self.master.download_scrip_master(exchange)
            
            instrument = "FUTIDX" if symbol.upper() in ("NIFTY", "BANKNIFTY", "SENSEX", "BANKEX") else "FUTCOM"
            
            futures = [r for r in self.master.DERIVATIVE_OPTIONS 
                      if r.get("symbol") == symbol.upper() 
                      and r.get("instrument") == instrument
                      and r.get("exchange") == exchange]
            
            if not futures:
                logger.warning(f"No futures found for {symbol} on {exchange}")
                return None
            
            # Sort by expiry date - parse expiry string to datetime for proper sorting
            from datetime import datetime
            def parse_expiry(expiry_str):
                if not expiry_str:
                    return datetime.max
                try:
                    # Format: 27FEB26 -> 27-Feb-2026
                    return datetime.strptime(expiry_str, "%d%b%y")
                except:
                    return datetime.max
            
            futures.sort(key=lambda x: parse_expiry(x.get("expiry", "")))
            nearest = futures[0]
            return {
                "ok": True,
                "symbol": nearest.get("symbol"),
                "expiry": nearest.get("expiry"),
                "token": nearest.get("token"),
                "tradingsymbol": nearest.get("tradingsymbol"),
                "exchange": nearest.get("exchange"),
                "lot_size": int(nearest.get("lotsize", 1))
            }
        except Exception as e:
            logger.error(f"Error getting near future: {e}")
            return None
