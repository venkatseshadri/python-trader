import time
from datetime import datetime, time as dt_time
import pytz
import math
import numpy as np
import re
import traceback
from utils.utils import safe_float, get_today_orb_times
from .state import OrbiterState

class Evaluator:
    @staticmethod
    def _time_key(raw):
        if raw is None: return None
        text = str(raw).strip()
        if " " in text: text = text.split(" ")[-1]
        parts = text.split(":")
        if len(parts) >= 2:
            try:
                return int(parts[0]) * 60 + int(parts[1])
            except ValueError:
                return None
        return None

    @staticmethod
    def _candle_stats(candles, time_key_func):
        ok = [c for c in candles or [] if c.get('stat') == 'Ok']
        if not ok: return None, None, None, None
        
        keyed = [(c, time_key_func(c.get('time') or c.get('tm') or c.get('intt') or c.get('t'))) for c in ok]
        with_time = [pair for pair in keyed if pair[1] is not None]
        ordered = [pair[0] for pair in sorted(with_time, key=lambda x: x[1])] if with_time else list(reversed(ok))
        first = ordered[0]
        
        opens = [safe_float(c.get('into')) for c in ok if safe_float(c.get('into')) > 0]
        highs = [safe_float(c.get('inth') or c.get('h')) for c in ok if safe_float(c.get('inth') or c.get('h')) > 0]
        lows = [safe_float(c.get('intl') or c.get('l')) for c in ok if safe_float(c.get('intl') or c.get('l')) > 0]
        closes = [safe_float(c.get('intc') or c.get('c')) for c in ok if safe_float(c.get('intc') or c.get('c')) > 0]
        
        open_val = opens[0] if opens else safe_float(first.get('into') or first.get('o') or first.get('intc'))
        close_val = closes[-1] if closes else safe_float(ordered[-1].get('intc') or ordered[-1].get('c'))
        high_val = max(highs) if highs else None
        low_val = min(lows) if lows else None
        
        return open_val, high_val, low_val, close_val

    def evaluate_filters(self, state: OrbiterState, token):
        """Evaluate entry filters and resolve price data"""
        data = state.client.SYMBOLDICT.get(token)
        has_live_data = bool(data)
        token_id = token.split("|")[-1]
        if not data:
            data = {'lp': 0, 'token': token_id}

        websocket_token = data.get('tk') or data.get('token') or token_id
        
        # ⭐ SIMULATION: Fetch last LTP via REST if missing
        if state.config.get('SIMULATION', False) and safe_float(data.get('lp', 0)) == 0:
            try:
                q_exch = token.split("|")[0] if "|" in token else 'NSE'
                quote = state.client.api.get_quotes(exchange=q_exch, token=token_id)
                if quote and quote.get('lp'):
                    data['lp'] = data['ltp'] = float(quote['lp'])
                    state.client.SYMBOLDICT[token] = data
            except Exception: pass

        start_time, end_time = get_today_orb_times(simulation=state.config.get('SIMULATION', False))
        start_ts, end_ts = int(start_time.timestamp()), int(end_time.timestamp())
        exchange = token.split("|")[0] if "|" in token else 'NSE'
        
        try:
            candle_data = state.client.api.get_time_price_series(
                exchange=exchange, token=websocket_token,
                starttime=start_ts, endtime=end_ts, interval=1
            )
            
            if not candle_data and token == state.symbols[0]:
                time.sleep(0.5)
                candle_data = state.client.api.get_time_price_series(
                    exchange=exchange, token=websocket_token,
                    starttime=start_ts, endtime=end_ts, interval=1
                )

            candle_open, candle_high, candle_low, candle_close = self._candle_stats(candle_data, self._time_key)

            # Resolve Prices & Stats BEFORE filters
            day_open = data.get('o') or data.get('open')
            day_high = data.get('h') or data.get('high')
            day_low = data.get('l') or data.get('low')
            day_close = data.get('c') or data.get('close')

            ltp = safe_float(data.get('ltp', data.get('lp', 0)) or 0)
            if ltp == 0 and candle_close is not None: ltp = safe_float(candle_close)
            
            data['lp'] = data['ltp'] = ltp
            if not safe_float(day_open): day_open = candle_open
            if not safe_float(day_high): day_high = candle_high
            if not safe_float(day_low): day_low = candle_low
            if not safe_float(day_close): day_close = candle_close
            
            data['o'], data['h'], data['l'], data['c'] = day_open, day_high, day_low, day_close
            if token not in state.client.SYMBOLDICT or not state.client.SYMBOLDICT[token].get('lp'):
                state.client.SYMBOLDICT[token] = data

            # Evaluate Filters
            entry_filters = getattr(state.filters, 'get_filters', lambda _: [])('entry')
            filter_results = {}
            scores = []

            if not candle_data or len(candle_data) < 5:
                for f in entry_filters: filter_results[f.key] = {'score': 0}
                total = 0
            else:
                for f in entry_filters:
                    res = f.evaluate(data, candle_data, token=websocket_token)
                    if not isinstance(res, dict): res = {'score': res if isinstance(res, (int, float)) else 0}
                    filter_results[f.key] = res
                    scores.append(res.get('score', 0))
                
                # 🧠 DYNAMIC WEIGHTING LOGIC
                # Weights: [F1_ORB, F2_EMA5, F3_EMA_X, F4_ST, F5_SCOPE, F6_GAP, F7_ATR, F8_SNIPER]
                base_weights = [1.0, 1.2, 1.2, 0.6, 1.2, 1.2, 1.0, 1.0] 
                
                # Time-based decay for ORB (F1)
                now_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
                if now_time < dt_time(11, 0): orb_w = 1.5    # Morning: High importance
                elif now_time < dt_time(13, 0): orb_w = 0.8 # Mid-day: Fading
                else: orb_w = 0.3                           # Afternoon: Noise
                
                base_weights[0] = orb_w
                
                valid_scores = [(w, s) for w, s in zip(base_weights, scores) if not math.isnan(s)]
                total = round(sum(w * s for w, s in valid_scores), 2) if valid_scores else 0

            if not has_live_data and ltp == 0: total = 0
            state.filter_results_cache[token] = {**filter_results, 'total': total}

            # Symbol/Company resolution
            mapped_symbol = state.client.get_symbol(token_id, exchange=exchange)
            mapped_company = state.client.get_company_name(token_id, exchange=exchange)
            symbol_out = data.get('t') or data.get('symbol') or mapped_symbol
            company_out = data.get('company_name') or mapped_company or symbol_out

            # BASE symbol cleanup
            base_symbol_res = company_out if company_out and '|' not in str(company_out) else symbol_out
            if isinstance(base_symbol_res, str):
                base_symbol_res = re.sub(r'\d{2}[A-Z]{3}\d{2}[FC]$', '', base_symbol_res)
                if base_symbol_res.endswith('-EQ'): base_symbol_res = base_symbol_res[:-3]
                base_symbol_res = base_symbol_res.strip()

            # Logging cleanup
            if isinstance(symbol_out, str) and '|' in symbol_out:
                symbol_out = company_out if company_out and '|' not in str(company_out) else token_id
            if isinstance(company_out, str) and '|' in company_out: company_out = symbol_out

            # MARGIN CALCULATION
            span_pe, span_ce = {'ok': False}, {'ok': False}
            span_key = f"{base_symbol_res}|{state.config.get('OPTION_EXPIRY')}|{state.config.get('OPTION_INSTRUMENT')}|{state.config.get('HEDGE_STEPS')}"
            
            cached = state.client.span_cache.get(span_key) if state.client.span_cache else None
            if cached:
                if cached.get('pe', {}).get('ok'): span_pe = cached['pe']
                if cached.get('ce', {}).get('ok'): span_ce = cached['ce']

            if ltp > 0 and (not span_pe.get('ok') or not span_ce.get('ok')):
                for side, store in [('PUT', span_pe), ('CALL', span_ce)]:
                    if store.get('ok'): continue
                    spread = state.client.get_credit_spread_contracts(base_symbol_res, ltp, side=side, 
                                                                    hedge_steps=state.config.get('HEDGE_STEPS', 4),
                                                                    expiry_type=state.config.get('OPTION_EXPIRY'),
                                                                    instrument=state.config.get('OPTION_INSTRUMENT'))
                    if spread.get('ok'):
                        margin = state.client.calculate_span_for_spread(spread, product_type=state.config.get('OPTION_PRODUCT_TYPE'))
                        if side == 'PUT': span_pe = margin
                        else: span_ce = margin

                if state.client.span_cache is not None:
                    state.client.span_cache[span_key] = {'pe': span_pe, 'ce': span_ce}
                    state.client.save_span_cache()

            state.last_scan_metrics.append({
                'token': token, 'symbol': symbol_out, 'company_name': company_out,
                'day_open': day_open, 'day_high': day_high, 'day_low': day_low, 'day_close': day_close,
                'ltp': ltp, 'filters': filter_results,
                'span_pe': span_pe, 'span_ce': span_ce,
                'trade_taken': token in state.active_positions
            })

            if state.verbose_logs:
                details = " ".join([f"{k.upper()}={v.get('score', 0)}" for k, v in filter_results.items()])
                print(f"📊 {symbol_out} ({token}): {details} TOTAL={total}")
            
            return total

        except Exception as e:
            print(f"❌ EVAL ERROR {token}: {e}")
            if state.verbose_logs: traceback.print_exc()
            return 0
