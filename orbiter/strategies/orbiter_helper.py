# orbiter/strategies/orbiter_helper.py
"""
🚀 ORBITER Helper - Complete Trading Logic
"""
from utils.utils import safe_ltp, get_today_orb_times
from datetime import datetime
import time
import pytz
import filters
from config.config import VERBOSE_LOGS

# Add to TOP:
import importlib.util
import os

# Load sheets.py dynamically from bot/ folder
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("sheets", base_dir+"/bot/sheets.py")
sheets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sheets)
log_buy_signals = sheets.log_buy_signals  # ✅ WORKS EVERYWHERE
log_square_off = getattr(sheets, 'log_square_off', None)
log_scan_metrics = getattr(sheets, 'log_scan_metrics', None)

# SL filters - generic registry from filters package
SL_FILTERS = getattr(filters, 'get_filters', lambda _: [])('sl')

class OrbiterHelper:
    def __init__(self, client, symbols, filters, config):
        self.client = client
        self.symbols = symbols
        self.filters = filters
        self.config = config
        # ⭐ NEW: Track active buy positions: token -> info
        # info = {'entry_price': float, 'entry_time': datetime, 'symbol': str, 'company_name': str}
        self.active_positions = {}  # {'NSE|3045': {...}}
        self.last_scan_metrics = []
        self.last_scan_log_ts = 0
        self.client.set_span_cache_path(os.path.join(base_dir, 'data', 'span', 'cache.json'))
        self.client.load_span_cache()
        self.verbose_logs = self.config.get('VERBOSE_LOGS', VERBOSE_LOGS)
        
    def evaluate_filters(self, token):
        """Evaluate entry filters - Store returnvalues + return numeric total"""
        data = self.client.SYMBOLDICT.get(token)
        has_live_data = bool(data)
        token_id = token.split("|")[-1]
        if not data:
            data = {'lp': 0, 'token': token_id}
            if self.verbose_logs:
                print(f"❌ NO LIVE DATA for token {token} (using TPSeries only)")

        if self.verbose_logs:
            print(f"🔍 RAW DATA KEYS: {list(data.keys())}")
        websocket_token = data.get('tk') or data.get('token') or token_id
        if self.verbose_logs:
            print(f"🔍 websocket='{websocket_token}' ltp={data.get('lp', 'MISSING')}")
        
        #ltp, ltp_display, symbol  = safe_ltp(data)
        start_time, end_time = get_today_orb_times(simulation=self.config.get('SIMULATION', False))
        start_ts = int(start_time.timestamp())
        end_ts = int(end_time.timestamp())
        
        try:
            candle_data = self.client.api.get_time_price_series(
                exchange='NSE', 
                token=websocket_token,
                starttime=start_ts, 
                endtime=end_ts, 
                interval=1
            )

            def _time_key(raw):
                if raw is None:
                    return None
                text = str(raw).strip()
                if " " in text:
                    text = text.split(" ")[-1]
                parts = text.split(":")
                if len(parts) >= 2:
                    try:
                        return int(parts[0]) * 60 + int(parts[1])
                    except ValueError:
                        return None
                return None

            def _candle_stats(candles):
                ok = [c for c in candles or [] if c.get('stat') == 'Ok']
                if not ok:
                    return None, None, None, None
                keyed = [(c, _time_key(c.get('time') or c.get('tm') or c.get('intt') or c.get('t'))) for c in ok]
                with_time = [pair for pair in keyed if pair[1] is not None]
                ordered = [pair[0] for pair in sorted(with_time, key=lambda x: x[1])] if with_time else list(reversed(ok))
                first = ordered[0]
                last = ordered[-1]
                opens = [float(c.get('into')) for c in ok if c.get('into') is not None]
                highs = [float(c.get('inth')) for c in ok if c.get('inth') is not None]
                lows = [float(c.get('intl')) for c in ok if c.get('intl') is not None]
                closes = [float(c.get('intc')) for c in ok if c.get('intc') is not None]
                open_val = float(first.get('into') or first.get('intc') or 0) if first else None
                close_val = float(last.get('intc') or last.get('into') or 0) if last else None
                high_val = max(highs) if highs else None
                low_val = min(lows) if lows else None
                if open_val is None and opens:
                    open_val = opens[0]
                if close_val is None and closes:
                    close_val = closes[-1]
                return open_val, high_val, low_val, close_val

            entry_filters = getattr(self.filters, 'get_filters', lambda _: [])('entry')
            filter_results = {}
            scores = []

            if not candle_data or len(candle_data) < 5:
                if self.verbose_logs:
                    print(f"🔴 FILTERS {token}: Insufficient candle data ({len(candle_data)})")
                for entry_filter in entry_filters:
                    filter_results[entry_filter.key] = {'score': 0}
                    scores.append(0)
            else:
                # ⭐ Get FULL returnvalues from filters via common evaluate interface
                for entry_filter in entry_filters:
                    result = entry_filter.evaluate(data, candle_data, token=websocket_token)
                    if not isinstance(result, dict):
                        result = {'score': result}
                    filter_results[entry_filter.key] = result
                    scores.append(result.get('score', 0))

            if not scores:
                total = 0
            else:
                total = sum(w * s for w, s in zip(self.config['ENTRY_WEIGHTS'], scores))
            if not has_live_data:
                total = 0

            # ⭐ STORE returnvalues for rank_signals() to use later
            data['_filter_results'] = {
                **filter_results,
                'total': total
            }

            # Collect scan metrics for Sheets
            day_open = data.get('o') or data.get('open')
            day_high = data.get('h') or data.get('high')
            day_low = data.get('l') or data.get('low')
            day_close = data.get('c') or data.get('close')

            ltp = float(data.get('ltp', data.get('lp', 0)) or 0)
            candle_open, candle_high, candle_low, candle_close = _candle_stats(candle_data)
            if ltp == 0 and candle_close is not None:
                ltp = float(candle_close)
                data['lp'] = ltp
                data['ltp'] = ltp
            if day_open is None:
                day_open = candle_open
            if day_high is None:
                day_high = candle_high
            if day_low is None:
                day_low = candle_low
            if day_close is None:
                day_close = candle_close

            token_id = token.split("|")[-1]
            mapped_symbol = self.client.get_symbol(token_id)
            mapped_company = self.client.get_company_name(token_id)
            live_symbol = data.get('t') or data.get('symbol')
            live_company = data.get('company_name')
            symbol_out = live_symbol or mapped_symbol or token
            company_out = live_company or mapped_company or symbol_out

            filters_payload = filter_results

            span_pe = {'ok': False}
            span_ce = {'ok': False}
            span_key_symbol = symbol_out or token
            span_cache_key = f"{span_key_symbol}|{self.config.get('OPTION_EXPIRY', 'monthly')}|{self.config.get('OPTION_INSTRUMENT', 'OPTSTK')}|{self.config.get('HEDGE_STEPS', 4)}"
            cached = None
            cached_pe_valid = False
            cached_ce_valid = False
            if self.client.span_cache is not None:
                cached = self.client.span_cache.get(span_cache_key)
            if cached:
                cached_pe = cached.get('pe', {'ok': False})
                cached_ce = cached.get('ce', {'ok': False})
                if cached_pe.get('ok') and (cached_pe.get('total_margin') or 0) > 0:
                    span_pe = cached_pe
                    cached_pe_valid = True
                if cached_ce.get('ok') and (cached_ce.get('total_margin') or 0) > 0:
                    span_ce = cached_ce
                    cached_ce_valid = True
            if ltp > 0 and (not cached_pe_valid or not cached_ce_valid):
                if not cached_pe_valid:
                    spread_pe = self.client.get_credit_spread_contracts(
                        symbol_out,
                        ltp,
                        side='PUT',
                        hedge_steps=self.config.get('HEDGE_STEPS', 4),
                        expiry_type=self.config.get('OPTION_EXPIRY', 'monthly'),
                        instrument=self.config.get('OPTION_INSTRUMENT', 'OPTSTK')
                    )
                    if spread_pe.get('ok'):
                        span_pe = self.client.calculate_span_for_spread(
                            spread_pe,
                            product_type=self.config.get('OPTION_PRODUCT_TYPE', 'I')
                        )

                if not cached_ce_valid:
                    spread_ce = self.client.get_credit_spread_contracts(
                        symbol_out,
                        ltp,
                        side='CALL',
                        hedge_steps=self.config.get('HEDGE_STEPS', 4),
                        expiry_type=self.config.get('OPTION_EXPIRY', 'monthly'),
                        instrument=self.config.get('OPTION_INSTRUMENT', 'OPTSTK')
                    )
                    if spread_ce.get('ok'):
                        span_ce = self.client.calculate_span_for_spread(
                            spread_ce,
                            product_type=self.config.get('OPTION_PRODUCT_TYPE', 'I')
                        )

                if self.client.span_cache is not None:
                    cache_entry = cached or {}
                    if span_pe.get('ok'):
                        cache_entry['pe'] = span_pe
                    if span_ce.get('ok'):
                        cache_entry['ce'] = span_ce
                    if cache_entry:
                        self.client.span_cache[span_cache_key] = cache_entry
                        self.client.save_span_cache()

            self.last_scan_metrics.append({
                'token': token,
                'symbol': symbol_out,
                'company_name': company_out,
                'day_open': float(day_open) if day_open is not None else None,
                'day_high': float(day_high) if day_high is not None else None,
                'day_low': float(day_low) if day_low is not None else None,
                'day_close': float(day_close) if day_close is not None else None,
                'span_pe': span_pe.get('span') if span_pe.get('ok') else None,
                'expo_pe': span_pe.get('expo') if span_pe.get('ok') else None,
                'total_margin_pe': span_pe.get('total_margin') if span_pe.get('ok') else None,
                'pledged_required_pe': span_pe.get('pledged_required') if span_pe.get('ok') else None,
                'span_ce': span_ce.get('span') if span_ce.get('ok') else None,
                'expo_ce': span_ce.get('expo') if span_ce.get('ok') else None,
                'total_margin_ce': span_ce.get('total_margin') if span_ce.get('ok') else None,
                'pledged_required_ce': span_ce.get('pledged_required') if span_ce.get('ok') else None,
                'ltp': ltp,
                'filters': filters_payload
            })

            if filter_results:
                parts = [
                    f"{key.upper()}={value.get('score', 0)}"
                    for key, value in filter_results.items()
                    if isinstance(value, dict)
                ]
                details = " ".join(parts)
                if self.verbose_logs:
                    print(f"📊 {token}: {details} TOTAL={total}")
            else:
                if self.verbose_logs:
                    print(f"📊 {token}: TOTAL={total}")
            return total  # ⭐ ONLY numeric total for ranking

        except Exception as e:
            print(f"❌ FILTER EVAL ERROR {token}: {e}")
            return 0

    def evaluate_all(self):
        """Scan all symbols"""
        scores = {}
        self.last_scan_metrics = []
        for token in self.symbols:
            # Use FULL token key - NO stripping needed!
            score = self.evaluate_filters(token)
            if score != 0:
                scores[token] = score
                
        if self.verbose_logs:
            print(f"📊 Scanned {len(self.symbols)} → {len(scores)} signals")
        if not scores:
            if self.verbose_logs:
                print("🔧 Filters: ['F1:25', 'F2:OFF', 'F3:OFF']")
                print("⏳ Waiting for WebSocket data...")
            
        return scores

    # In your rank_signals() method:
    def rank_signals(self, scores):
        buy_signals = []
        ranked = sorted(scores.items(), key=lambda x: abs(x[1]), reverse=True)[:self.config['TOP_N']]
        
        if self.verbose_logs:
            print(f"🔍 DEBUG: active_positions={self.active_positions}")  # ⭐ SEE STATE
        
        for token, score in ranked:
            if self.verbose_logs:
                print(f"🔍 CHECKING {token}: {score}pts")  # ⭐ DEBUG
            
            # ⭐ SKIP if already in position (BEFORE 45pt check)
            if token in self.active_positions:
                if self.verbose_logs:
                    print(f"⏭️ SKIP {token} - Position active")
                continue

            # ⭐ CONFIRMED → NEW POSITION (bull or bear)
            if score >= self.config['TRADE_SCORE'] or score <= -self.config['TRADE_SCORE']:
                print(f"🟢 NEW SIGNAL: {token} {score}pts")
                
                data = self.client.SYMBOLDICT.get(token)
                filter_results = data.get('_filter_results') or {}
                orb_result = filter_results.get('ef1_orb', {}) if isinstance(filter_results.get('ef1_orb', {}), dict) else {}
                ema5_result = filter_results.get('ef2_price_above_5ema', {}) if isinstance(filter_results.get('ef2_price_above_5ema', {}), dict) else {}
                ltp, ltp_display, symbol = safe_ltp(data)  # ✅ 3 values

                if score >= self.config['TRADE_SCORE']:
                    spread = self.client.place_put_credit_spread(
                        symbol=symbol,
                        ltp=ltp,
                        hedge_steps=self.config.get('HEDGE_STEPS', 4),
                        expiry_type=self.config.get('OPTION_EXPIRY', 'monthly'),
                        execute=self.config.get('OPTION_EXECUTE', False),
                        product_type=self.config.get('OPTION_PRODUCT_TYPE', 'I'),
                        price_type=self.config.get('OPTION_PRICE_TYPE', 'MKT'),
                        instrument=self.config.get('OPTION_INSTRUMENT', 'OPTSTK')
                    )
                    strategy = 'PUT_CREDIT_SPREAD'
                else:
                    spread = self.client.place_call_credit_spread(
                        symbol=symbol,
                        ltp=ltp,
                        hedge_steps=self.config.get('HEDGE_STEPS', 4),
                        expiry_type=self.config.get('OPTION_EXPIRY', 'monthly'),
                        execute=self.config.get('OPTION_EXECUTE', False),
                        product_type=self.config.get('OPTION_PRODUCT_TYPE', 'I'),
                        price_type=self.config.get('OPTION_PRICE_TYPE', 'MKT'),
                        instrument=self.config.get('OPTION_INSTRUMENT', 'OPTSTK')
                    )
                    strategy = 'CALL_CREDIT_SPREAD'

                if not spread.get('ok'):
                    print(f"⚠️ Spread order failed for {symbol}: {spread.get('reason')}")
                    continue

                span_metrics = self.client.calculate_span_for_spread(
                    spread,
                    product_type=self.config.get('OPTION_PRODUCT_TYPE', 'I')
                )

                atm_premium_entry = self.client.get_option_ltp_by_symbol(spread.get('atm_symbol'))
                hedge_premium_entry = self.client.get_option_ltp_by_symbol(spread.get('hedge_symbol'))

                buy_signals.append({
                    'token': token,
                    'symbol': symbol,           # RELIANCE
                    'company_name': data.get('company_name', symbol),  # ✅ Use company name from websocket data
                    'ltp': ltp,
                    'ltp_display': ltp_display, # ₹1446.40 (bonus)
                    'score': score,
                    'orb_high': orb_result.get('orb_high', 0),
                    'orb_low': orb_result.get('orb_low', 0),
                    'ema5': ema5_result.get('ema5', 0),
                    'span_pe': span_metrics.get('span', 0) if span_metrics.get('ok') and strategy == 'PUT_CREDIT_SPREAD' else 0,
                    'expo_pe': span_metrics.get('expo', 0) if span_metrics.get('ok') and strategy == 'PUT_CREDIT_SPREAD' else 0,
                    'total_margin_pe': span_metrics.get('total_margin', 0) if span_metrics.get('ok') and strategy == 'PUT_CREDIT_SPREAD' else 0,
                    'pledged_required_pe': span_metrics.get('pledged_required', 0) if span_metrics.get('ok') and strategy == 'PUT_CREDIT_SPREAD' else 0,
                    'span_ce': span_metrics.get('span', 0) if span_metrics.get('ok') and strategy == 'CALL_CREDIT_SPREAD' else 0,
                    'expo_ce': span_metrics.get('expo', 0) if span_metrics.get('ok') and strategy == 'CALL_CREDIT_SPREAD' else 0,
                    'total_margin_ce': span_metrics.get('total_margin', 0) if span_metrics.get('ok') and strategy == 'CALL_CREDIT_SPREAD' else 0,
                    'pledged_required_ce': span_metrics.get('pledged_required', 0) if span_metrics.get('ok') and strategy == 'CALL_CREDIT_SPREAD' else 0,
                    'strategy': strategy,
                    'expiry': spread.get('expiry'),
                    'atm_strike': spread.get('atm_strike'),
                    'hedge_strike': spread.get('hedge_strike'),
                    'atm_symbol': spread.get('atm_symbol'),
                    'hedge_symbol': spread.get('hedge_symbol'),
                    'atm_premium_entry': atm_premium_entry,
                    'hedge_premium_entry': hedge_premium_entry,
                    'dry_run': spread.get('dry_run', False)
                })

                for item in self.last_scan_metrics:
                    if item.get('token') == token:
                        if span_metrics.get('ok'):
                            if strategy == 'PUT_CREDIT_SPREAD':
                                item['span_pe'] = span_metrics.get('span')
                                item['expo_pe'] = span_metrics.get('expo')
                                item['total_margin_pe'] = span_metrics.get('total_margin')
                                item['pledged_required_pe'] = span_metrics.get('pledged_required')
                            else:
                                item['span_ce'] = span_metrics.get('span')
                                item['expo_ce'] = span_metrics.get('expo')
                                item['total_margin_ce'] = span_metrics.get('total_margin')
                                item['pledged_required_ce'] = span_metrics.get('pledged_required')
                        break
                
                # ⭐ ADD TO POSITIONS IMMEDIATELY (inside 45pt block)
                self.active_positions[token] = {
                    'entry_price': ltp,
                    'entry_time': datetime.now(pytz.timezone('Asia/Kolkata')),
                    'symbol': symbol,
                    'company_name': data.get('company_name', symbol),
                    'strategy': strategy,
                    'atm_symbol': spread.get('atm_symbol'),
                    'hedge_symbol': spread.get('hedge_symbol'),
                    'expiry': spread.get('expiry'),
                    'atm_strike': spread.get('atm_strike'),
                    'hedge_strike': spread.get('hedge_strike'),
                    'atm_premium_entry': atm_premium_entry,
                    'hedge_premium_entry': hedge_premium_entry
                }
                print(f"✅ POSITION ADDED: {token} @ {ltp}")
        
        # ⭐ LOG ONLY NEW 45pt SIGNALS
        if buy_signals:
            log_buy_signals(buy_signals)
            print(f"✅ {len(buy_signals)} NEW buys → Google Sheets")

        if log_scan_metrics and self.last_scan_metrics:
            now_ts = time.time()
            if now_ts - self.last_scan_log_ts >= 60:
                trade_tokens = {item.get('token') for item in buy_signals}
                for item in self.last_scan_metrics:
                    item['trade_taken'] = item.get('token') in trade_tokens
                log_scan_metrics(self.last_scan_metrics)
                self.last_scan_log_ts = now_ts
        
        return buy_signals

    def check_sl(self):
        """Periodically called to evaluate SL filters for active positions."""
        if not self.active_positions:
            return []

        to_square = []
        for token, info in list(self.active_positions.items()):
            # get latest LTP
            data = self.client.SYMBOLDICT.get(token) or {}
            ltp = None
            try:
                ltp = float(data.get('ltp')) if data.get('ltp') is not None else self.client.get_ltp(token)
            except Exception:
                ltp = self.client.get_ltp(token)

            if ltp is None:
                continue

            # run SL filters (any match triggers square-off)
            res = None
            for sl_filter in SL_FILTERS:
                try:
                    candidate = sl_filter.evaluate(info, float(ltp), data)
                except Exception as exc:
                    candidate = {'hit': False, 'reason': f"error:{exc}"}
                if candidate and candidate.get('hit'):
                    res = candidate
                    if 'reason' not in res:
                        res['reason'] = sl_filter.key
                    break

            if res and res.get('hit'):
                pct = res.get('pct', 0.0)
                reason = res.get('reason', 'SL HIT')
                atm_premium_exit = self.client.get_option_ltp_by_symbol(info.get('atm_symbol'))
                hedge_premium_exit = self.client.get_option_ltp_by_symbol(info.get('hedge_symbol'))
                so = {
                    'token': token,
                    'symbol': info.get('symbol'),
                    'company_name': info.get('company_name'),
                    'entry_price': info.get('entry_price'),
                    'exit_price': float(ltp),
                    'pct_change': pct,
                    'reason': reason,
                    'strategy': info.get('strategy'),
                    'expiry': info.get('expiry'),
                    'atm_strike': info.get('atm_strike'),
                    'hedge_strike': info.get('hedge_strike'),
                    'atm_symbol': info.get('atm_symbol'),
                    'hedge_symbol': info.get('hedge_symbol'),
                    'atm_premium_entry': info.get('atm_premium_entry'),
                    'hedge_premium_entry': info.get('hedge_premium_entry'),
                    'atm_premium_exit': atm_premium_exit,
                    'hedge_premium_exit': hedge_premium_exit
                }
                to_square.append(so)
                # remove position
                try:
                    del self.active_positions[token]
                except KeyError:
                    pass

        # log square offs
        if to_square and log_square_off:
            log_square_off(to_square)
        return to_square

    
    def is_market_hours(self):
        """🔍 MOVED HERE - Check trading hours IST"""
        now = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        return (self.config['MARKET_OPEN'] <= now <= self.config['MARKET_CLOSE'])

# 🔥 ADD THESE 3 LINES AT BOTTOM:
if __name__ == "__main__":
    pass