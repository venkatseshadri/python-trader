import os
import json
import datetime
import calendar
import time as _time
from typing import Dict, Optional, Any, List
from .master import ScripMaster

class ContractResolver:
    def __init__(self, scrip_master: ScripMaster):
        self.master = scrip_master

    def _is_last_thursday(self, d: datetime.date) -> bool:
        last_day = calendar.monthrange(d.year, d.month)[1]
        last_date = datetime.date(d.year, d.month, last_day)
        while last_date.weekday() != 3: last_date -= datetime.timedelta(days=1)
        return d == last_date

    def _get_option_rows(self, symbol: str, expiry: datetime.date, instrument: str):
        exchange = 'MCX' if instrument == 'OPTCOM' else 'NFO'
        if not self.master.DERIVATIVE_LOADED: self.master.download_scrip_master(exchange)
        expiry_str = expiry.isoformat()
        return [row for row in self.master.DERIVATIVE_OPTIONS if row.get('symbol') == symbol and row.get('instrument') == instrument and row.get('expiry') == expiry_str and row.get('exchange') == exchange]

    def _select_expiry(self, symbol: str, expiry_type: str, instrument: str) -> Optional[datetime.date]:
        if not self.master.DERIVATIVE_LOADED: self.master.download_scrip_master("NFO"); self.master.download_scrip_master("MCX")
        
        def find_exp():
            exps = set()
            exchange = 'MCX' if instrument == 'OPTCOM' else 'NFO'
            for row in self.master.DERIVATIVE_OPTIONS:
                if row.get('symbol') == symbol and row.get('instrument') == instrument and row.get('exchange') == exchange:
                    exp = self.master._parse_expiry_date(row.get('expiry'))
                    if exp: exps.add(exp)
            return exps

        expiries = find_exp()
        
        # 🔄 EMERGENCY: If still no expiries, force one more download and retry
        # Limit refresh to once per 5 minutes to avoid blocking
        last_refresh = getattr(self.master, '_last_refresh_time', 0)
        now = _time.time()
        
        if not expiries and (now - last_refresh > 300):
            target_exch = 'MCX' if instrument == 'OPTCOM' else 'NFO'
            print(f"🔄 No expiries for {symbol}. Forcing {target_exch} master refresh...")
            self.master.download_scrip_master(target_exch)
            self.master._last_refresh_time = now
            expiries = find_exp()

        if not expiries: return None
        today = datetime.date.today()
        valid = sorted(d for d in expiries if d >= today)
        if not valid: return None
        if expiry_type == "monthly":
            monthly = [d for d in valid if self._is_last_thursday(d)]
            return monthly[0] if monthly else valid[0]
        return valid[0]

    def get_near_future(self, symbol: str, exchange: str, api) -> Optional[Dict[str, str]]:
        try:
            ret = api.searchscrip(exchange=exchange, searchtext=symbol)
            if ret and ret.get('stat') == 'Ok' and 'values' in ret:
                candidates, today = [], datetime.date.today()
                for scrip in ret['values']:
                    if scrip.get('instname') in ('FUTSTK', 'FUTIDX', 'FUTCOM') and scrip.get('symname') == symbol:
                        exp = self.master._parse_expiry_date(scrip.get('exp') or scrip.get('exd'))
                        if exp and exp >= today: candidates.append((exp, scrip['token'], scrip.get('tsym')))
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    return {'token': f"{exchange}|{candidates[0][1]}", 'tsym': candidates[0][2]}
        except Exception: pass
        if exchange == 'NFO':
            futures = [row for row in self.master.DERIVATIVE_OPTIONS if row.get('symbol') == symbol and row.get('instrument') in ('FUTSTK', 'FUTIDX')]
            valid = []
            for f in futures:
                exp = self.master._parse_expiry_date(f.get('expiry'))
                if exp and exp >= datetime.date.today(): valid.append((exp, f))
            if valid:
                valid.sort(key=lambda x: x[0])
                return {'token': f"NFO|{valid[0][1]['token']}", 'tsym': valid[0][1]['tradingsymbol']}
        return None

    def get_credit_spread_contracts(self, symbol: str, ltp: float, side: str, hedge_steps: int, expiry_type: str, instrument: str) -> Dict[str, Any]:
        expiry = self._select_expiry(symbol, expiry_type, instrument)
        if not expiry: return {'ok': False, 'reason': 'no_expiry'}
        rows = self._get_option_rows(symbol, expiry, instrument)
        strikes = sorted({row.get('strike') for row in rows if row.get('strike')})
        if not strikes: return {'ok': False, 'reason': 'no_strikes'}
        atm_strike = min(strikes, key=lambda s: abs(s - ltp))
        diffs = sorted({round(strikes[i+1]-strikes[i], 2) for i in range(len(strikes)-1) if strikes[i+1]>strikes[i]})
        step = diffs[0] if diffs else None
        if atm_strike is None or not step: return {'ok': False, 'reason': 'no_atm_or_step'}
        
        opt_type = 'PE' if side.upper() == 'PUT' else 'CE'
        h_strike = round(atm_strike - hedge_steps * step, 2) if opt_type == 'PE' else round(atm_strike + hedge_steps * step, 2)
        
        def find_best(s, t):
            matches = [r for r in rows if r.get('option_type') == t]
            if not matches: return None
            # Exact or closest
            best = min(matches, key=lambda r: abs(float(r.get('strike', 0)) - s))
            return best if abs(float(best.get('strike', 0)) - s) / (s or 1) <= 0.05 else None

        h_row, a_row = find_best(h_strike, opt_type), find_best(atm_strike, opt_type)
        if not h_row or not a_row: return {'ok': False, 'reason': 'option_symbol_not_found'}
        
        return {
            'ok': True, 'expiry': expiry.isoformat(), 'atm_strike': a_row['strike'], 'hedge_strike': h_row['strike'],
            'lot_size': int(a_row.get('lot_size') or 0), 'atm_symbol': a_row['tradingsymbol'], 'hedge_symbol': h_row['tradingsymbol'],
            'side': side.upper(), 'exchange': h_row.get('exchange', 'NFO')
        }
