#!/usr/bin/env python3
"""
🚀 ORBITER v3.1.0-20260217-440cb55 - Unified Segment Multi-Market Trader
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
import filters
import config.config as global_config

VERSION = "3.1.0-20260217-440cb55"

class LoggerWriter:
    def __init__(self, level):
        self.level = level
    def write(self, message):
        if message.strip():
            self.level(message.strip())
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
    
    # 🔥 Redirect stdout and stderr to logger
    sys.stdout = LoggerWriter(l.info)
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
        """Auto-detect if we should run NFO or MCX"""
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        current_time = now.time()
        
        # 1. Initial Segment Selection (based on time)
        import config.nfo.config as nfo
        import config.mcx.config as mcx
        
        if current_time > nfo.MARKET_CLOSE:
            logger.info("🌙 Evening session: Detected MCX time window")
            segment = mcx
            seg_name = 'mcx'
        else:
            logger.info("☀️ Day session: Detected NFO time window")
            segment = nfo
            seg_name = 'nfo'

        # 2. Segment-Specific Holiday/Off-Hours Check
        is_weekend = now.weekday() >= 5
        is_holiday = now.strftime("%Y-%m-%d") in segment.MARKET_HOLIDAYS
        is_off_hours = not (segment.MARKET_OPEN <= current_time <= segment.MARKET_CLOSE)
        
        if not self.simulation:
            if is_weekend or is_holiday or is_off_hours:
                reason = "WEEKEND" if is_weekend else ("HOLIDAY" if is_holiday else "OFF-HOURS")
                logger.warning(f"😴 {reason} for active segment! Soft-enabling SIMULATION mode.")
                self.simulation = True
            else:
                logger.info(f"🟢 Market is LIVE for {seg_name.upper()}")

        return segment, seg_name

    def setup(self):
        logger.info(f"✅ Initializing Engine [v{VERSION}]...")
        segment, seg_name = self._get_active_segment()
        
        # Build merged configuration
        full_config = {
            **vars(global_config),
            'MARKET_OPEN': segment.MARKET_OPEN,
            'MARKET_CLOSE': segment.MARKET_CLOSE,
            'OPTION_INSTRUMENT': segment.OPTION_INSTRUMENT,
            'SIMULATION': self.simulation
        }
        
        # Initialize Agnostic Components
        self.client = BrokerClient("../ShoonyaApi-py/cred.yml", segment_name=seg_name)
        self.state = OrbiterState(self.client, segment.SYMBOLS_FUTURE_UNIVERSE, filters, full_config)
        
        # Inject agnostic sheets logic
        from bot.sheets import log_buy_signals, log_closed_positions, update_active_positions
        from filters import get_filters
        
        self.executor = Executor(log_buy_signals, log_closed_positions, get_filters('sl'), get_filters('tp'))
        self.syncer = Syncer(update_active_positions)
        
        # Link state back to components
        self.state.evaluator = self.evaluator
        self.state.executor = self.executor
        self.state.syncer = self.syncer

        logger.info(f"📊 Universe: {len(segment.SYMBOLS_FUTURE_UNIVERSE)} tokens")
        logger.info(f"🎯 Entry Threshold: {full_config['TRADE_SCORE']}pts")

    def login(self):
        ok = self.client.login()
        if not ok: return False
        self.client.start_live_feed(self.state.symbols)
        return True

    def run(self):
        try:
            logger.info("⏳ Stabilizing connection (2s)...")
            time.sleep(2)
            
            last_sl_check = 0
            while True:
                now_ts = time.time()

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
                    
                    logger.info("🏁 Session ended. Exiting for scheduled restart...")
                    sys.exit(0)
                
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
                    last_sl_check = now_ts
                
                # Scan Metrics Logging
                from bot.sheets import log_scan_metrics
                if log_scan_metrics and self.state.last_scan_metrics:
                    if now_ts - self.state.last_scan_log_ts >= 60:
                        log_scan_metrics(self.state.last_scan_metrics)
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
        bot.setup()
        if bot.login():
            bot.run()
    except Exception as e:
        logger.critical(f"💀 FATAL ERROR: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        manage_lockfile("release")
