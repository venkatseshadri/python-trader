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
    def __init__(self, scrip_master: ScripMaster):
        self.master = scrip_master

    def _get_option_rows(self, symbol: str, expiry: datetime.date, instrument: str, exchange_override: str = None):
        exchange = exchange_override or ("MCX" if instrument in ("OPTCOM", "FUTCOM", "OPTFUT", "FUTIDX") else "NFO")
        if not self.master.DERIVATIVE_LOADED: self.master.download_scrip_master(exchange)
        expiry_str = expiry.isoformat()
        return [row for row in self.master.DERIVATIVE_OPTIONS if row.get("symbol") == symbol and row.get("instrument") == instrument and row.get("expiry") == expiry_str and row.get("exchange") == exchange]

    def _select_expiry(self, symbol: str, expiry_type: str, instrument: str, exchange_override: str = None) -> Optional[datetime.date]:
        exchange = exchange_override or ("MCX" if instrument in ("OPTCOM", "FUTCOM", "OPTFUT", "FUTIDX") else "NFO")
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
        instrument = "OPTIDX" if is_index else "OPTSTK"
        expiry = self._select_expiry(symbol, expiry_type, instrument, exchange_override=exchange)
        if not expiry: return {"ok": False, "reason": f"no_expiry_found_for_{symbol}"}
        rows = self._get_option_rows(symbol, expiry, instrument, exchange_override=exchange)
        strikes = sorted({float(row.get("strike")) for row in rows if row.get("strike")})
        if not strikes: return {"ok": False, "reason": "no_strikes"}
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
            "lot_size": int(res.get("lotsize", 0))
        }

    def get_credit_spread_contracts(self, symbol: str, ltp: float, side: str, hedge_steps: int = 4, expiry_type: str = "monthly", instrument: str = "OPTSTK") -> Dict[str, Any]:
        is_put = (side.upper() == "PUT")
        atm_res = self.resolve_option_symbol(symbol, ltp, "PE" if is_put else "CE", "ATM", expiry_type)
        if not atm_res["ok"]: return atm_res
        hedge_logic = f"ATM-{hedge_steps}" if is_put else f"ATM+{hedge_steps}"
        hedge_res = self.resolve_option_symbol(symbol, ltp, "PE" if is_put else "CE", hedge_logic, expiry_type)
        if not hedge_res["ok"]: return hedge_res
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
