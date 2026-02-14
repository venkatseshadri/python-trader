from .state import OrbiterState

class Syncer:
    def __init__(self, update_active_positions):
        self.update_active_positions = update_active_positions

    def sync_active_positions_to_sheets(self, state: OrbiterState):
        """Push current active positions to Google Sheets"""
        if not self.update_active_positions: return
        if state.verbose_logs:
            print(f"🔄 Syncing {len(state.active_positions)} positions to Google Sheets...")

        payload = []
        for token, info in state.active_positions.items():
            data = state.client.SYMBOLDICT.get(token, {})
            ltp = data.get('ltp', data.get('lp', 0))
            
            span_cache = state.client.span_cache or {}
            base_sym = info.get('company_name')
            span_key = f"{base_sym}|{state.config.get('OPTION_EXPIRY')}|{state.config.get('OPTION_INSTRUMENT')}|{state.config.get('HEDGE_STEPS')}"
            margin_info = span_cache.get(span_key, {})
            
            strategy = info.get('strategy', 'PUT_CREDIT_SPREAD')
            total_margin = margin_info.get('pe' if strategy == 'PUT_CREDIT_SPREAD' else 'ce', {}).get('total_margin', 0)

            entry_net, basis = info.get('entry_net_premium', 0), info.get('atm_premium_entry', 0)
            pnl_rs, pnl_pct = 0, 0
            
            current_net = data.get('current_net_premium')
            if current_net is not None and entry_net != 0:
                pnl_rs = (entry_net - current_net) * info.get('lot_size', 0)
                if basis != 0: pnl_pct = (entry_net - current_net) / abs(basis) * 100.0

            payload.append({
                'entry_time': info.get('entry_time').strftime("%Y-%m-%d %H:%M:%S IST") if info.get('entry_time') else "N/A",
                'token': token, 'symbol': info.get('symbol'), 'company_name': info.get('company_name'),
                'entry_price': info.get('entry_price'), 'ltp': ltp, 'pnl_pct': pnl_pct, 'pnl_rs': pnl_rs,
                'max_profit_pct': info.get('max_profit_pct', 0), 'max_pnl_rs': info.get('max_pnl_rs', 0),
                'strategy': strategy, 'expiry': info.get('expiry'), 'atm_symbol': info.get('atm_symbol'),
                'hedge_symbol': info.get('hedge_symbol'), 'total_margin': total_margin
            })
        
        self.update_active_positions(payload)
