from datetime import datetime
import time
import pytz
import re
import numpy as np
from utils.utils import safe_ltp, safe_float
from utils.telegram_notifier import send_telegram_msg
from .state import OrbiterState

class Executor:
    def __init__(self, log_buy_signals, log_closed_positions, sl_filters, tp_filters, summary_manager=None):
        self.log_buy_signals = log_buy_signals
        self.log_closed_positions = log_closed_positions
        self.sl_filters = sl_filters
        self.tp_filters = tp_filters
        self.summary = summary_manager

    def rank_signals(self, state: OrbiterState, scores, syncer):
        """Process signals and place orders"""
        buy_signals = []
        ranked = sorted(scores.items(), key=lambda x: abs(x[1]), reverse=True)[:state.config['TOP_N']]
        
        for i, (token, score) in enumerate(ranked):
            if token in state.active_positions: continue

            # 🔥 NIFTY-ONLY WHITELIST (v3.15.0)
            # Ensure only NIFTY is considered for this live sprint
            data = state.client.SYMBOLDICT.get(token)
            symbol_check = data.get('t', '').upper() if data else ''
            if 'NIFTY' not in symbol_check and '51714' not in token:
                continue

            # 🔥 NEW: Score Velocity Tracking
            if token not in state.opening_scores and abs(score) > 0.1:
                state.opening_scores[token] = score
            
            opening = state.opening_scores.get(token, score)
            velocity = score - opening
            velocity_str = f"({'+' if velocity >= 0 else ''}{velocity:.2f})"

            if state.verbose_logs and i == 0:
                data = state.client.SYMBOLDICT.get(token)
                symbol_full = data.get('ts') if data else token
                print(f"🔍 Evaluated {len(scores)} symbols. Top Signal: {symbol_full} Score: {score:.2f} {velocity_str}")

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
                
                # 🔥 NEW: Price Guard (v3.14.1)
                max_p = state.config.get('MAX_NOMINAL_PRICE', 999999)
                if ltp > max_p:
                    print(f"🛡️ Price Guard: {symbol_full} price ₹{ltp:,.0f} > Cap ₹{max_p:,.0f}. Skipping.")
                    continue

                # 🔥 NEW: Trend-State Guards
                try:
                    candle_data = data.get('candles', []) if data else []
                    entry_atr = 0
                    if len(candle_data) >= 15:
                        import talib
                        # Strict filtering for valid candle data
                        valid_candles = [c for c in candle_data if c.get('stat')=='Ok' and c.get('intc') and c.get('inth') and c.get('intl')]
                        
                        if len(valid_candles) < 15:
                            print(f"🛡️ Guard: {symbol_full} insufficient valid candles ({len(valid_candles)} < 15). Skipping.")
                            continue

                        closes_raw = np.array([safe_float(c.get('intc')) for c in valid_candles], dtype=float)
                        highs_raw = np.array([safe_float(c.get('inth')) for c in valid_candles], dtype=float)
                        lows_raw = np.array([safe_float(c.get('intl')) for c in valid_candles], dtype=float)
                        
                        atrs = talib.ATR(highs_raw, lows_raw, closes_raw, timeperiod=14)
                        entry_atr = float(atrs[-1]) if not np.isnan(atrs[-1]) else 0

                        # Determine direction early for Guard
                        is_bull_guard = score > 0 
                        is_sideways_guard = results.get('regime') == 'SIDEWAYS'

                        # 🧠 STRATEGY GUARD LOGIC
                        # Trending trades (Breakouts) require Slope & Freshness.
                        # Sideways trades (Mean Reversion) are exempt from these as they trade the bounce.
                        if not is_sideways_guard:
                            # 1. Slope Guard (EMA5 Direction)
                            ema5 = talib.EMA(closes_raw, timeperiod=5)
                            if len(ema5) >= 6 and not np.isnan(ema5[-1]) and not np.isnan(ema5[-6]):
                                slope = ema5[-1] - ema5[-6]
                                if is_bull_guard and slope < 0:
                                    print(f"🛡️ Guard: {symbol_full} slope negative for LONG. Skipping.")
                                    continue
                                elif not is_bull_guard and slope > 0:
                                    print(f"🛡️ Guard: {symbol_full} slope positive for SHORT. Skipping.")
                                    continue
                            
                            # 2. Freshness Guard (Near RECENT high/low)
                            freshness_limit = 0.995 if token.startswith('MCX|') else 0.998
                            if is_bull_guard:
                                recent_high = np.max(highs_raw[-15:]) 
                                if ltp < recent_high * freshness_limit:
                                    print(f"🛡️ Guard: {symbol_full} stale LONG (LTP {ltp} < Recent High {recent_high} * {freshness_limit}). Skipping.")
                                    continue
                            else:
                                # Short Guard: LTP shouldn't be too far ABOVE recent low
                                recent_low = np.min(lows_raw[-15:])
                                buffer = 1 + (1 - freshness_limit)
                                if ltp > recent_low * buffer:
                                    print(f"🛡️ Guard: {symbol_full} stale SHORT (LTP {ltp} > Recent Low {recent_low} * {buffer:.4f}). Skipping.")
                                    continue
                        else:
                            if state.verbose_logs:
                                print(f"🌊 Sideways Mode: {symbol_full} bypassing trend guards.")
                    else:
                        print(f"🛡️ Guard: {symbol_full} insufficient candles ({len(candle_data)} < 15). Skipping.")
                        continue
                except Exception as e:
                    print(f"⚠️ Guard Error for {symbol_full}: {e}")
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

                    # 🧠 MARGIN GUARD (MCX) (v3.13.1)
                    span_m = None
                    fut_res = state.client.resolver.get_near_future(base_symbol, 'MCX', state.client.api)
                    if fut_res:
                        lot_size = state.client.master.TOKEN_TO_LOTSIZE.get(t_id_raw, 0)
                        if lot_size <= 0:
                            for r in state.client.master.DERIVATIVE_OPTIONS:
                                if r.get('tradingsymbol') == fut_res['tsym']:
                                    lot_size = int(r.get('lot_size', 0))
                                    break
                        if lot_size > 0:
                            fut_details = {'tsym': fut_res['tsym'], 'lot_size': lot_size, 'exchange': 'MCX', 'token': token}
                            span_m = state.client.calculate_future_margin(fut_details, product_type=state.config.get('OPTION_PRODUCT_TYPE'))
                            if span_m.get('ok'):
                                req_margin = span_m.get('total_margin', 0)
                                limits = state.client.get_limits()
                                total_power = limits.get('total_power', 0) if limits else 0
                                sim_used = sum(p.get('total_margin', 0) for p in state.active_positions.values())
                                
                                if False: # FORCED RECOVERY - NO MARGIN LIMIT (v3.13.8)
                                    print(f"🛡️ Margin Guard: {fut_res['tsym']} requires ₹{req_margin:,.0f} (Total Sim Used: ₹{sim_used:,.0f}) but only ₹{total_power:,.0f} power. Skipping.")
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
                    
                    # 🧠 Regime-Specific Stop Loss (v3.14.0)
                    regime = results.get('regime', 'TRENDING')
                    sl_mult = state.config.get('SL_MULT_TRENDING', 1.5) if regime == 'TRENDING' else state.config.get('SL_MULT_SIDEWAYS', 0.25)

                    state.active_positions[token] = {
                        'entry_price': ltp, 'entry_time': datetime.now(pytz.timezone('Asia/Kolkata')),
                        'symbol': symbol_full, 'company_name': base_symbol, 'strategy': sig['strategy'],
                        'orb_high': sig['orb_high'], 'orb_low': sig['orb_low'],
                        'lot_size': sig['lot_size'],
                        'total_margin': span_m.get('total_margin', 0) if (span_m and span_m.get('ok')) else 0,
                        'regime': regime,
                        'target_profit_rs': state.config.get('TARGET_PROFIT_RS', 0),
                        'stop_loss_rs': state.config.get('STOP_LOSS_RS', 0),
                        'future_max_loss_pct': state.config.get('FUTURE_MAX_LOSS_PCT', 5.0),
                        'tsl_retracement_pct': state.config.get('TSL_RETREACEMENT_PCT', 50),
                        'tsl_activation_rs': state.config.get('TSL_ACTIVATION_RS', 1000),
                        'tp_trail_activation': state.config.get('TP_TRAIL_ACTIVATION', 1.5),
                        'tp_trail_gap': state.config.get('TP_TRAIL_GAP', 0.75),
                        'entry_atr': entry_atr,
                        'atr_sl_mult': sl_mult
                    }
                    buy_signals.append(sig) # 🔥 Capture signal for summary alert

                else:
                    # 1. Resolve Contracts (v3.14.5 - Dynamic instrument detection)
                    res = state.client.resolver.get_credit_spread_contracts(
                        base_symbol, ltp, 'PUT' if score > 0 else 'CALL', 
                        state.config.get('HEDGE_STEPS'), state.config.get('OPTION_EXPIRY'), 
                        None # instrument set dynamically by resolver
                    )

                    
                    if not res.get('ok'):
                        print(f"⚠️ Spread resolution failed for {base_symbol}: {res.get('reason')}")
                        continue
                    
                    # 2. 🔥 MARGIN GUARD (v3.13.1)
                    span_m = state.client.calculate_span_for_spread(res, product_type=state.config.get('OPTION_PRODUCT_TYPE'))
                    if span_m.get('ok'):
                        req_margin = span_m.get('total_margin', 0)
                        limits = state.client.get_limits()
                        total_power = limits.get('total_power', 0) if limits else 0
                        
                        # Calculate total simulated margin used by all active positions
                        sim_used = sum(p.get('total_margin', 0) for p in state.active_positions.values())
                        
                        if (req_margin + sim_used) > total_power:
                            print(f"🛡️ Margin Guard: {base_symbol} requires ₹{req_margin:,.0f} (Total Sim Used: ₹{sim_used:,.0f}) but only ₹{total_power:,.0f} power. Skipping.")
                            continue
                        
                        if state.verbose_logs:
                            print(f"💰 Margin Check: {base_symbol} OK (Req: ₹{req_margin:,.0f} | Sim Used: ₹{sim_used:,.0f} | Power: ₹{total_power:,.0f})")

                    # 3. Execute/Simulate
                    spread = state.client.executor.place_spread(
                        res, state.config.get('OPTION_EXECUTE'), 
                        state.config.get('OPTION_PRODUCT_TYPE'), state.config.get('OPTION_PRICE_TYPE')
                    )

                    if not spread.get('ok'):
                        print(f"⚠️ Spread failed for {base_symbol}: {spread.get('reason')}")
                        continue

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

                    # 🧠 Regime-Specific Stop Loss (v3.14.0)
                    regime = results.get('regime', 'TRENDING')
                    sl_mult = state.config.get('SL_MULT_TRENDING', 0.25) if regime == 'TRENDING' else state.config.get('SL_MULT_SIDEWAYS', 0.10)

                    state.active_positions[token] = {
                        'entry_price': ltp, 'entry_time': datetime.now(pytz.timezone('Asia/Kolkata')),
                        'symbol': symbol_full, 'company_name': base_symbol, 'strategy': sig['strategy'],
                        'atm_symbol': sig['atm_symbol'], 'hedge_symbol': sig['hedge_symbol'],
                        'expiry': sig['expiry'], 'atm_strike': sig['atm_strike'], 'hedge_strike': sig['hedge_strike'],
                        'atm_premium_entry': atm_p, 'hedge_premium_entry': hdg_p,
                        'orb_high': sig['orb_high'], 'orb_low': sig['orb_low'],
                        'entry_net_premium': (atm_p - hdg_p) if (atm_p and hdg_p) else 0,
                        'lot_size': spread.get('lot_size', 0),
                        'total_margin': span_m.get('total_margin', 0),
                        'regime': regime,
                        'target_profit_rs': state.config.get('TARGET_PROFIT_RS', 0),
                        'stop_loss_rs': state.config.get('STOP_LOSS_RS', 0),
                        'future_max_loss_pct': state.config.get('FUTURE_MAX_LOSS_PCT', 5.0),
                        'tsl_retracement_pct': state.config.get('TSL_RETREACEMENT_PCT', 50),
                        'tsl_activation_rs': state.config.get('TSL_ACTIVATION_RS', 1000),
                        'tp_trail_activation': state.config.get('TP_TRAIL_ACTIVATION', 1.5),
                        'tp_trail_gap': state.config.get('TP_TRAIL_GAP', 0.75),
                        'entry_atr': entry_atr,
                        'atr_sl_mult': sl_mult
                    }
                    buy_signals.append(sig) # 🔥 Capture signal for summary alert

        if buy_signals:
            self.log_buy_signals(buy_signals)
            syncer.sync_active_positions_to_sheets(state)
            
            # 🔥 NEW: Smart Batch Entry Notification
            lines = []
            for sig in buy_signals:
                v_str = state.opening_scores.get(sig['token'], 0)
                velocity = sig['score'] - v_str if v_str != 0 else 0
                lines.append(f"• `{sig['symbol']}` @ {sig['ltp']} [Score: {sig['score']:.2f} ({velocity:+.2f})]")
            
            summary = "\n".join(lines)
            try:
                # Get current margin for the final line
                margin_data = self.summary.get_current_funds()
                available = margin_data.get('available_margin', 0)
                
                msg = (f"🚀 *Positions Opened*\n\n{summary}\n\n"
                       f"💰 *Liquidity:* ₹{available/100000:.2f}L Available")
                send_telegram_msg(msg)
            except Exception as e:
                print(f"⚠️ UX Alert Failed: {e}")
                send_telegram_msg(f"🚀 *Positions Opened*\n\n{summary}")

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
        # 🔥 Reset Global TSL State on Mass Exit
        state.global_tsl_active = False
        state.max_portfolio_pnl = 0.0
        
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

            # 🔥 Record for Session Ledger
            state.realized_pnl += total_pnl
            state.trade_count += len(to_square)

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
            # ✅ Always calculate Stock Move % (The "Truth")
            stock_move_pct = ((ltp - info['entry_price']) / info['entry_price'] * 100.0)
            if 'SHORT' in strategy or 'PUT_CREDIT' in strategy: # PUT Spread is Bullish, but we track stock move
                pass # Stock Move is positive for long/bullish
            if 'FUTURE_SHORT' in strategy or 'CALL_CREDIT' in strategy:
                # We'll keep stock_move_pct as absolute stock change for SL filters
                pass

            # ✅ Calculate Cash PnL
            if 'FUTURE' in strategy:
                profit_pct = stock_move_pct
                if 'SHORT' in strategy: profit_pct = -profit_pct
                pos_pnl = (profit_pct / 100.0) * info['entry_price'] * info.get('lot_size', 0)
                info['pnl_rs'] = pos_pnl
                info['max_pnl_rs'] = max(info.get('max_pnl_rs', 0.0), pos_pnl)
                port_pnl += pos_pnl
                
                if state.verbose_logs:
                    print(f"📈 FUT {token}: PnL=₹{pos_pnl:.2f} [Stock: {stock_move_pct:+.2f}%] [LTP: {ltp:.2f}]")
                
                # For compatibility
                atm_ltp, hdg_ltp = 0, 0 

            else:
                # Spread
                atm_ltp = state.client.get_option_ltp_by_symbol(info.get('atm_symbol'))
                hdg_ltp = state.client.get_option_ltp_by_symbol(info.get('hedge_symbol'))
                
                if atm_ltp and hdg_ltp:
                    current_net = atm_ltp - hdg_ltp
                    data['current_net_premium'] = current_net
                    entry_net = info.get('entry_net_premium', 0)
                    pos_pnl = (entry_net - current_net) * info.get('lot_size', 0)
                    info['pnl_rs'] = pos_pnl
                    info['max_pnl_rs'] = max(info.get('max_pnl_rs', 0.0), pos_pnl)
                    port_pnl += pos_pnl
                    
                    if state.verbose_logs:
                        print(f"📈 POS {token}: PnL=₹{pos_pnl:.2f} [Stock: {stock_move_pct:+.2f}%] [LTP: {ltp:.2f}] [Spread: {current_net:.2f}]")
            
            evaluated.append((token, info, ltp, data, atm_ltp, hdg_ltp))

        target_t, sl_t = state.config.get('TOTAL_TARGET_PROFIT_RS', 0), state.config.get('TOTAL_STOP_LOSS_RS', 0)
        global_tsl_enabled = state.config.get('GLOBAL_TSL_ENABLED', False)
        global_tsl_pct = state.config.get('GLOBAL_TSL_PCT', 20.0)

        if state.verbose_logs and state.active_positions:
            print(f"📊 Portfolio PnL: ₹{port_pnl:.2f} (Target: ₹{target_t} SL: -₹{sl_t})")
            
        mass_reason = None
        
        # 1. Check for Global TSL Activation
        if global_tsl_enabled and target_t > 0:
            if port_pnl >= target_t:
                if not state.global_tsl_active:
                    state.global_tsl_active = True
                    print(f"🚀 GLOBAL TSL ACTIVATED: Portfolio PnL ₹{port_pnl:.2f} >= Target ₹{target_t}")
            
            if state.global_tsl_active:
                state.max_portfolio_pnl = max(state.max_portfolio_pnl, port_pnl)
                # Calculate drawdown allowed
                allowed_drop = state.max_portfolio_pnl * (global_tsl_pct / 100.0)
                trail_floor = state.max_portfolio_pnl - allowed_drop
                
                if state.verbose_logs:
                     print(f"🛡️ Global TSL Active: Peak ₹{state.max_portfolio_pnl:.2f} | Floor ₹{trail_floor:.2f} | Current ₹{port_pnl:.2f}")

                if port_pnl <= trail_floor:
                    mass_reason = f"Global TSL Hit: Peak ₹{state.max_portfolio_pnl:.2f}, Floor ₹{trail_floor:.2f}, Current ₹{port_pnl:.2f}"

        # 2. Legacy Hard Exits (if Global TSL disabled OR strict SL hit)
        if not mass_reason:
             if not global_tsl_enabled and target_t > 0 and port_pnl >= target_t: 
                 mass_reason = f"Portfolio Target: ₹{port_pnl:.2f} >= ₹{target_t}"
             elif sl_t > 0 and port_pnl <= -sl_t: 
                 mass_reason = f"Portfolio SL: ₹{port_pnl:.2f} <= -₹{sl_t}"
            
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
                    # 🧠 PROFIT EFFICIENCY GUARD (v3.13.0)
                    # For Sideways scalps, don't take tiny profits (< ₹500) 
                    # unless it's a Stop Loss (Reason starts with 'SL' or 'sf').
                    is_tp = not (cand.get('reason', '').startswith('SL') or cand.get('reason', '').startswith('sf'))
                    if info.get('regime') == 'SIDEWAYS' and is_tp and info.get('pnl_rs', 0) < 500:
                        continue

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
                    # 🔥 Record for Session Ledger
                    state.realized_pnl += info.get('pnl_rs', 0)
                    state.trade_count += 1
                    
                    del state.active_positions[token]
                    state.exit_history[token] = time.time() # 🔥 Record exit for cooldown
        if to_square:
            if self.log_closed_positions: self.log_closed_positions(to_square)
            syncer.sync_active_positions_to_sheets(state)
        return to_square
