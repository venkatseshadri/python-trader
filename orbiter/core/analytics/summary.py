import logging
from typing import Dict, List, Any
from datetime import datetime

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
            msg.append(f"💰 *Available Margin:* ₹{limits['available']:,.2f}")
            msg.append(f"🔒 *Margin Used:* ₹{limits['margin_used']:,.2f}")
            msg.append(f"💳 *Cash Balance:* ₹{limits['cash']:,.2f}")
        else:
            msg.append("⚠️ *Limits:* Could not fetch margin status.")

        overnight = [p for p in positions if int(p.get('netqty', 0)) != 0]
        if overnight:
            msg.append(f"
📦 *Overnight Positions:* ({len(overnight)})")
            for p in overnight:
                qty = int(p['netqty'])
                side = "🟢 LONG" if qty > 0 else "🔴 SHORT"
                mtm = float(p.get('rpnl', 0)) + float(p.get('urpnl', 0))
                msg.append(f"- {p['tsym']}: {side} {abs(qty)} (PnL: ₹{mtm:,.2f})")
        else:
            msg.append("
✅ *No overnight positions found.*")

        msg.append("
🚀 *Orbiter:* Ready for the session.")
        return "
".join(msg)

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
        
        # 2. Estimated Charges (Proxy: ₹25 per executed order for brokerage/taxes)
        est_charges = len(executed) * 25.0
        net_pnl = total_pnl - est_charges
        
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        msg.append(f"{pnl_emoji} *Gross PnL:* ₹{total_pnl:,.2f}")
        msg.append(f"💸 *Est. Charges:* ₹{est_charges:,.2f}")
        msg.append(f"📈 *Net PnL (Est):* ₹{net_pnl:,.2f}")
        
        # 3. Execution Activity
        msg.append(f"
🎯 *Activity:* {len(executed)} Orders Executed")
        
        # 4. Final Margin Status
        if limits:
            msg.append(f"💰 *Final Margin:* ₹{limits['available']:,.2f}")
        
        # 5. T+1 Estimate (Crude: Add Net PnL to Cash)
        if limits:
            t1_margin = limits['available'] + net_pnl
            msg.append(f"📅 *T+1 Est. Margin:* ₹{t1_margin:,.2f}")

        msg.append("
💤 *Orbiter:* Session closed.")
        return "
".join(msg)
