from .state import OrbiterState

class Syncer:
    def __init__(self, update_active_positions):
        self.update_active_positions = update_active_positions

    def sync_active_positions_to_sheets(self, state: OrbiterState):
        """Push current active positions to Google Sheets"""
        if not self.update_active_positions: return

        payload = []
        for token, info in state.active_positions.items():
            data = state.client.SYMBOLDICT.get(token, {})
            ltp = data.get('ltp', data.get('lp', 0))
            mode = info.get('exec_mode', 'CREDIT_SPREAD')
            
            pnl_rs, pnl_pct = 0.0, 0.0
            
            if mode == 'CREDIT_SPREAD':
                entry_net, basis = info.get('entry_net_premium', 0), info.get('atm_premium_entry', 0)
                current_net = data.get('current_net_premium')
                if current_net is not None and entry_net != 0:
                    pnl_rs = (entry_net - current_net) * info.get('lot_size', 0)
                    if basis != 0: pnl_pct = (entry_net - current_net) / abs(basis) * 100.0
                
                atm_s, hdg_s = info.get('atm_symbol'), info.get('hedge_symbol')
                exp = info.get('expiry')
            else: # FUTURES
                entry_p, side = info.get('entry_price', 0), info.get('side', 'B')
                pnl_rs = (ltp - entry_p) * info.get('lot_size', 0) if side == 'B' else (entry_p - ltp) * info.get('lot_size', 0)
                if entry_p != 0: pnl_pct = (pnl_rs / (entry_p * info.get('lot_size', 1))) * 100.0
                
                atm_s, hdg_s = info.get('tsym'), 'N/A'
                exp = 'N/A'

            payload.append({
                'entry_time': info.get('entry_time').strftime("%Y-%m-%d %H:%M:%S IST") if info.get('entry_time') else "N/A",
                'token': token, 'symbol': info.get('symbol'), 'company_name': info.get('company_name'),
                'entry_price': info.get('entry_price'), 'ltp': ltp, 'pnl_pct': pnl_pct, 'pnl_rs': pnl_rs,
                'max_profit_pct': info.get('max_profit_pct', 0), 'max_pnl_rs': info.get('max_pnl_rs', 0),
                'strategy': info.get('strategy'), 'expiry': exp, 'atm_symbol': atm_s,
                'hedge_symbol': hdg_s, 'total_margin': 0 # Future margin integration planned
            })
        
        seg_name = state.config.get('segment_name', 'nfo')
        self.update_active_positions(payload, segment_name=seg_name)
