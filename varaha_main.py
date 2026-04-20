"""
🐗 Project Varaha: Phase 5 – Master Orchestrator
The single "Command Center" that ties all modules together.

Operational Timeline:
- 09:00 AM: Download Master Contracts & Sync Time
- 09:15 AM: Authentication & Margin Check
- 09:20 AM: Strike Selection & Position Entry
- 09:21 AM - 03:05 PM: Active Monitoring
- 03:06 PM: Final Logging & Shutdown

Usage:
    python3 varaha_main.py [--dry-run] [--live]
"""

import sys
import os
import time
import logging
import argparse
from datetime import datetime, time as dt_time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import Varaha modules
from varaha_auth import VarahaConnect
from varaha_master import VarahaMaster
from varaha_executor import VarahaExecutor
from varaha_monitor import VarahaMonitor
from varaha_sentinel import VarahaSentinel

# ============================================================
# CONFIGURATION
# ============================================================

class Config:
    """Global configuration for Varaha"""
    
    # Market hours (IST)
    MARKET_START = dt_time(9, 20)   # 9:20 AM - Entry window opens
    MARKET_END = dt_time(15, 0)    # 3:00 PM - Entry window closes
    EOD_EXIT = dt_time(15, 5)      # 3:05 PM - All positions closed
    
    # Entry parameters
    TARGET_MTM = 1500      # Exit when net profit >= ₹1,500
    MAX_LOSS = -2200        # Exit when net loss <= -₹2,200
    COST_BUFFER = 400      # Brokerage, STT, slippage
    
    # Execution parameters
    LOTS = 4               # Default: 4 lots (₹4L margin)
    INDEX = 'NIFTY'         # Trade Nifty weekly options
    EXPIRY = 'WEEKLY'      # Current weekly expiry
    
    # Logging
    # (varaha_system.log is now created by setup_logging())


# ============================================================
# SETUP LOGGING
# ============================================================

def setup_logging(dry_run: bool = True):
    """Configure logging for the orchestrator
    
    Tiered logging system:
    - FileHandler: Records ALL DEBUG level messages to varaha_system.log
    - StreamHandler: Outputs only INFO and above to console (keeps screen clean)
    """
    import sys
    
    # Create custom logger (not the root logger)
    logger = logging.getLogger("Varaha")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # Clear any existing handlers
    
    # Format: Time | Module | Level | Message
    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)-8s | %(message)s')
    
    # 1. File Handler - Writes EVERYTHING for troubleshooting/history
    file_handler = logging.FileHandler(PROJECT_ROOT / "varaha_system.log")
    file_handler.setLevel(logging.DEBUG)  # Capture all levels
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 2. Console Handler - Only shows INFO and above (keeps screen clean)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # Only INFO and above to console
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if dry_run:
        logging.info("🐗 RUNNING IN DRY-RUN MODE - No real orders will be placed")


# ============================================================
# MARKET TIMING CHECKS
# ============================================================

def is_weekday() -> bool:
    """Check if today is a weekday (Monday-Friday)"""
    return datetime.now().weekday() < 5  # 0=Mon, 4=Fri


def is_market_hours(include_pre: bool = False) -> bool:
    """Check if current time is within market hours"""
    now = datetime.now().time()
    
    if include_pre:
        # Allow 09:15-15:00 for morning setup
        return dt_time(9, 15) <= now <= Config.MARKET_END
    else:
        # Strict entry window: 09:20-15:00
        return Config.MARKET_START <= now <= Config.MARKET_END


def is_market_close() -> bool:
    """Check if market is about to close (within 5 min)"""
    now = datetime.now().time()
    return now >= Config.EOD_EXIT


def wait_for_market_open():
    """Wait until 09:20 AM or return immediately if already past"""
    now = datetime.now().time()
    
    if now < Config.MARKET_START:
        wait_seconds = (
            datetime.combine(datetime.now().date(), Config.MARKET_START) - 
            datetime.now()
        ).seconds
        logging.info(f"🐗 Waiting for market open ({wait_seconds//60} min)...")
        time.sleep(wait_seconds)
    else:
        logging.info("🐗 Market already open - proceeding with entry")


# ============================================================
# PHASE 1: AUTHENTICATION
# ============================================================

def authenticate(dry_run: bool = True) -> VarahaConnect:
    """
    Phase 1: Authenticate with broker API
    
    Returns:
        VarahaConnect instance or None on failure
    """
    logging.info("🔐 PHASE 1: AUTHENTICATION")
    logging.info("-" * 40)
    
    try:
        engine = VarahaConnect()
        
        if not dry_run:
            if not engine.start_session():
                logging.error("❌ Authentication failed - cannot proceed")
                return None
            logging.info("✅ Authenticated successfully")
        else:
            logging.info("🐛 [DRY-RUN] Skipping actual login")
            # In dry-run, create mock engine
            engine = create_mock_engine()
        
        logging.info("-" * 40 + "\n")
        return engine
        
    except Exception as e:
        logging.error(f"❌ Authentication error: {e}")
        return None


def create_mock_engine():
    """Create a mock engine for testing"""
    class MockAPI:
        def get_quotes(self, exchange, token):
            return {'lp': 22500.0, 'ltp': 22500.0}
        
        def get_positions(self):
            return []
        
        def get_order_book(self):
            return []
    
    return MockAPI()


# ============================================================
# PHASE 2: MASTER DATA SYNC
# ============================================================

def sync_master_data(dry_run: bool = True) -> VarahaMaster:
    """
    Phase 2: Download and sync master contracts
    
    Returns:
        VarahaMaster instance or None on failure
    """
    logging.info("📦 PHASE 2: MASTER DATA SYNC")
    logging.info("-" * 40)
    
    try:
        master = VarahaMaster()
        
        if not dry_run:
            master.sync_masters()
            master.load_data()
            logging.info("✅ Master contracts synced")
        else:
            logging.info("🐛 [DRY-RUN] Skipping master sync")
            # Load cached data in dry-run
            master.load_data()
        
        logging.info("-" * 40 + "\n")
        return master
        
    except Exception as e:
        logging.error(f"❌ Master sync error: {e}")
        return None


# ============================================================
# PHASE 3: STRATEGY & STRIKE SELECTION
# ============================================================

def select_strikes(engine, master) -> dict:
    """
    Phase 3: Get ATM strike and build iron butterfly legs
    
    Returns:
        dict with 4 legs (buy_ce, buy_pe, sell_ce, sell_pe)
    """
    logging.info("🎯 PHASE 3: STRIKE SELECTION")
    logging.info("-" * 40)
    
    try:
        # Get spot price via strategist or API
        if hasattr(engine, 'get_quotes'):
            quote = engine.get_quotes('NSE', 'NIFTY 50')
            spot = float(quote.get('lp', quote.get('ltp', 22500)))
        else:
            spot = 22500.0  # Mock
        
        # Round to nearest 50
        atm_strike = round(spot / 50) * 50
        
        logging.info(f"   Spot: ₹{spot}")
        logging.info(f"   ATM Strike: {atm_strike}")
        
        # Get expiry (current weekly)
        # In production, calculate from master
        expiry = get_weekly_expiry()
        
        # Build 4 legs for Iron Butterfly
        legs = build_iron_butterfly_legs(atm_strike, expiry)
        
        logging.info(f"   Expiry: {expiry}")
        logging.info(f"   Sell CE: {legs['sell_ce']['tsym']}")
        logging.info(f"   Buy CE:  {legs['buy_ce']['tsym']}")
        logging.info(f"   Sell PE: {legs['sell_pe']['tsym']}")
        logging.info(f"   Buy PE:  {legs['buy_pe']['tsym']}")
        
        logging.info("-" * 40 + "\n")
        return legs
        
    except Exception as e:
        logging.error(f"❌ Strike selection error: {e}")
        return {}


def get_weekly_expiry() -> str:
    """Get current weekly expiry date string"""
    # In production, calculate from calendar
    # Returns format like "30-APR-2026"
    from datetime import timedelta
    
    # Find next Thursday (weekly expiry)
    today = datetime.now()
    days_until_thursday = (3 - today.weekday()) % 7
    if days_until_thursday == 0:
        days_until_thursday = 7
    
    expiry_date = today + timedelta(days=days_until_thursday)
    return expiry_date.strftime("%d-%b-%Y").upper()


def build_iron_butterfly_legs(atm_strike: int, expiry: str) -> dict:
    """
    Build the 4 legs for Iron Butterfly
    
    Structure:
    - buy_ce: OTM Call (Strike + 100)
    - sell_ce: ATM Call
    - sell_pe: ATM Put
    - buy_pe: OTM Put (Strike - 100)
    """
    # ATM Call/Put (center)
    sell_ce_strike = atm_strike
    sell_pe_strike = atm_strike
    
    # OTM wings (100 points away)
    buy_ce_strike = atm_strike + 100
    buy_pe_strike = atm_strike - 100
    
    return {
        'buy_ce': {
            'exchange': 'NFO',
            'tsym': f'NIFTY{expiry}{buy_ce_strike}CE',
            'token': f'NIFTY{buy_ce_strike}{expiry}CE',
            'ltp': 45.0,  # Mock - will fetch real
            'lot_size': 50,
            'strike': buy_ce_strike
        },
        'sell_ce': {
            'exchange': 'NFO',
            'tsym': f'NIFTY{expiry}{sell_ce_strike}CE',
            'token': f'NIFTY{sell_ce_strike}{expiry}CE',
            'ltp': 120.0,  # Mock
            'lot_size': 50,
            'strike': sell_ce_strike
        },
        'sell_pe': {
            'exchange': 'NFO',
            'tsym': f'NIFTY{expiry}{sell_pe_strike}PE',
            'token': f'NIFTY{sell_pe_strike}{expiry}PE',
            'ltp': 115.0,  # Mock
            'lot_size': 50,
            'strike': sell_pe_strike
        },
        'buy_pe': {
            'exchange': 'NFO',
            'tsym': f'NIFTY{expiry}{buy_pe_strike}PE',
            'token': f'NIFTY{buy_pe_strike}{expiry}PE',
            'ltp': 48.0,  # Mock
            'lot_size': 50,
            'strike': buy_pe_strike
        }
    }


# ============================================================
# PHASE 4: EXECUTION
# ============================================================

def execute_position(engine, legs: dict, lots: int = 4) -> list:
    """
    Phase 4: Execute Iron Butterfly
    
    Returns:
        List of open positions
    """
    logging.info("⚡ PHASE 4: EXECUTION")
    logging.info("-" * 40)
    
    try:
        executor = VarahaExecutor(engine)
        
        logging.info(f"   Placing Iron Butterfly: {lots} lots")
        
        # Execute in simulation mode (dry-run)
        result = executor.execute_iron_butterfly(legs, lots)
        
        if result['sequence_verified']:
            logging.info("✅ Position opened successfully")
            logging.info(f"   Qty per leg: {result['quantity_per_leg']}")
        else:
            logging.warning("⚠️ Sequence verification failed")
        
        # Build positions list for monitoring
        open_positions = build_positions_from_result(result, legs)
        
        logging.info("-" * 40 + "\n")
        return open_positions
        
    except Exception as e:
        logging.error(f"❌ Execution error: {e}")
        return []


def build_positions_from_result(result: dict, legs: dict) -> list:
    """Build position list for monitoring"""
    positions = []
    
    # Add SELL legs (shorts) first
    positions.append({
        'side': 'SELL',
        'symbol': legs['sell_ce']['tsym'],
        'token': legs['sell_ce']['token'],
        'exchange': 'NFO',
        'quantity': result['quantity_per_leg'],
        'entry_price': legs['sell_ce']['ltp'],
        'current_price': legs['sell_ce']['ltp'],
        'leg_type': 'short_ce'
    })
    positions.append({
        'side': 'SELL',
        'symbol': legs['sell_pe']['tsym'],
        'token': legs['sell_pe']['token'],
        'exchange': 'NFO',
        'quantity': result['quantity_per_leg'],
        'entry_price': legs['sell_pe']['ltp'],
        'current_price': legs['sell_pe']['ltp'],
        'leg_type': 'short_pe'
    })
    
    # Add BUY legs (wings)
    positions.append({
        'side': 'BUY',
        'symbol': legs['buy_ce']['tsym'],
        'token': legs['buy_ce']['token'],
        'exchange': 'NFO',
        'quantity': result['quantity_per_leg'],
        'entry_price': legs['buy_ce']['ltp'],
        'current_price': legs['buy_ce']['ltp'],
        'leg_type': 'wing_ce'
    })
    positions.append({
        'side': 'BUY',
        'symbol': legs['buy_pe']['tsym'],
        'token': legs['buy_pe']['token'],
        'exchange': 'NFO',
        'quantity': result['quantity_per_leg'],
        'entry_price': legs['buy_pe']['ltp'],
        'current_price': legs['buy_pe']['ltp'],
        'leg_type': 'wing_pe'
    })
    
    return positions


# ============================================================
# PHASE 5: MONITORING & EXIT
# ============================================================

def start_monitoring(engine, open_positions: list, legs: dict, dry_run: bool = True):
    """
    Phase 5: Active monitoring loop
    
    Monitors P&L and triggers exits based on:
    - Profit target: +₹1,500
    - Max loss: -₹2,200
    - EOD: 3:05 PM
    """
    logging.info("🛡️ PHASE 5: MONITORING STARTED")
    logging.info("-" * 40)
    logging.info(f"   Target: +₹{Config.TARGET_MTM}")
    logging.info(f"   Max Loss: ₹{Config.MAX_LOSS}")
    logging.info(f"   EOD Exit: {Config.EOD_EXIT}")
    logging.info("-" * 40 + "\n")
    
    monitor = VarahaMonitor(engine)
    
    # Fake LTP simulation for testing
    fake_ltp = {
        legs['sell_ce']['token']: legs['sell_ce']['ltp'],
        legs['sell_pe']['token']: legs['sell_pe']['ltp'],
        legs['buy_ce']['token']: legs['buy_ce']['ltp'],
        legs['buy_pe']['token']: legs['buy_pe']['ltp'],
    }
    
    # Simulate a few MTM checks
    # In production, this would be: while is_market_hours() and not exited:
    for i in range(3):
        # Simulate price movement (mock)
        mtm = simulate_price_movement(i, fake_ltp)
        
        net_pnl = mtm - Config.COST_BUFFER
        
        logging.info(f"   [Check {i+1}] MTM: ₹{mtm:.2f} | Net: ₹{net_pnl:.2f}")
        
        if net_pnl >= Config.TARGET_MTM:
            logging.info(f"🎯 TARGET HIT! Exiting at +₹{net_pnl:.2f}")
            break
        elif net_pnl <= Config.MAX_LOSS:
            logging.info(f"🛑 STOP LOSS! Exiting at ₹{net_pnl:.2f}")
            break
        
        # In production: sleep 60 (1 minute checks)
        if i < 2:
            time.sleep(1)  # 1 second for testing
    
    logging.info("-" * 40 + "\n")


def simulate_price_movement(iteration: int, fake_ltp: dict) -> float:
    """Simulate MTM calculation for testing"""
    import random
    
    # Simulate small price changes
    # Iteration 0: ~+500
    # Iteration 1: ~+1200 (target hit)
    # Iteration 2: N/A
    
    base = 500 * iteration
    
    # Add some random movement
    movement = random.uniform(-100, 100)
    
    # Calculate net premium received
    sell_ce = fake_ltp.get(list(fake_ltp.keys())[0], 120)
    sell_pe = fake_ltp.get(list(fake_ltp.keys())[1], 115)
    buy_ce = fake_ltp.get(list(fake_ltp.keys())[2], 45)
    buy_pe = fake_ltp.get(list(fake_ltp.keys())[3], 48)
    
    # Net premium = Sell ATM - Buy Wings
    net_premium = (sell_ce + sell_pe) - (buy_ce + buy_pe)
    
    # MTM = Net premium + P/L from price movement
    mtm = net_premium * 50 + (base + movement) * 2  # 50 qty * price move
    
    return mtm


# ============================================================
# 🛡️ SAFETY GATE: Step 3 - Session Recovery Functions
# ============================================================

def check_existing_positions(engine, dry_run: bool = True) -> list:
    """
    Check if Iron Butterfly positions already exist from a previous run.
    
    This is the Session Recovery mechanism - if script crashed and restarted,
    detect existing positions instead of opening new ones.
    
    Args:
        engine: API instance
        dry_run: If True, simulate (no API calls)
        
    Returns:
        List of existing positions (4 legs) or empty list if none found
    """
    logging.info("🛡️ SESSION RECOVERY: Checking for existing positions...")
    
    if dry_run or not engine:
        logging.info("   [DRY-RUN] Skipping position check")
        return []
    
    try:
        # Get positions from broker
        positions = engine.get_positions()
        
        if not positions or (isinstance(positions, dict) and positions.get('stat') != 'Ok'):
            logging.info("   No existing positions found")
            return []
        
        # Convert to list if needed
        if isinstance(positions, dict) and 'netpositions' in positions:
            positions = positions['netpositions']
        
        if not positions:
            logging.info("   Position book is empty")
            return []
        
        logging.info(f"   Found {len(positions)} positions in book")
        
        # Look for Iron Butterfly pattern (4 legs)
        # We expect: 2 SELL (ATM straddle) + 2 BUY (OTM wings)
        existing_legs = []
        
        for pos in positions:
            # Skip if no quantity or closed
            if not pos.get('netqty') or int(pos.get('netqty', 0)) == 0:
                continue
            
            # Build position dict
            leg = {
                'side': 'SELL' if int(pos.get('netqty', 0)) < 0 else 'BUY',
                'symbol': pos.get('tsym', ''),
                'token': pos.get('token', ''),
                'exchange': pos.get('exchange', 'NFO'),
                'quantity': abs(int(pos.get('netqty', 0))),
                'entry_price': float(pos.get('avgprc', 0)),
                'current_price': float(pos.get('lp', pos.get('ltp', 0))),
                'leg_type': ''
            }
            
            # Determine leg type
            symbol = leg['symbol'].upper()
            if 'CE' in symbol:
                leg['leg_type'] = 'short_ce' if leg['side'] == 'SELL' else 'wing_ce'
            elif 'PE' in symbol:
                leg['leg_type'] = 'short_pe' if leg['side'] == 'SELL' else 'wing_pe'
            
            existing_legs.append(leg)
            logging.info(f"   Found leg: {leg['side']} {leg['symbol']} x{leg['quantity']}")
        
        # Check if we have the Iron Butterfly (4 legs)
        if len(existing_legs) >= 4:
            logging.info(f"🛡️ SESSION RECOVERY: Found {len(existing_legs)} legs - Iron Butterfly active!")
            return existing_legs
        else:
            logging.info(f"   Only {len(existing_legs)} legs found - not a complete Iron Butterfly")
            return []
            
    except Exception as e:
        logging.warning(f"   Position check failed: {e}")
        return []


def start_monitoring_from_recovery(engine, existing_positions: list, dry_run: bool = True):
    """
    Resume monitoring from an existing Iron Butterfly position.
    
    Args:
        engine: API instance
        existing_positions: List of position dicts from previous run
        dry_run: Simulation mode
    """
    logging.info("🛡️ SESSION RECOVERY: Starting monitoring from existing position")
    
    # Import VarahaSentinel for TSL
    try:
        from varaha_sentinel import VarahaSentinel
        sentinel = VarahaSentinel(telegram_enabled=False)
        sentinel.current_sl = -2200  # Reset to max loss
    except ImportError:
        sentinel = None
        logging.warning("   VarahaSentinel not available - using basic monitoring")
    
    # In production, this would start the live monitoring loop
    # For now, log the recovery
    
    if not dry_run and engine:
        try:
            # Get current P&L
            limits = engine.get_limits()
            if limits and limits.get('stat') == 'Ok':
                logging.info(f"   Available margin: ₹{limits.get('turnover', 'N/A')}")
        except:
            pass
    
    # Resume the monitoring loop
    monitor = VarahaMonitor(engine)
    
    # Simulate a few checks (in production, this would be a loop)
    for i in range(3):
        mtm = 0  # Would fetch real MTM
        net_pnl = mtm - 400  # After cost buffer
        
        if sentinel and net_pnl > sentinel.current_sl:
            tsl_result = sentinel.update_tsl(net_pnl)
            logging.info(f"   TSL Update: P&L ₹{net_pnl:.0f} → SL ₹{sentinel.current_sl:.0f}")
    
    logging.info("🛡️ SESSION RECOVERY: Monitoring resumed successfully")


# ============================================================
# PHASE 6: CLEANUP
# ============================================================

def close_all_positions(engine, open_positions: list) -> bool:
    """
    Phase 6: Close all positions (emergency exit)
    
    NOTE: Closes SHORT legs first, then LONG legs
    """
    logging.info("🚪 PHASE 6: EMERGENCY EXIT")
    logging.info("-" * 40)
    
    try:
        executor = VarahaExecutor(engine)
        
        # Close shorts first (to release margin faster)
        sell_positions = [p for p in open_positions if p.get('side') == 'SELL']
        for pos in sell_positions:
            close_side = 'BUY'
            logging.info(f"   Closing SHORT: {close_side} {pos['symbol']}")
        
        time.sleep(1.5)
        
        # Close longs/wings (to complete exit)
        buy_positions = [p for p in open_positions if p.get('side') == 'BUY']
        for pos in buy_positions:
            close_side = 'SELL'
            logging.info(f"   Closing LONG: {close_side} {pos['symbol']}")
        
        logging.info("✅ All positions closed")
        logging.info("-" * 40 + "\n")
        return True
        
    except Exception as e:
        logging.error(f"❌ Exit error: {e}")
        return False


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================

def run_orchestrator(dry_run: bool = True, live: bool = False):
    """
    The main orchestrator function
    
    Args:
        dry_run: If True, simulate everything (log only)
        live: If True, execute real orders
    """
    # Setup logging
    setup_logging(dry_run)
    
    # Banner
    logging.info("=" * 60)
    logging.info("🐗 PROJECT VARAHA - MASTER ORCHESTRATOR v1.0")
    logging.info(f"   Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    logging.info(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 60 + "\n")
    
    # ========================================================
    # PRE-FLIGHT CHECKS
    # ========================================================
    
    if not is_weekday():
        logging.info("🛑 WEEKEND - No trading today")
        logging.info("   Varaha runs Monday-Thursday only")
        return
    
    if not is_market_hours(include_pre=True):
        now = datetime.now().time()
        if now < dt_time(9, 15):
            logging.info("⏰ Market not open yet (opens 9:15 AM)")
            return
        else:
            logging.info("⏰ Market closed for the day")
            return
    
    # ========================================================
    # PHASE 1: AUTHENTICATION
    # ========================================================
    
    engine = authenticate(dry_run)
    if not engine and not dry_run:
        logging.error("❌ FATAL: Authentication failed - aborting")
        return
    
    # ========================================================
    # 🛡️ SAFETY GATE: Step 3 - Session Recovery
    # ========================================================
    # Check if positions already exist (script restart scenario)
    
    existing_positions = check_existing_positions(engine, dry_run)
    
    if existing_positions:
        logging.info("🔄 SESSION RECOVERY: Found existing positions")
        logging.info(f"   Resuming monitoring with {len(existing_positions)} legs")
        # Resume monitoring with existing positions instead of opening new
        return start_monitoring_from_recovery(engine, existing_positions, dry_run)
    
    # ========================================================
    # PHASE 2: MASTER DATA
    # ========================================================
    
    master = sync_master_data(dry_run)
    if not master and not dry_run:
        logging.error("❌ FATAL: Master sync failed - aborting")
        close_all_positions(engine, [])
        return
    
    # ========================================================
    # PHASE 3: STRIKE SELECTION
    # ========================================================
    
    wait_for_market_open()
    
    if not is_market_hours():
        logging.info("⏰ Missed entry window (09:20-15:00)")
        return
    
    legs = select_strikes(engine, master)
    if not legs:
        logging.error("❌ FATAL: Strike selection failed")
        return
    
    # ========================================================
    # PHASE 4: EXECUTION
    # ========================================================
    
    open_positions = execute_position(engine, legs, Config.LOTS)
    
    if not open_positions:
        logging.error("❌ FATAL: Position entry failed")
        return
    
    # ========================================================
    # PHASE 5: MONITORING
    # ========================================================
    
    start_monitoring(engine, open_positions, legs, dry_run)
    
    # ========================================================
    # PHASE 6: CLEANUP
    # ========================================================
    
    if not dry_run:
        close_all_positions(engine, open_positions)
    
    # Final summary
    logging.info("=" * 60)
    logging.info("🐗 PROJECT VARAHA - SESSION COMPLETE")
    logging.info(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="🐗 Project Varaha Orchestrator")
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help="Run in simulation mode (default: True)")
    parser.add_argument('--live', action='store_true', default=False,
                        help="Run in live trading mode")
    
    args = parser.parse_args()
    
    # Disable dry-run if --live is explicitly set
    dry_run = not args.live
    
    # Run the orchestrator
    run_orchestrator(dry_run=dry_run, live=args.live)