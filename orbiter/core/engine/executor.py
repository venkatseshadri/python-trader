from datetime import datetime
import time
import pytz
import re
from utils.utils import safe_ltp
from utils.telegram_notifier import send_telegram_msg
from .state import OrbiterState

class Executor:
    def __init__(self, log_buy_signals, log_closed_positions, sl_filters, tp_filters, summary_manager=None):
        self.log_buy_signals = log_buy_signals
        self.log_closed_positions = log_closed_positions
        self.sl_filters = sl_filters
        self.tp_filters = tp_filters
        self.summary = summary_manager

    def _send_margin_update(self):
        """Helper to send concise margin status to Telegram"""
        if self.summary:
            try:
                msg = self.summary.generate_margin_status()
                send_telegram_msg(msg)
            except Exception as e:
                print(f"⚠️ Could not send margin update: {e}")

    def rank_signals(self, state: OrbiterState, scores, syncer):
        """Process signals and place orders"""
        buy_signals = []
        ranked = sorted(scores.items(), key=lambda x: abs(x[1]), reverse=True)[:state.config['TOP_N']]
        
        if state.verbose_logs and scores:
            print(f"🔍 Evaluated {len(scores)} symbols. Top Signal: {ranked[0][0] if ranked else 'None'} Score: {ranked[0][1] if ranked else 0}")

        for token, score in ranked:
            if token in state.active_positions: continue

            # 🔥 NEW: Entry Guards (Cooldown & Trend State)
            now_ts = time.time()
            if token in state.exit_history and (now_ts - state.exit_history[token] < 900): # 15 min cooldown
                continue

            if abs(score) >= state.config['TRADE_SCORE']:
                data = state.client.SYMBOLDICT.get(token)
                results = state.filter_results_cache.get(token, {})
                orb_r = results.get('ef1_orb', {})
                ema_r = results.get('ef2_price_above_5ema', {})
                ltp, ltp_display, symbol_full = safe_ltp(data, token)
                
                # 🔥 NEW: Trend-State Guards
                candle_data = data.get('candles', []) if data else []
                if len(candle_data) >= 10:
                    # 1. Slope Guard (EMA5 rising)
                    import talib
                    closes = np.array([safe_float(c.get('intc')) for c in candle_data if c.get('stat')=='Ok'], dtype=float)
                    ema5 = talib.EMA(closes, timeperiod=5)
                    if len(ema5) >= 6 and ema5[-1] <= ema5[-6]: # Negative/flat slope over last 5 mins
                        if state.verbose_logs: print(f"🛡️ Guard: {symbol_full} slope negative. Skipping.")
                        continue
                    
                    # 2. Freshness Guard (Near session high)
                    day_high = max([safe_float(c.get('inth')) for c in candle_data if c.get('stat')=='Ok'])
                    if ltp < day_high * 0.998: # More than 0.2% below high
                        if state.verbose_logs: print(f"🛡️ Guard: {symbol_full} stale (below high). Skipping.")
                        continue

                base_symbol = data.get('company_name') or symbol_full
                if isinstance(base_symbol, str):
                    base_symbol = re.sub(r'\d{2}[A-Z]{3}\d{2}[FC]$', '', base_symbol)
                    if base_symbol.endswith('-EQ'): base_symbol = base_symbol[:-3]
                    base_symbol = base_symbol.strip()

                is_bull = score >= state.config['TRADE_SCORE']
                sig = None
                
                # ✅ MCX: Trade Futures Directly
                if token.startswith('MCX|'):
                    # Check SYMBOLDICT with both full key and raw ID
                    t_id_raw = token.split('|')[-1]
                    if token not in state.client.SYMBOLDICT and f"MCX|{t_id_raw}" not in state.client.SYMBOLDICT:
                        print(f"⏳ Waiting for WS resolution for {token}...")
                        continue

                    order_res = state.client.place_future_order(
                        symbol=base_symbol, token=token, side='B' if is_bull else 'S',
                        execute=state.config.get('OPTION_EXECUTE'),
                        product_type=state.config.get('OPTION_PRODUCT_TYPE'),
                        price_type=state.config.get('OPTION_PRICE_TYPE')
                    )
                    
                    if not order_res.get('ok'):
                        print(f"⚠️ Future order failed for {base_symbol}: {order_res.get('reason')}")
                        continue

                    sig = {
                        'token': token, 'symbol': symbol_full, 'company_name': base_symbol,
                        'ltp': ltp, 'ltp_display': ltp_display, 'score': score,
                        'orb_high': orb_r.get('orb_high', 0), 'orb_low': orb_r.get('orb_low', 0),
                        'strategy': 'FUTURE_LONG' if is_bull else 'FUTURE_SHORT',
                        'dry_run': order_res.get('dry_run', False),
                        'lot_size': order_res.get('lot_size', 0),
                        'total_margin': order_res.get('total_margin', 0)
                    }
                    
                    state.active_positions[token] = {
                        'entry_price': ltp, 'entry_time': datetime.now(pytz.timezone('Asia/Kolkata')),
                        'symbol': symbol_full, 'company_name': base_symbol, 'strategy': sig['strategy'],
                        'orb_high': sig['orb_high'], 'orb_low': sig['orb_low'],
                        'lot_size': sig['lot_size'], 'config': state.config
                    }

                # ✅ NFO (or others): Use Credit Spreads
                else:
                    spread = (state.client.place_put_credit_spread if is_bull else state.client.place_call_credit_spread)(
                        symbol=base_symbol, ltp=ltp, hedge_steps=state.config.get('HEDGE_STEPS'),
                        expiry_type=state.config.get('OPTION_EXPIRY'), execute=state.config.get('OPTION_EXECUTE'),
                        product_type=state.config.get('OPTION_PRODUCT_TYPE'), price_type=state.config.get('OPTION_PRICE_TYPE'),
                        instrument=state.config.get('OPTION_INSTRUMENT')
                    )

                    if not spread.get('ok'):
                        print(f"⚠️ Spread failed for {base_symbol}: {spread.get('reason')}")
                        continue

                    span_m = state.client.calculate_span_for_spread(spread, product_type=state.config.get('OPTION_PRODUCT_TYPE'))
                    atm_p = state.client.get_option_ltp_by_symbol(spread.get('atm_symbol'))
                    hdg_p = state.client.get_option_ltp_by_symbol(spread.get('hedge_symbol'))

                    sig = {
                        'token': token, 'symbol': symbol_full, 'company_name': base_symbol,
                        'ltp': ltp, 'ltp_display': ltp_display, 'score': score,
                        'orb_high': orb_r.get('orb_high', 0), 'orb_low': orb_r.get('orb_low', 0),
                        'ema5': ema_r.get('ema5', 0), 'strategy': 'PUT_CREDIT_SPREAD' if is_bull else 'CALL_CREDIT_SPREAD',
                        'expiry': spread.get('expiry'), 'atm_strike': spread.get('atm_strike'),
                        'hedge_strike': spread.get('hedge_strike'), 'atm_symbol': spread.get('atm_symbol'),
                        'hedge_symbol': spread.get('hedge_symbol'), 'atm_premium_entry': atm_p,
                        'hedge_premium_entry': hdg_p, 'dry_run': spread.get('dry_run', False),
                        **{k: span_m.get(k, 0) for k in ['span', 'expo', 'total_margin', 'pledged_required', 'span_trade', 'expo_trade', 'pre_trade', 'add', 'add_trade', 'ten', 'ten_trade', 'del', 'del_trade', 'spl', 'spl_trade']}
                    }

                    state.active_positions[token] = {
                        'entry_price': ltp, 'entry_time': datetime.now(pytz.timezone('Asia/Kolkata')),
                        'symbol': symbol_full, 'company_name': base_symbol, 'strategy': sig['strategy'],
                        'atm_symbol': sig['atm_symbol'], 'hedge_symbol': sig['hedge_symbol'],
                        'expiry': sig['expiry'], 'atm_strike': sig['atm_strike'], 'hedge_strike': sig['hedge_strike'],
                        'atm_premium_entry': atm_p, 'hedge_premium_entry': hdg_p,
                        'orb_high': sig['orb_high'], 'orb_low': sig['orb_low'],
                        'entry_net_premium': (atm_p - hdg_p) if (atm_p and hdg_p) else 0,
                        'lot_size': spread.get('lot_size', 0), 'config': state.config
                    }

                if sig:
                    buy_signals.append(sig)
                    print(f"✅ POSITION ADDED: {token} @ {ltp}")
                    send_telegram_msg(f"✅ *Position Opened*\nSymbol: `{symbol_full}`\nStrategy: `{sig['strategy']}`\nLTP: `{ltp}`\nScore: `{score}`")
                    self._send_margin_update()
        
        if buy_signals:
            self.log_buy_signals(buy_signals)
            syncer.sync_active_positions_to_sheets(state)
        return buy_signals

    def square_off_all(self, state: OrbiterState, reason="EOD EXIT"):
        if not state.active_positions: return []
        to_square = []
        exec_orders = state.config.get('OPTION_EXECUTE', False)
        
        for token, info in list(state.active_positions.items()):
            ltp = state.client.get_ltp(token) or info.get('entry_price', 0)
            strategy = info.get('strategy', '')
            
            # ✅ Handle Future Square-Off
            if 'FUTURE' in strategy:
                if exec_orders:
                    side = 'S' if 'LONG' in strategy else 'B'
                    qty = info.get('lot_size', 0)
                    exch = token.split('|')[0] if '|' in token else 'NFO'
                    tsym = state.client.TOKEN_TO_SYMBOL.get(token.split('|')[-1])
                    if qty > 0 and tsym:
                        state.client.api.place_order(buy_or_sell=side, product_type=state.config.get('OPTION_PRODUCT_TYPE'),
                                                   exchange=exch, tradingsymbol=tsym, quantity=qty, discloseqty=0,
                                                   price_type='MKT', price=0, retention='DAY', remarks=f'{reason}_sq_fut')
                
                pct = ((float(ltp) - info['entry_price']) / info['entry_price'] * 100.0)
                if 'SHORT' in strategy: pct = -pct
                
                to_square.append({
                    'token': token, 'symbol': info.get('symbol'), 'company_name': info.get('company_name'),
                    'entry_price': info.get('entry_price'), 'exit_price': float(ltp), 'pct_change': pct, 'reason': reason,
                    'strategy': strategy, 'lot_size': info.get('lot_size', 0),
                    'entry_time': info.get('entry_time').strftime("%Y-%m-%d %H:%M:%S IST") if info.get('entry_time') else "N/A"
                })

            # ✅ Handle Spread Square-Off
            else:
                atm_p_exit = state.client.get_option_ltp_by_symbol(info.get('atm_symbol'))
                hdg_p_exit = state.client.get_option_ltp_by_symbol(info.get('hedge_symbol'))

                entry_net = info.get('entry_net_premium', 0)
                basis = info.get('atm_premium_entry', 0)
                pct = 0.0
                if entry_net != 0 and basis != 0 and atm_p_exit and hdg_p_exit:
                    pct = (entry_net - (atm_p_exit - hdg_p_exit)) / abs(basis) * 100.0

                if exec_orders:
                    qty, atm_s, hdg_s = info.get('lot_size', 0), info.get('atm_symbol'), info.get('hedge_symbol')
                    if qty > 0 and atm_s and hdg_s:
                        for side, sym, rem in [('B', atm_s, 'sq_atm'), ('S', hdg_s, 'sq_hdg')]:
                            state.client.api.place_order(buy_or_sell=side, product_type=state.config.get('OPTION_PRODUCT_TYPE'),
                                                       exchange='NFO', tradingsymbol=sym, quantity=qty, discloseqty=0,
                                                       price_type='MKT', price=0, retention='DAY', remarks=f'{reason}_{rem}')

                # Calculate final spread for logging/alerts
                exit_net = (atm_p_exit - hdg_p_exit) if (atm_p_exit and hdg_p_exit) else 0
                
                to_square.append({
                    'token': token, 'symbol': info.get('symbol'), 'company_name': info.get('company_name'),
                    'entry_price': info.get('entry_price'), 'exit_price': float(ltp), 'pct_change': pct, 'reason': reason,
                    'strategy': info.get('strategy'), 'expiry': info.get('expiry'), 'atm_strike': info.get('atm_strike'),
                    'hedge_strike': info.get('hedge_strike'), 'atm_symbol': info.get('atm_symbol'), 'hedge_symbol': info.get('hedge_symbol'),
                    'atm_premium_entry': info.get('atm_premium_entry'), 'hedge_premium_entry': info.get('hedge_premium_entry'),
                    'atm_premium_exit': atm_p_exit, 'hedge_premium_exit': hdg_p_exit, 
                    'exit_net_premium': exit_net, 'lot_size': info.get('lot_size', 0),
                    'entry_time': info.get('entry_time').strftime("%Y-%m-%d %H:%M:%S IST") if info.get('entry_time') else "N/A"
                })

        state.active_positions.clear()
        now_ts = time.time()
        if to_square:
            for pos in to_square:
                state.exit_history[pos['token']] = now_ts # Record exit time
            
            if self.log_closed_positions:
                self.log_closed_positions(to_square)
            
            # Send summary to Telegram
            lines = []
            total_pnl = 0.0
            for pos in to_square:
                strategy = pos.get('strategy', '')
                lot_size = int(pos.get('lot_size', 0))
                pnl_val = 0.0
                
                if 'FUTURE' in strategy:
                    entry = float(pos.get('entry_price', 0))
                    exit_p = float(pos.get('exit_price', 0))
                    if 'SHORT' in strategy: pnl_val = (entry - exit_p) * lot_size
                    else: pnl_val = (exit_p - entry) * lot_size
                    price_details = f"[LTP: {exit_p}]"
                else:
                    # Spread
                    atm_e = float(pos.get('atm_premium_entry', 0) or 0)
                    hdg_e = float(pos.get('hedge_premium_entry', 0) or 0)
                    atm_x = float(pos.get('atm_premium_exit', 0) or 0)
                    hdg_x = float(pos.get('hedge_premium_exit', 0) or 0)
                    if atm_x and hdg_x:
                        pnl_val = ((atm_e - hdg_e) - (atm_x - hdg_x)) * lot_size
                    
                    exit_net = pos.get('exit_net_premium', 0)
                    price_details = f"[LTP: {pos.get('exit_price')}] [Spread: {exit_net:.2f}]"
                
                total_pnl += pnl_val
                lines.append(f"• `{pos['symbol']}`: {pos['pct_change']:.2f}% (₹{pnl_val:.2f}) {price_details}")

            summary = "\n".join(lines)
            send_telegram_msg(f"⏹️ *Mass Square Off Complete*\nReason: `{reason}`\nTotal PnL: ₹{total_pnl:.2f}\n\n*Positions:*\n{summary}")
        return to_square

    def check_sl(self, state: OrbiterState, syncer):
        if not state.active_positions: return []
        to_square, port_pnl, evaluated = [], 0.0, []

        for token, info in list(state.active_positions.items()):
            data = state.client.SYMBOLDICT.get(token) or {}
            ltp = float(data.get('ltp') or state.client.get_ltp(token) or 0)
            if ltp == 0: continue

            strategy = info.get('strategy', '')
            
            # ✅ PnL for Futures
            if 'FUTURE' in strategy:
                profit_pct = ((ltp - info['entry_price']) / info['entry_price'] * 100.0)
                if 'SHORT' in strategy: profit_pct = -profit_pct
                
                info['max_profit_pct'] = max(info.get('max_profit_pct', 0.0), profit_pct)
                pos_pnl = (profit_pct / 100.0) * info['entry_price'] * info.get('lot_size', 0)
                info['max_pnl_rs'] = max(info.get('max_pnl_rs', 0.0), pos_pnl)
                port_pnl += pos_pnl
                
                if state.verbose_logs:
                    print(f"📈 FUT {token}: PnL=₹{pos_pnl:.2f} ({profit_pct:.2f}%) [LTP: {ltp:.2f}] Max={info.get('max_profit_pct', 0.0):.2f}%")
                
                # For compatibility with legacy filters
                atm_ltp, hdg_ltp = 0, 0 

            # ✅ PnL for Spreads
            else:
                atm_ltp = state.client.get_option_ltp_by_symbol(info.get('atm_symbol'))
                hdg_ltp = state.client.get_option_ltp_by_symbol(info.get('hedge_symbol'))
                
                if atm_ltp and hdg_ltp:
                    current_net = atm_ltp - hdg_ltp
                    data['current_net_premium'] = current_net
                    entry_net, basis = info.get('entry_net_premium', 0), info.get('atm_premium_entry', 0)
                    if entry_net != 0 and basis != 0:
                        profit_pct = (entry_net - current_net) / abs(basis) * 100.0
                        info['max_profit_pct'] = max(info.get('max_profit_pct', 0.0), profit_pct)
                        pos_pnl = (entry_net - current_net) * info.get('lot_size', 0)
                        info['max_pnl_rs'] = max(info.get('max_pnl_rs', 0.0), pos_pnl)
                        port_pnl += pos_pnl
                        if state.verbose_logs:
                            print(f"📈 POS {token}: PnL=₹{pos_pnl:.2f} ({profit_pct:.2f}%) [LTP: {ltp:.2f}] [ATM: {atm_ltp:.2f} HDG: {hdg_ltp:.2f} NET: {current_net:.2f}] Max={info.get('max_profit_pct', 0.0):.2f}%")
            
            evaluated.append((token, info, ltp, data, atm_ltp, hdg_ltp))

        target_t, sl_t = state.config.get('TOTAL_TARGET_PROFIT_RS', 0), state.config.get('TOTAL_STOP_LOSS_RS', 0)
        if state.verbose_logs and state.active_positions:
            print(f"📊 Portfolio PnL: ₹{port_pnl:.2f} (Target: ₹{target_t} SL: -₹{sl_t})")
        mass_reason = None
        if target_t > 0 and port_pnl >= target_t: mass_reason = f"Portfolio Target: ₹{port_pnl:.2f} >= ₹{target_t}"
        elif sl_t > 0 and port_pnl <= -sl_t: mass_reason = f"Portfolio SL: ₹{port_pnl:.2f} <= -₹{sl_t}"
            
        if mass_reason:
            print(f"🚨 MASS EXIT: {mass_reason}")
            res = self.square_off_all(state, reason=mass_reason)
            syncer.sync_active_positions_to_sheets(state)
            return res

        for token, info, ltp, data, atm_exit, hdg_exit in evaluated:
            res = None
            # Inject candles into data for technical SL filters
            data['candles'] = state.client.api.get_time_price_series(
                exchange=token.split("|")[0] if "|" in token else 'NSE',
                token=token.split("|")[-1],
                starttime=int(info['entry_time'].timestamp()) - 3600, # 1 hour buffer
                endtime=int(datetime.now(pytz.timezone('Asia/Kolkata')).timestamp()),
                interval=1
            )
            
            for f in (self.sl_filters + self.tp_filters):
                try: cand = f.evaluate(info, float(ltp), data)
                except Exception as e: cand = {'hit': False, 'reason': f"err:{e}"}
                if cand and cand.get('hit'):
                    res = cand
                    if 'reason' not in res: res['reason'] = f.key
                    break

            if res and res.get('hit'):
                if state.config.get('OPTION_EXECUTE', False):
                    qty, atm_s, hdg_s = info.get('lot_size', 0), info.get('atm_symbol'), info.get('hedge_symbol')
                    if qty > 0 and atm_s and hdg_s:
                        for side, sym, rem in [('B', atm_s, 'sl_atm'), ('S', hdg_s, 'sl_hdg')]:
                            state.client.api.place_order(buy_or_sell=side, product_type=state.config.get('OPTION_PRODUCT_TYPE'),
                                                       exchange='NFO', tradingsymbol=sym, quantity=qty, discloseqty=0,
                                                       price_type='MKT', price=0, retention='DAY', remarks=f'SLTP_{rem}')

                # Calculate final spread for logging/alerts
                exit_net = (atm_exit - hdg_exit) if (atm_exit and hdg_exit) else 0

                so = {
                    'token': token, 'symbol': info.get('symbol'), 'company_name': info.get('company_name'),
                    'entry_price': info.get('entry_price'), 'exit_price': float(ltp), 'pct_change': res.get('pct', 0),
                    'reason': res.get('reason', 'SL HIT'), 'strategy': info.get('strategy'), 'expiry': info.get('expiry'),
                    'atm_strike': info.get('atm_strike'), 'hedge_strike': info.get('hedge_strike'), 'atm_symbol': info.get('atm_symbol'),
                    'hedge_symbol': info.get('hedge_symbol'), 'atm_premium_entry': info.get('atm_premium_entry'),
                    'hedge_premium_entry': info.get('hedge_premium_entry'), 'atm_premium_exit': atm_exit,
                    'hedge_premium_exit': hdg_exit, 'exit_net_premium': exit_net, 'lot_size': info.get('lot_size', 0),
                    'entry_time': info.get('entry_time').strftime("%Y-%m-%d %H:%M:%S IST") if info.get('entry_time') else "N/A"
                }
                to_square.append(so)
                if token in state.active_positions: 
                    del state.active_positions[token]
                    state.exit_history[token] = time.time() # 🔥 Record exit for cooldown
        if to_square:
            if self.log_closed_positions: self.log_closed_positions(to_square)
            syncer.sync_active_positions_to_sheets(state)
        return to_square
