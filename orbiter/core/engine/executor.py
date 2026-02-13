from datetime import datetime
import time
import pytz
import re
from utils.utils import safe_ltp
from .state import OrbiterState

class Executor:
    def __init__(self, log_buy_signals, log_closed_positions, sl_filters, tp_filters):
        self.log_buy_signals = log_buy_signals
        self.log_closed_positions = log_closed_positions
        self.sl_filters = sl_filters
        self.tp_filters = tp_filters

    def rank_signals(self, state: OrbiterState, scores, syncer):
        """Process signals and place orders"""
        buy_signals = []
        ranked = sorted(scores.items(), key=lambda x: abs(x[1]), reverse=True)[:state.config['TOP_N']]
        exec_mode = state.config.get('EXECUTION_MODE', 'CREDIT_SPREAD')
        seg_name = state.config.get('segment_name', 'nfo')
        
        for token, score in ranked:
            if token in state.active_positions: continue

            if score >= state.config['TRADE_SCORE'] or score <= -state.config['TRADE_SCORE']:
                data = state.client.SYMBOLDICT.get(token)
                results = state.filter_results_cache.get(token, {})
                orb_r = results.get('ef1_orb', {})
                ema_r = results.get('ef2_price_above_5ema', {})
                ltp, ltp_display, symbol_full = safe_ltp(data, token)
                
                base_symbol = data.get('company_name') or symbol_full
                if isinstance(base_symbol, str):
                    base_symbol = re.sub(r'\d{2}[A-Z]{3}\d{2}[FC]$', '', base_symbol)
                    if base_symbol.endswith('-EQ'): base_symbol = base_symbol[:-3]
                    base_symbol = base_symbol.strip()

                is_bull = score >= state.config['TRADE_SCORE']
                
                if exec_mode == 'CREDIT_SPREAD':
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
                        'exchange': spread.get('exchange', 'NFO'),
                        **{k: span_m.get(k, 0) for k in ['span', 'expo', 'total_margin', 'pledged_required', 'span_trade', 'expo_trade', 'pre_trade', 'add', 'add_trade', 'ten', 'ten_trade', 'del', 'del_trade', 'spl', 'spl_trade']}
                    }
                    state.active_positions[token] = {
                        'entry_price': ltp, 'entry_time': datetime.now(pytz.timezone('Asia/Kolkata')),
                        'symbol': symbol_full, 'company_name': base_symbol, 'strategy': sig['strategy'],
                        'atm_symbol': sig['atm_symbol'], 'hedge_symbol': sig['hedge_symbol'],
                        'expiry': sig['expiry'], 'atm_strike': sig['atm_strike'], 'hedge_strike': sig['hedge_strike'],
                        'atm_premium_entry': atm_p, 'hedge_premium_entry': hdg_p,
                        'entry_net_premium': (atm_p - hdg_p) if (atm_p and hdg_p) else 0,
                        'lot_size': spread.get('lot_size', 0), 'config': state.config,
                        'exchange': sig['exchange'], 'exec_mode': 'CREDIT_SPREAD'
                    }
                else: # FUTURES MODE
                    side = 'B' if is_bull else 'S'
                    exch = 'MCX' if seg_name == 'mcx' else 'NFO'
                    fut = state.client.place_future_order(
                        symbol=base_symbol, side=side, exchange=exch,
                        execute=state.config.get('OPTION_EXECUTE'),
                        product_type=state.config.get('OPTION_PRODUCT_TYPE'),
                        price_type=state.config.get('OPTION_PRICE_TYPE')
                    )
                    if not fut.get('ok') and not fut.get('dry_run'):
                        print(f"⚠️ Future order failed for {base_symbol}: {fut.get('reason')}")
                        continue
                    
                    sig = {
                        'token': token, 'symbol': symbol_full, 'company_name': base_symbol,
                        'ltp': ltp, 'ltp_display': ltp_display, 'score': score,
                        'orb_high': orb_r.get('orb_high', 0), 'orb_low': orb_r.get('orb_low', 0),
                        'ema5': ema_r.get('ema5', 0), 'strategy': 'FUTURE_LONG' if is_bull else 'FUTURE_SHORT',
                        'expiry': 'N/A', 'atm_symbol': fut.get('tsym'), 'hedge_symbol': 'N/A',
                        'dry_run': fut.get('dry_run', False), 'exchange': exch,
                        'span': 0, 'total_margin': 0
                    }
                    
                    # Align with Spread math for filters:
                    # Long: Profit if LTP rises. (Entry - Current) needs to be positive.
                    # So EntryNet = -EntryPrice, CurrentNet = -CurrentLTP.
                    # (-EntryPrice - (-CurrentLTP)) = CurrentLTP - EntryPrice.
                    entry_net = -ltp if is_bull else ltp
                    
                    state.active_positions[token] = {
                        'entry_price': ltp, 'entry_time': datetime.now(pytz.timezone('Asia/Kolkata')),
                        'symbol': symbol_full, 'company_name': base_symbol, 'strategy': sig['strategy'],
                        'tsym': fut.get('tsym'), 'lot_size': fut.get('lot_size', 0),
                        'side': side, 'exchange': exch, 'exec_mode': 'FUTURES',
                        'entry_net_premium': entry_net,
                        'atm_premium_entry': ltp # Basis for % calculation
                    }

                buy_signals.append(sig)
                print(f"✅ POSITION ADDED: {token} @ {ltp} ({exec_mode})")
        
        if buy_signals:
            self.log_buy_signals(buy_signals, segment_name=seg_name)
            syncer.sync_active_positions_to_sheets(state)
        return buy_signals

    def square_off_all(self, state: OrbiterState, reason="EOD EXIT"):
        if not state.active_positions: return []
        to_square = []
        exec_orders = state.config.get('OPTION_EXECUTE', False)
        seg_name = state.config.get('segment_name', 'nfo')
        
        for token, info in list(state.active_positions.items()):
            ltp = state.client.get_ltp(token) or info.get('entry_price', 0)
            mode = info.get('exec_mode', 'CREDIT_SPREAD')
            
            if mode == 'CREDIT_SPREAD':
                atm_p_exit = state.client.get_option_ltp_by_symbol(info.get('atm_symbol'))
                hdg_p_exit = state.client.get_option_ltp_by_symbol(info.get('hedge_symbol'))
                entry_net, basis = info.get('entry_net_premium', 0), info.get('atm_premium_entry', 0)
                pct = (entry_net - (atm_p_exit - hdg_p_exit)) / abs(basis) * 100.0 if entry_net != 0 and basis != 0 and atm_p_exit and hdg_p_exit else 0.0
                
                if exec_orders:
                    exch = info.get('exchange', 'NFO')
                    for s, sym, rem in [('B', info['atm_symbol'], 'sq_atm'), ('S', info['hedge_symbol'], 'sq_hdg')]:
                        state.client.api.place_order(buy_or_sell=s, product_type=state.config['OPTION_PRODUCT_TYPE'], exchange=exch,
                                                   tradingsymbol=sym, quantity=info['lot_size'], price_type='MKT', price=0, retention='DAY', remarks=f'{reason}_{rem}')
            else: # FUTURES
                entry_p = info.get('entry_price', 0)
                side = info.get('side', 'B')
                pct = (ltp - entry_p) / entry_p * 100.0 if side == 'B' else (entry_p - ltp) / entry_p * 100.0
                if exec_orders:
                    exit_side = 'S' if side == 'B' else 'B'
                    state.client.api.place_order(buy_or_sell=exit_side, product_type=state.config['OPTION_PRODUCT_TYPE'], exchange=info['exchange'],
                                               tradingsymbol=info['tsym'], quantity=info['lot_size'], price_type='MKT', price=0, retention='DAY', remarks=f'{reason}_sq_fut')
                atm_p_exit = hdg_p_exit = 0

            to_square.append({
                'token': token, 'symbol': info.get('symbol'), 'company_name': info.get('company_name'),
                'entry_price': info.get('entry_price'), 'exit_price': float(ltp), 'pct_change': pct, 'reason': reason,
                'strategy': info.get('strategy'), 'expiry': info.get('expiry', 'N/A'),
                'atm_premium_entry': info.get('atm_premium_entry', 0), 'hedge_premium_entry': info.get('hedge_premium_entry', 0),
                'atm_premium_exit': atm_p_exit, 'hedge_premium_exit': hdg_p_exit, 'lot_size': info.get('lot_size', 0),
                'entry_time': info.get('entry_time').strftime("%Y-%m-%d %H:%M:%S IST") if info.get('entry_time') else "N/A"
            })

        state.active_positions.clear()
        if to_square and self.log_closed_positions: self.log_closed_positions(to_square, segment_name=seg_name)
        return to_square

    def check_sl(self, state: OrbiterState, syncer):
        if not state.active_positions: return []
        to_square, port_pnl, evaluated = [], 0.0, []
        seg_name = state.config.get('segment_name', 'nfo')

        for token, info in list(state.active_positions.items()):
            data = state.client.SYMBOLDICT.get(token) or {}
            ltp = float(data.get('ltp') or state.client.get_ltp(token) or 0)
            if ltp == 0: continue
            
            mode = info.get('exec_mode', 'CREDIT_SPREAD')
            if mode == 'CREDIT_SPREAD':
                atm_ltp = state.client.get_option_ltp_by_symbol(info.get('atm_symbol'))
                hdg_ltp = state.client.get_option_ltp_by_symbol(info.get('hedge_symbol'))
                if atm_ltp and hdg_ltp:
                    curr_net = atm_ltp - hdg_ltp
                    data['current_net_premium'] = curr_net
                    entry_net, basis = info.get('entry_net_premium', 0), info.get('atm_premium_entry', 0)
                    if entry_net != 0 and basis != 0:
                        profit_pct = (entry_net - curr_net) / abs(basis) * 100.0
                        info['max_profit_pct'] = max(info.get('max_profit_pct', 0.0), profit_pct)
                        pos_pnl = (entry_net - current_net) * info.get('lot_size', 0)
                        info['max_pnl_rs'] = max(info.get('max_pnl_rs', 0.0), pos_pnl)
                        port_pnl += pos_pnl
                evaluated.append((token, info, ltp, data, atm_ltp, hdg_ltp))
            else: # FUTURES
                entry_p, side = info.get('entry_price', 0), info.get('side', 'B')
                pos_pnl = (ltp - entry_p) * info.get('lot_size', 0) if side == 'B' else (entry_p - ltp) * info.get('lot_size', 0)
                profit_pct = (ltp - entry_p) / entry_p * 100.0 if side == 'B' else (entry_p - ltp) / entry_p * 100.0
                info['max_profit_pct'] = max(info.get('max_profit_pct', 0.0), profit_pct)
                info['max_pnl_rs'] = max(info.get('max_pnl_rs', 0.0), pos_pnl)
                port_pnl += pos_pnl
                data['current_net_premium'] = -ltp if side == 'B' else ltp
                evaluated.append((token, info, ltp, data, 0, 0))

        # Portfolio Kill-switch
        target_t, sl_t = state.config.get('TOTAL_TARGET_PROFIT_RS', 0), state.config.get('TOTAL_STOP_LOSS_RS', 0)
        mass_reason = None
        if target_t > 0 and port_pnl >= target_t: mass_reason = f"Portfolio Target: ₹{port_pnl:.2f}"
        elif sl_t > 0 and port_pnl <= -sl_t: mass_reason = f"Portfolio SL: ₹{port_pnl:.2f}"
        if mass_reason:
            res = self.square_off_all(state, reason=mass_reason)
            syncer.sync_active_positions_to_sheets(state)
            return res

        for token, info, ltp, data, atm_exit, hdg_exit in evaluated:
            res = None
            for f in (self.sl_filters + self.tp_filters):
                try: cand = f.evaluate(info, float(ltp), data)
                except Exception: cand = {'hit': False}
                if cand and cand.get('hit'):
                    res = cand
                    if 'reason' not in res: res['reason'] = f.key
                    break

            if res and res.get('hit'):
                mode = info.get('exec_mode', 'CREDIT_SPREAD')
                if state.config.get('OPTION_EXECUTE', False):
                    qty, exch = info['lot_size'], info['exchange']
                    if mode == 'CREDIT_SPREAD':
                        for s, sym, rem in [('B', info['atm_symbol'], 'sl_atm'), ('S', info['hedge_symbol'], 'sl_hdg')]:
                            state.client.api.place_order(buy_or_sell=s, product_type=state.config['OPTION_PRODUCT_TYPE'], exchange=exch,
                                                       tradingsymbol=sym, quantity=qty, price_type='MKT', price=0, retention='DAY', remarks=f'SLTP_{rem}')
                    else: # FUTURES
                        exit_side = 'S' if info['side'] == 'B' else 'B'
                        state.client.api.place_order(buy_or_sell=exit_side, product_type=state.config['OPTION_PRODUCT_TYPE'], exchange=exch,
                                                   tradingsymbol=info['tsym'], quantity=qty, price_type='MKT', price=0, retention='DAY', remarks='SLTP_fut')

                so = {
                    'token': token, 'symbol': info.get('symbol'), 'company_name': info.get('company_name'),
                    'entry_price': info.get('entry_price'), 'exit_price': float(ltp), 'pct_change': res.get('pct', 0),
                    'reason': res.get('reason', 'SL HIT'), 'strategy': info.get('strategy'), 'expiry': info.get('expiry', 'N/A'),
                    'atm_premium_entry': info.get('atm_premium_entry', 0), 'hedge_premium_entry': info.get('hedge_premium_entry', 0),
                    'atm_premium_exit': atm_exit, 'hedge_premium_exit': hdg_exit, 'lot_size': info.get('lot_size', 0),
                    'entry_time': info.get('entry_time').strftime("%Y-%m-%d %H:%M:%S IST") if info.get('entry_time') else "N/A"
                }
                to_square.append(so)
                if token in state.active_positions: del state.active_positions[token]

        if to_square:
            if self.log_closed_positions: self.log_closed_positions(to_square, segment_name=seg_name)
            syncer.sync_active_positions_to_sheets(state)
        return to_square
