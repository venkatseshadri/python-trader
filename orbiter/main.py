#!/usr/bin/env python3
"""
🚀 ORBITER v3.6.3-20260218-0c972a7 - Unified Segment Multi-Market Trader
"""

import time
import sys
import os
import argparse
import pytz
import logging
import traceback
from datetime import datetime, time as dt_time

# Path setup
base_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(base_dir)
sys.path.insert(0, base_dir)
sys.path.append(os.path.join(base_dir, '..', 'ShoonyaApi-py'))

from core.broker import BrokerClient
from core.engine.state import OrbiterState
from core.engine.evaluator import Evaluator
from core.engine.executor import Executor
from core.engine.syncer import Syncer
from core.analytics.summary import SummaryManager
from utils.cleanup_sheets import cleanup_google_sheets
from utils.ai_handler import OrbiterAI
import filters
import config.config as global_config
from utils.telegram_notifier import send_telegram_msg, TelegramCommandListener

# Version Loading Logic
def load_version():
    try:
        # 1. Read Base Version (e.g., 3.9.6)
        base_v = "3.9.6"
        v_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'version.txt')
        if os.path.exists(v_path):
            with open(v_path, 'r') as f:
                base_v = f.read().strip().split('-')[0]
        
        # 2. Get Live Git Hash and Date
        import subprocess
        git_hash = subprocess.check_output(['git', 'rev-parse', '--short=7', 'HEAD'], 
                                         stderr=subprocess.DEVNULL).decode('ascii').strip()
        date_str = datetime.now().strftime("%Y%m%d")
        
        # 3. Combine to original scheme: 3.9.6-20260219-a1b2c3d
        return f"{base_v}-{date_str}-{git_hash}"
    except Exception:
        return "3.9.6-STABLE"

VERSION = load_version()

class LoggerWriter:
    def __init__(self, level, raw=False):
        self.level = level
        self.raw = raw
    def write(self, message):
        if message and message.strip():
            self.level(message.strip())
            if self.raw:
                sys.__stdout__.write(message)
    def flush(self):
        pass

def setup_logging():
    """Setup dual logging to console and timestamped file"""
    log_dir = os.path.join(project_root, 'logs', 'system')
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    log_file = os.path.join(log_dir, f"orbiter_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    l = logging.getLogger("ORBITER")
    
    # 🔥 Redirect stdout and stderr to logger (with raw support for stdout)
    sys.stdout = LoggerWriter(l.info, raw=True)
    sys.stderr = LoggerWriter(l.error)
    
    return l

logger = setup_logging()

def manage_lockfile(action="acquire"):
    """Manage application lock file to prevent multiple instances"""
    lock_file = os.path.join(project_root, '.orbiter.lock')
    
    if action == "acquire":
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    content = f.read().strip()
                    if not content: raise ValueError("Empty lock file")
                    old_pid = int(content)
                # Check if process is actually running
                os.kill(old_pid, 0)
                logger.error(f"❌ Another instance is already running (PID: {old_pid}). Exiting.")
                sys.exit(1)
            except (OSError, ValueError):
                # OSError: PID doesn't exist. ValueError: file is empty or corrupted.
                if os.path.exists(lock_file):
                    os.remove(lock_file)
                    logger.warning("🧹 Cleared stale or invalid lock file.")
        
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        logger.info(f"🔒 Lock acquired (PID: {os.getpid()})")
        
    elif action == "release":
        if os.path.exists(lock_file):
            os.remove(lock_file)
            logger.info("🔓 Lock released")

class Orbiter:
    def __init__(self, simulation: bool = False):
        self.simulation = simulation
        self.client = None
        self.state = None
        self.evaluator = Evaluator()
        self.executor = None
        self.syncer = None

    def _get_active_segment(self):
        """Auto-detect if we should run NFO or MCX with Hibernation support"""
        ist = pytz.timezone('Asia/Kolkata')
        
        while True:
            now = datetime.now(ist)
            current_time = now.time()
            is_weekend = now.weekday() >= 5
            
            # 1. Initial Segment Selection (based on time)
            import config.nfo.config as nfo
            import config.mcx.config as mcx
            
            # Determine Segment
            if current_time > nfo.MARKET_CLOSE:
                segment, seg_name = mcx, 'mcx'
            else:
                segment, seg_name = nfo, 'nfo'

            # 2. Check if the determined segment is actually LIVE
            is_holiday = now.strftime("%Y-%m-%d") in segment.MARKET_HOLIDAYS
            is_off_hours = not (segment.MARKET_OPEN <= current_time <= segment.MARKET_CLOSE)
            
            # 3. Decision Logic
            if self.simulation:
                # In simulation, we always run the best fit segment
                logger.info(f"🧪 Simulation: Using {seg_name.upper()} context")
                return segment, seg_name

            if is_weekend or is_holiday or is_off_hours:
                reason = "WEEKEND" if is_weekend else ("HOLIDAY" if is_holiday else f"OFF-HOURS ({seg_name.upper()})")
                logger.info(f"💤 {reason}. Hibernating for 10 minutes...")
                # Non-blocking sleep: check every 60s but keep thread alive
                for _ in range(10):
                    time.sleep(60)
                continue # Re-check after sleep
            
            logger.info(f"🟢 Market is LIVE for {seg_name.upper()}")
            return segment, seg_name

    def is_session_active(self):
        """Check if current time is within active market hours for the loaded segment"""
        if not self.state or not self.state.config:
            return False
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist).time()
        start = self.state.config.get('MARKET_OPEN')
        end = self.state.config.get('MARKET_CLOSE')
        if start and end:
            return start <= now <= end
        return False

    def setup(self):
        # 🎧 Start Global Command Listener Early
        def safe_cleanup():
            if self.is_session_active():
                send_telegram_msg("❌ *Cleanup Blocked:* Cannot reset sheets during active trading session.")
                return False
            cleanup_google_sheets()
            return True

        def handle_ai_query(q):
            if not self.state: return "🤖 *Orbiter:* System is currently hibernating. Full state context is unavailable."
            try:
                return self.ai.ask(q, self._get_ai_context())
            except Exception as e:
                logger.error(f"❌ AI Query Error: {e}")
                return f"❌ AI Error: Internal state processing failed ({str(e)})"

        callbacks = {
            "margin": lambda: self.summary.generate_margin_status() if self.summary else "💤 *Orbiter:* Hibernating. Margin data unavailable.",
            "status": lambda: self.summary.generate_pre_session_report() if self.summary else "💤 *Orbiter:* Hibernating. Session report unavailable.",
            "scan": lambda: self.summary.generate_live_scan_report(self.state) if self.summary and self.state else "💤 *Orbiter:* Hibernating. No active scans.",
            "cleanup": safe_cleanup,
            "query": handle_ai_query,
            "version": lambda: f"🤖 *Orbiter v{VERSION}*"
        }
        listener = TelegramCommandListener(callbacks)
        listener.start()

        segment, seg_name = self._get_active_segment()
        logger.info(f"✅ Initializing Engine [v{VERSION}] for {seg_name.upper()}...")
        
        # Build merged configuration
        full_config = {
            **vars(global_config),
            'MARKET_OPEN': segment.MARKET_OPEN,
            'MARKET_CLOSE': segment.MARKET_CLOSE,
            'OPTION_INSTRUMENT': segment.OPTION_INSTRUMENT,
            'SIMULATION': self.simulation,
            'VERBOSE_LOGS': True # 🔥 FORCE
        }
        
        # Initialize Agnostic Components
        self.client = BrokerClient("../ShoonyaApi-py/cred.yml", segment_name=seg_name)
        self.state = OrbiterState(self.client, segment.SYMBOLS_FUTURE_UNIVERSE, filters, full_config)
        
        # Initialise Summary Manager
        self.summary = SummaryManager(self.client, seg_name, version=VERSION)
        
        # Initialise AI Handler
        cred_path = os.path.join(project_root, "ShoonyaApi-py", "cred.yml")
        self.ai = OrbiterAI(cred_path)

        # Inject agnostic sheets logic
        from bot.sheets import log_buy_signals, log_closed_positions, update_active_positions
        from filters import get_filters
        
        self.executor = Executor(log_buy_signals, log_closed_positions, get_filters('sl'), get_filters('tp'), summary_manager=self.summary)
        self.syncer = Syncer(update_active_positions)
        
        # Link state back to components
        self.state.load_session() # 🔥 Recover Memory

        logger.info(f"📊 Universe: {len(segment.SYMBOLS_FUTURE_UNIVERSE)} tokens")
        logger.info(f"🎯 Entry Threshold: {full_config['TRADE_SCORE']}pts")

    def login(self):
        ok = self.client.login()
        if not ok: return False
        self.client.start_live_feed(self.state.symbols)
        return True

    def _get_ai_context(self):
        """Package current bot state for AI analysis"""
        # Ensure we only send JSON-serializable data
        cache = self.state.filter_results_cache if hasattr(self.state, 'filter_results_cache') else {}
        
        return {
            "config": {
                "TRADE_SCORE": self.state.config.get("TRADE_SCORE", 0),
                "TOP_N": self.state.config.get("TOP_N", 0),
                "SEGMENT": getattr(self.client, 'segment_name', 'UNKNOWN')
            },
            "active_positions": [
                {"symbol": p.get("symbol", "??"), "strategy": p.get("strategy", "??"), "entry": p.get("entry_price", 0)}
                for p in self.state.active_positions.values()
            ],
            "recent_filters": cache
        }

    def run(self):
        try:
            # ☀️ Market Start Summary
            # Only send if we didn't just recover a very recent session
            if not self.state.active_positions:
                try:
                    pre_report = self.summary.generate_pre_session_report()
                    send_telegram_msg(pre_report)
                except Exception as e:
                    logger.error(f"⚠️ Could not generate pre-session report: {e}")
                    send_telegram_msg(f"🚀 *Orbiter Online*\nSegment: `{self.state.config['OPTION_INSTRUMENT']}`")
            
            last_sl_check = 0
            while True:
                now_ts = time.time()
                self.state.save_session() # 🔥 Persist Memory every loop

                # EOD Auto-Reset (3:15 PM for NFO, 11:15 PM for MCX)
                ist = pytz.timezone('Asia/Kolkata')
                now = datetime.now(ist).time()
                
                # Check for reset time (15 mins before close)
                close_time = self.state.config['MARKET_CLOSE']
                reset_hour = (close_time.hour if close_time.minute >= 15 else close_time.hour - 1)
                reset_min = (close_time.minute - 15) if close_time.minute >= 15 else (60 + close_time.minute - 15)
                
                if not self.state.config['SIMULATION'] and now >= dt_time(reset_hour, reset_min):
                    if self.state.active_positions:
                        logger.info("🔄 Triggering Market Close Reset (Squaring Off)...")
                        self.executor.square_off_all(self.state, reason="Market Close Reset")
                    
                    logger.info("🏁 Session ended. Preparing debrief...")
                    time.sleep(30) # Wait for Shoonya to settle positions/orders
                    
                    try:
                        post_report = self.summary.generate_post_session_report()
                        send_telegram_msg(post_report)
                    except Exception as e:
                        logger.error(f"⚠️ Could not generate post-session report: {e}")
                        send_telegram_msg("🏁 *Orbiter:* Session ended (Report failed).")

                    logger.info("💤 Hibernating until next segment check...")
                    # Non-blocking sleep: check every 60s but keep the process alive
                    # This ensures the Telegram background thread stays responsive
                    for _ in range(30): # 30 minutes
                        if not self.is_running: break
                        time.sleep(60)
                    break 
                
                # Evaluation Cycle
                scores = {}
                self.state.last_scan_metrics = []
                for token in self.state.symbols:
                    score = self.evaluator.evaluate_filters(self.state, token)
                    if score != 0: scores[token] = score
                
                # Execute Signals
                self.executor.rank_signals(self.state, scores, self.syncer)

                # SL/TP Monitoring
                if now_ts - last_sl_check >= 60:
                    exit_hits = self.executor.check_sl(self.state, self.syncer)
                    if exit_hits:
                        logger.info(f"🔔 SL/TP Hits: {len(exit_hits)} positions squared off")
                        lines = []
                        for hit in exit_hits:
                            # Calculate PnL for message
                            strategy = hit.get('strategy', '')
                            lot_size = int(hit.get('lot_size', 0))
                            pnl_val = 0.0
                            if 'FUTURE' in strategy:
                                entry = float(hit.get('entry_price', 0))
                                exit_p = float(hit.get('exit_price', 0))
                                if 'SHORT' in strategy: pnl_val = (entry - exit_p) * lot_size
                                else: pnl_val = (exit_p - entry) * lot_size
                            else:
                                # Spread
                                atm_e = float(hit.get('atm_premium_entry', 0) or 0)
                                hdg_e = float(hit.get('hedge_premium_entry', 0) or 0)
                                atm_x = float(hit.get('atm_premium_exit', 0) or 0)
                                hdg_x = float(hit.get('hedge_premium_exit', 0) or 0)
                                if atm_x and hdg_x:
                                    pnl_val = ((atm_e - hdg_e) - (atm_x - hdg_x)) * lot_size
                            
                            lines.append(f"• `{hit.get('symbol')}`: {hit.get('reason', 'SL/TP')} (₹{pnl_val:.2f}) @ {hit.get('exit_price')}")
                        
                        summary = "\n".join(lines)
                        send_telegram_msg(f"🎯 *Positions Closed*\n\n{summary}")
                    last_sl_check = now_ts
                
                # Scan Metrics Logging
                from bot.sheets import log_scan_metrics
                if log_scan_metrics and self.state.last_scan_metrics:
                    if now_ts - self.state.last_scan_log_ts >= 60:
                        tab_name = f"scan_metrics_{self.client.segment_name.lower()}"
                        log_scan_metrics(self.state.last_scan_metrics, tab_name=tab_name)
                        self.state.last_scan_log_ts = now_ts
                        self.syncer.sync_active_positions_to_sheets(self.state)

                time.sleep(self.state.config.get('UPDATE_INTERVAL', 5))
                
        except KeyboardInterrupt:
            logger.info("👋 Shutdown signal received")
        except Exception as e:
            logger.critical(f"💥 CRITICAL CRASH: {e}")
            logger.error(traceback.format_exc())
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulation", action="store_true")
    args = parser.parse_args()

    manage_lockfile("acquire")
    try:
        bot = Orbiter(simulation=args.simulation)
        bot.verbose_logs = True # 🔥 FORCE DEBUG
        bot.setup()
        if bot.login():
            bot.run()
    except Exception as e:
        logger.critical(f"💀 FATAL ERROR: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        manage_lockfile("release")
        # Final safety sleep to prevent aggressive systemd restart loops
        time.sleep(10)
