import logging
from typing import Dict, List, Any
from datetime import datetime

class TaxCalculator:
    """
    🧮 Estimates Brokerage, STT, and Exchange Charges.
    """
    @staticmethod
    def estimate_charges(num_orders: int, gross_pnl: float, segment: str) -> float:
        # Brokerage: ₹20 per executed order leg
        brokerage = num_orders * 20.0
        
        # STT/Exchange/GST (Proxy: 0.05% for NFO, 0.03% for MCX)
        rate = 0.0005 if segment == 'NFO' else 0.0003
        statutory = abs(gross_pnl) * rate if gross_pnl != 0 else 0
        
        # Total
        return round(brokerage + statutory, 2)

class SummaryManager:
    """
    📊 Orchestrates Session-Start and Session-End Reporting.
    
    Data Source: BrokerClient (Shoonya API)
    Output: Formatted Telegram Messages.
    """
    
    def __init__(self, broker_client, segment_name: str, version: str = "3.x"):
        self.broker = broker_client
        self.segment = segment_name.upper()
        self.version = version
        self.logger = logging.getLogger(f"SummaryManager_{segment_name}")

    def get_current_funds(self) -> Dict[str, float]:
        """Programmatic access to margin data."""
        limits = self.broker.get_limits()
        if not limits:
            return {'available_margin': 0.0, 'used_margin': 0.0, 'cash': 0.0}
        return {
            'available_margin': limits['available'],
            'used_margin': limits['margin_used'],
            'cash': limits['liquid_cash']
        }

    def generate_pre_session_report(self) -> str:
        """9:30 AM (NFO) / 5:30 PM (MCX) Pre-Market Check."""
        limits = self.broker.get_limits()
        positions = self.broker.get_positions()
        
        msg = [f"🌅 *{self.segment} SESSION PREP* ({datetime.now().strftime('%H:%M')})"]
        msg.append(f"🤖 *Orbiter v{self.version}*")
        msg.append("-" * 25)
        
        if limits:
            msg.append(f"💰 *Total Buying Power:* ₹{limits['total_power']:,.2f}")
            msg.append(f"🔒 *Margin Used:* ₹{limits['margin_used']:,.2f}")
            msg.append(f"✅ *Net Available:* ₹{limits['available']:,.2f}")
            msg.append("-" * 20)
            msg.append(f"🏦 *Collateral Value:* ₹{limits['collateral_value']:,.2f}")
            msg.append(f"💵 *Ledger Cash:* ₹{limits['liquid_cash']:,.2f}")
            
            # Health check: Warn if liquid cash is dangerously low (< 5k)
            if limits['liquid_cash'] < 5000:
                msg.append("\n⚠️ *Warning:* Low liquid cash. MTM loss might lead to liquidations.")
        else:
            msg.append("⚠️ *Limits:* Could not fetch margin status.")

        overnight = [p for p in positions if int(p.get('netqty', 0)) != 0]
        if overnight:
            msg.append(f"\n📦 *Overnight Positions:* ({len(overnight)})")
            for p in overnight:
                qty = int(p['netqty'])
                side = "🟢 LONG" if qty > 0 else "🔴 SHORT"
                mtm = float(p.get('rpnl', 0)) + float(p.get('urpnl', 0))
                msg.append(f"- {p['tsym']}: {side} {abs(qty)} (PnL: ₹{mtm:,.2f})")
        else:
            msg.append("\n✅ *No overnight positions found.*")

        msg.append("\n🚀 *Orbiter:* Ready for the session.")
        return "\n".join(msg)

    def generate_margin_status(self) -> str:
        """Concise margin update for post-trade and /margin command."""
        limits = self.broker.get_limits()
        if not limits:
            return "⚠️ *Margin Status:* Could not fetch data."
            
        msg = [
            f"💰 *Margin Update ({self.segment})* (v{self.version})",
            f"✅ *Available:* ₹{limits['available']:,.2f}",
            f"🔒 *Used:* ₹{limits['margin_used']:,.2f}",
            f"🏦 *Collateral:* ₹{limits['collateral_value']:,.2f}",
            f"💵 *Ledger:* ₹{limits['liquid_cash']:,.2f}"
        ]
        return "\n".join(msg)

    def generate_pnl_report(self, state) -> str:
        """Report total day summary including realized and unrealized PnL."""
        is_sim = state.config.get('SIMULATION', False)
        msg = [f"📊 <b>Session Summary ({self.segment})</b>{' [SIM]' if is_sim else ''}"]
        msg.append("-" * 25)
        
        active_pnl = 0.0
        active_lines = []
        for token, info in state.active_positions.items():
            try:
                # 🛡️ Safety: Fallback to entry price if LTP is None
                raw_ltp = self.broker.get_ltp(token)
                current_price = float(raw_ltp) if raw_ltp is not None else float(info.get('entry_price', 0))
                entry_price = float(info.get('entry_price', 0))
                strategy = info.get('strategy', '')
                
                # PnL Calculation
                pos_pnl = 0.0
                stock_move = ((current_price - entry_price) / (entry_price or 1) * 100.0)
                
                if 'FUTURE' in strategy:
                    profit_pct = stock_move
                    if 'SHORT' in strategy: profit_pct = -profit_pct
                    pos_pnl = (profit_pct / 100.0) * entry_price * info.get('lot_size', 1)
                else:
                    # Spread PnL
                    atm_ltp = self.broker.get_option_ltp_by_symbol(info.get('atm_symbol'))
                    hdg_ltp = self.broker.get_option_ltp_by_symbol(info.get('hedge_symbol'))
                    if atm_ltp is not None and hdg_ltp is not None:
                        current_net = float(atm_ltp) - float(hdg_ltp)
                        entry_net = float(info.get('entry_net_premium', 0))
                        pos_pnl = (entry_net - current_net) * info.get('lot_size', 1)
                
                active_pnl += pos_pnl
                emoji = "🟢" if pos_pnl >= 0 else "🔴"
                active_lines.append(f"{emoji} <code>{info.get('symbol', token)}</code>: <b>₹{pos_pnl:,.2f}</b> ({stock_move:+.2f}%)")
            except Exception as e:
                active_lines.append(f"⚠️ <code>{info.get('symbol', token)}</code>: Calculation Error")
                print(f"❌ PnL Calc Error for {token}: {e}")
        
        realized_pnl = getattr(state, 'realized_pnl', 0.0)
        total_pnl = active_pnl + realized_pnl
        trade_count = getattr(state, 'trade_count', 0)

        msg.append(f"🎯 <b>Total Day PnL:</b> <b>₹{total_pnl:,.2f}</b>")
        msg.append(f"✅ <b>Realized:</b>  ₹{realized_pnl:,.2f} ({trade_count} trades)")
        msg.append(f"📈 <b>Unrealized:</b> ₹{active_pnl:,.2f}")
        
        if active_lines:
            msg.append("\n💼 <b>Active Positions:</b>")
            msg.extend(active_lines)
        
        return "\n".join(msg)

    def generate_live_scan_report(self, state) -> str:
        """🔍 Real-time report of scans and active positions."""
        is_sim = state.config.get('SIMULATION', False)
        mode_tag = " [SIMULATION]" if is_sim else ""
        
        msg = [f"📊 <b>{self.segment} LIVE STATUS{mode_tag}</b>"]
        msg.append("-" * 25)

        # 1. Scan Stats
        msg.append(f"🔎 <b>Scanning:</b> {len(state.symbols)} symbols")
        
        # 2. Top 10 Scans by Score (Absolute)
        scores = []
        for token, results in state.filter_results_cache.items():
            total_score = sum(r.get('score', 0) for r in results.values() if isinstance(r, dict))
            scores.append((token, total_score))
        
        # Sort by absolute score descending
        top_10 = sorted(scores, key=lambda x: abs(x[1]), reverse=True)[:10]
        if top_10:
            msg.append("\n🔝 <b>Top 10 Scans (Score | Move | LTP):</b>")
            for token, score in top_10:
                data = state.client.SYMBOLDICT.get(token, {})
                
                # A. Robust Name Resolution (Check SYMBOLDICT first, then Master)
                token_id = token.split('|')[-1]
                exch = token.split('|')[0]
                
                # Try multiple sources for the symbol name
                raw_symbol = data.get('symbol') or data.get('tsym')
                if not raw_symbol or '|' in str(raw_symbol):
                    raw_symbol = self.broker.get_symbol(token_id, exchange=exch)
                
                import re
                clean_name = re.sub(r'\d{2}[A-Z]{3}\d{2}[FC]$', '', str(raw_symbol))
                if clean_name.endswith('-EQ'): clean_name = clean_name[:-3]
                clean_name = clean_name.strip()

                # B. Calculate Day Change % (with Zerodha Spot Parity)
                ltp_spot = 0.0
                baseline_price = 0.0
                
                try:
                    spot_token_id = self.broker.get_token(clean_name)
                    if spot_token_id and not spot_token_id.startswith('NFO') and not spot_token_id.startswith('MCX'):
                        quote = self.broker.api.get_quotes(exchange='NSE', token=spot_token_id)
                        if quote:
                            ltp_spot = float(quote.get('lp') or 0)
                            baseline_price = float(quote.get('c') or 0)
                except:
                    pass
                
                if ltp_spot == 0 or baseline_price == 0:
                    ltp_display = float(data.get('lp', 0))
                    raw_c = float(data.get('c') or data.get('pc') or 0)
                    raw_o = float(data.get('o') or 0)
                    baseline_price = raw_c if raw_c > 10.0 else raw_o
                else:
                    ltp_display = ltp_spot

                day_change = 0.0
                day_points = 0.0
                if baseline_price > 10.0: 
                    day_points = ltp_display - baseline_price
                    day_change = (day_points / baseline_price * 100.0)
                
                if abs(day_change) > 20.0:
                    day_change = 0.0
                    day_points = 0.0
                
                if day_change > 0:    change_emoji = "🟢 📈"
                elif day_change < 0:  change_emoji = "🔴 📉"
                else:                 change_emoji = "⚪ ➖"
                
                # C. Final "Color Coded" Formatting
                row = (
                    f"- <code>{clean_name:<10}</code>: <b>[{score:>+6.2f}]</b> | "
                    f"{change_emoji} <code>{day_points:>+7.2f}</code> (<code>{day_change:>+5.2f}%</code>) | "
                    f"<code>₹{ltp_display:,.2f}</code>"
                )
                msg.append(row)
        
        # 3. Active Positions & PnL
        if state.active_positions:
            pos_title = "🧪 <b>Active Simulations:</b>" if is_sim else "💼 <b>Active Positions:</b>"
            msg.append(f"\n{pos_title} ({len(state.active_positions)})")
            total_pnl = 0.0
            for token, info in state.active_positions.items():
                ltp = state.client.get_ltp(token) or info.get('entry_price', 0)
                strategy = info.get('strategy', '')
                
                # PnL Calculation
                pos_pnl = 0.0
                if 'FUTURE' in strategy:
                    profit_pct = ((float(ltp) - info['entry_price']) / (info['entry_price'] or 1) * 100.0)
                    if 'SHORT' in strategy: profit_pct = -profit_pct
                    pos_pnl = (profit_pct / 100.0) * info['entry_price'] * info.get('lot_size', 0)
                else:
                    # Spread PnL
                    atm_ltp = state.client.get_option_ltp_by_symbol(info.get('atm_symbol'))
                    hdg_ltp = state.client.get_option_ltp_by_symbol(info.get('hedge_symbol'))
                    if atm_ltp and hdg_ltp:
                        current_net = atm_ltp - hdg_ltp
                        entry_net = info.get('entry_net_premium', 0)
                        pos_pnl = (entry_net - current_net) * info.get('lot_size', 0)
                
                total_pnl += pos_pnl
                emoji = "🟢" if pos_pnl >= 0 else "🔴"
                msg.append(f"{emoji} <code>{info['symbol']}</code>: ₹{pos_pnl:,.2f}")
            
            msg.append("-" * 20)
            pnl_emoji = "💰" if total_pnl >= 0 else "💸"
            pnl_label = "<b>Total PnL (Simulated):</b>" if is_sim else "<b>Total PnL:</b>"
            msg.append(f"{pnl_emoji} {pnl_label} <b>₹{total_pnl:,.2f}</b>")
        else:
            msg.append("\n✅ <b>No active positions.</b>")

        return "\n".join(msg)

    def generate_post_session_report(self) -> str:
        """3:30 PM (NFO) / End of MCX Post-Market Debrief."""
        limits = self.broker.get_limits()
        orders = self.broker.get_order_history()
        positions = self.broker.get_positions()
        
        # Filter for executed orders only
        executed = [o for o in orders if o.get('status') == 'COMPLETE']
        
        msg = [f"🌇 <b>{self.segment} SESSION DEBRIEF</b>"]
        msg.append("-" * 25)
        
        # 1. Financial Performance
        total_pnl = sum(float(p.get('rpnl', 0)) + float(p.get('urpnl', 0)) for p in positions)
        
        # 2. Detailed Charges
        est_charges = TaxCalculator.estimate_charges(len(executed), total_pnl, self.segment)
        net_pnl = total_pnl - est_charges
        
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        msg.append(f"{pnl_emoji} <b>Gross PnL:</b> ₹{total_pnl:,.2f}")
        msg.append(f"💸 <b>Est. Charges:</b> ₹{est_charges:,.2f}")
        msg.append(f"📈 <b>Net PnL (Est):</b> ₹{net_pnl:,.2f}")
        
        # 3. Portfolio Concentration Risk
        if positions:
            msg.append("\n📊 <b>Portfolio Concentration:</b>")
            max_pos = None
            max_val = -1.0
            for p in positions:
                pnl = abs(float(p.get('rpnl', 0)) + float(p.get('urpnl', 0)))
                if pnl > max_val:
                    max_val = pnl
                    max_pos = p['tsym']
            if max_pos:
                msg.append(f"🔥 <b>Top Mover:</b> {max_pos} (₹{max_val:,.2f})")
        
        # 4. Execution Activity
        msg.append(f"\n🎯 <b>Activity:</b> {len(executed)} Orders Executed")
        
        # 5. Final Margin & T+1 Estimate
        if limits:
            msg.append(f"💰 <b>Final Margin:</b> ₹{limits['available']:,.2f}")
            # T+1 Estimate: If NFO, profits are usually available next day.
            t1_margin = limits['available'] + net_pnl
            msg.append(f"📅 <b>T+1 Est. Margin:</b> ₹{t1_margin:,.2f}")

        msg.append("\n💤 <b>Orbiter:</b> Session closed.")
        return "\n".join(msg)
