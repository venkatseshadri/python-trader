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
    
    def __init__(self, broker_client, segment_name: str):
        self.broker = broker_client
        self.segment = segment_name.upper()
        self.logger = logging.getLogger(f"SummaryManager_{segment_name}")

    def generate_pre_session_report(self) -> str:
        """9:30 AM (NFO) / 5:30 PM (MCX) Pre-Market Check."""
        limits = self.broker.get_limits()
        positions = self.broker.get_positions()
        
        msg = [f"🌅 *{self.segment} SESSION PREP* ({datetime.now().strftime('%H:%M')})"]
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
            f"💰 *Margin Update ({self.segment})*",
            f"✅ *Available:* ₹{limits['available']:,.2f}",
            f"🔒 *Used:* ₹{limits['margin_used']:,.2f}",
            f"🏦 *Collateral:* ₹{limits['collateral_value']:,.2f}",
            f"💵 *Ledger:* ₹{limits['liquid_cash']:,.2f}"
        ]
        return "\n".join(msg)

    def generate_live_scan_report(self, state) -> str:
        """🔍 Real-time report of scans and active positions."""
        msg = [f"📊 *{self.segment} LIVE STATUS*"]
        msg.append("-" * 25)

        # 1. Scan Stats
        msg.append(f"🔎 *Scanning:* {len(state.symbols)} symbols")
        
        # 2. Top 10 Scans by Score (Absolute)
        scores = []
        for token, results in state.filter_results_cache.items():
            total_score = sum(r.get('score', 0) for r in results.values() if isinstance(r, dict))
            scores.append((token, total_score))
        
        # Sort by absolute score descending
        top_10 = sorted(scores, key=lambda x: abs(x[1]), reverse=True)[:10]
        if top_10:
            msg.append("\n🔝 *Top 10 Scans (Score | Day %):*")
            for token, score in top_10:
                data = state.client.SYMBOLDICT.get(token, {})
                full_symbol = data.get('symbol', token)
                
                # A. Clean Stock Name (Remove contract dates/suffixes)
                import re
                clean_name = re.sub(r'\d{2}[A-Z]{3}\d{2}[FC]$', '', full_symbol)
                if clean_name.endswith('-EQ'): clean_name = clean_name[:-3]
                clean_name = clean_name.strip()

                # B. Calculate Day Change % (with Sanity Filter & API Fallback)
                ltp = float(data.get('lp', 0))
                
                # Industry Standard: Day % is calculated from Previous Close ('c' or 'pc')
                raw_o = float(data.get('o') or 0)
                raw_c = float(data.get('c') or data.get('pc') or 0)
                
                # Prefer Close, fallback to Open
                baseline_price = raw_c if raw_c > 10.0 else raw_o
                
                # 🔄 API Fallback: If live feed is missing baseline, fetch a quick quote
                if baseline_price < 10.0:
                    try:
                        exch = token.split('|')[0]
                        tok_id = token.split('|')[-1]
                        quote = state.client.api.get_quotes(exchange=exch, token=tok_id)
                        if quote:
                            # Prefer 'c' (Close) from quote
                            baseline_price = float(quote.get('c') or quote.get('o') or 0)
                    except:
                        pass

                day_change = 0.0
                if baseline_price > 10.0: 
                    day_change = ((ltp - baseline_price) / baseline_price * 100.0)
                
                # Final Sanity: If change is physically impossible (>20% for NFO), reset to 0
                if abs(day_change) > 20.0:
                    day_change = 0.0
                
                if day_change > 0:    change_emoji = "📈"
                elif day_change < 0:  change_emoji = "📉"
                else:                 change_emoji = "➖"
                
                msg.append(f"- `{clean_name:<10}`: *{score:>+6.2f}* | {change_emoji}{day_change:>+5.2f}%")
        
        # 3. Active Positions & PnL
        if state.active_positions:
            msg.append(f"\n💼 *Active Positions:* ({len(state.active_positions)})")
            total_pnl = 0.0
            for token, info in state.active_positions.items():
                ltp = state.client.get_ltp(token) or info.get('entry_price', 0)
                strategy = info.get('strategy', '')
                
                # PnL Calculation
                pos_pnl = 0.0
                if 'FUTURE' in strategy:
                    profit_pct = ((float(ltp) - info['entry_price']) / info['entry_price'] * 100.0)
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
                msg.append(f"{emoji} `{info['symbol']}`: ₹{pos_pnl:,.2f}")
            
            msg.append("-" * 20)
            pnl_emoji = "💰" if total_pnl >= 0 else "💸"
            msg.append(f"{pnl_emoji} *Total PnL:* ₹{total_pnl:,.2f}")
        else:
            msg.append("\n✅ *No active positions.*")

        return "\n".join(msg)

    def generate_post_session_report(self) -> str:
        """3:30 PM (NFO) / End of MCX Post-Market Debrief."""
        limits = self.broker.get_limits()
        orders = self.broker.get_order_history()
        positions = self.broker.get_positions()
        
        # Filter for executed orders only
        executed = [o for o in orders if o.get('status') == 'COMPLETE']
        
        msg = [f"🌇 *{self.segment} SESSION DEBRIEF*"]
        msg.append("-" * 25)
        
        # 1. Financial Performance
        total_pnl = sum(float(p.get('rpnl', 0)) + float(p.get('urpnl', 0)) for p in positions)
        
        # 2. Detailed Charges
        est_charges = TaxCalculator.estimate_charges(len(executed), total_pnl, self.segment)
        net_pnl = total_pnl - est_charges
        
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        msg.append(f"{pnl_emoji} *Gross PnL:* ₹{total_pnl:,.2f}")
        msg.append(f"💸 *Est. Charges:* ₹{est_charges:,.2f}")
        msg.append(f"📈 *Net PnL (Est):* ₹{net_pnl:,.2f}")
        
        # 3. Portfolio Concentration Risk
        if positions:
            msg.append("\n📊 *Portfolio Concentration:*")
            max_pos = None
            max_val = -1.0
            for p in positions:
                pnl = abs(float(p.get('rpnl', 0)) + float(p.get('urpnl', 0)))
                if pnl > max_val:
                    max_val = pnl
                    max_pos = p['tsym']
            if max_pos:
                msg.append(f"🔥 *Top Mover:* {max_pos} (₹{max_val:,.2f})")
        
        # 4. Execution Activity
        msg.append(f"\n🎯 *Activity:* {len(executed)} Orders Executed")
        
        # 5. Final Margin & T+1 Estimate
        if limits:
            msg.append(f"💰 *Final Margin:* ₹{limits['available']:,.2f}")
            # T+1 Estimate: If NFO, profits are usually available next day.
            t1_margin = limits['available'] + net_pnl
            msg.append(f"📅 *T+1 Est. Margin:* ₹{t1_margin:,.2f}")

        msg.append("\n💤 *Orbiter:* Session closed.")
        return "\n".join(msg)
