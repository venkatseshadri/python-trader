#!/usr/bin/env python3
"""
Data Capture Script - Captures live broker data for test suite.

Run this once to capture:
- Scrip master (symbol/token mappings)
- Margin requirements  
- Sample candle data

After capture, tests can run offline using this data.

Usage:
    python3 capture_test_data.py [--output-dir orbiter/tests/data]
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Setup path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'ShoonyaApi-py'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataCapture")

# Map exchange codes to file suffixes
EXCHANGE_MAP = {
    'NSE': 'nse',
    'NFO': 'nfo', 
    'BFO': 'bfo',
    'MCX': 'mcx',
}


def get_broker_client():
    """Initialize and login to broker."""
    from orbiter.core.broker.connection import ConnectionManager
    
    logger.info("🔐 Initializing broker connection...")
    conn = ConnectionManager()
    
    if not conn.login():
        raise RuntimeError("❌ Login failed!")
    
    logger.info("✅ Logged in successfully")
    return conn


def capture_scrip_master(conn, exchange: str, output_dir: str) -> Dict[str, Any]:
    """Capture scrip master for exchange."""
    logger.info(f"📥 Capturing scrip master for {exchange}...")
    
    try:
        # Get scrip master from API
        ret = conn.api.get_scrip_master(exchange=exchange)
        
        if not ret or ret.get('stat') != 'Ok':
            logger.warning(f"⚠️ No data for {exchange}: {ret}")
            return {}
        
        # Parse and structure the data
        symbols = ret.get('values', [])
        logger.info(f"   Got {len(symbols)} symbols for {exchange}")
        
        # Convert to token-indexed dict
        token_data = {}
        for sym in symbols:
            token = str(sym.get('token', ''))
            if token:
                token_data[token] = {
                    'token': token,
                    'symbol': sym.get('symbol', ''),
                    'tradingsymbol': sym.get('tsym', ''),
                    'exchange': sym.get('exch', exchange),
                    'lotsize': int(sym.get('ls', 1)),
                    'instrument': sym.get('inst', ''),
                    'option_type': sym.get('optt', ''),
                    'strike_price': sym.get('strike', 0),
                    'expiry': sym.get('expdt', ''),
                }
        
        output_file = os.path.join(output_dir, f'scrip_{EXCHANGE_MAP[exchange]}.json')
        with open(output_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        logger.info(f"   💾 Saved to {output_file}")
        
        return token_data
        
    except Exception as e:
        logger.error(f"❌ Failed to capture {exchange}: {e}")
        return {}


def capture_margins(conn, output_dir: str) -> Dict[str, Any]:
    """Capture margin/limits data."""
    logger.info("📥 Capturing margin/limits...")
    
    try:
        ret = conn.api.get_limits()
        
        if not ret or ret.get('stat') != 'Ok':
            logger.warning(f"⚠️ No margin data: {ret}")
            return {}
        
        # Extract only what we need for testing (no sensitive data)
        margin_data = {
            'cash': ret.get('cash', 0),
            'available_balance': ret.get('brkcoll', 0),
            'available_margin': ret.get('unblock_margin', 0),
            'utilized_margin': ret.get('margin_used', 0),
            'available_margin_sqr': ret.get('unblock_margin_sqr', 0),
            'segment_limits': ret.get('seg Limits', []),
            'capture_time': datetime.now().isoformat(),
        }
        
        output_file = os.path.join(output_dir, 'margins.json')
        with open(output_file, 'w') as f:
            json.dump(margin_data, f, indent=2)
        logger.info(f"   💾 Saved margins to {output_file}")
        
        return margin_data
        
    except Exception as e:
        logger.error(f"❌ Failed to capture margins: {e}")
        return {}


def capture_candles(conn, symbols: List[Dict], output_dir: str, lookback_mins: int = 60) -> Dict[str, Any]:
    """Capture historical candle data for sample symbols."""
    logger.info(f"📥 Capturing candles for {len(symbols)} symbols (last {lookback_mins} mins)...")
    
    import pytz
    ist = pytz.timezone('Asia/Kolkata')
    end_dt = datetime.now(ist)
    start_dt = end_dt - timedelta(minutes=lookback_mins)
    
    candles_data = {}
    
    for sym in symbols[:20]:  # Limit to 20 symbols
        try:
            token = str(sym.get('token', ''))
            exchange = sym.get('exchange', 'NSE')
            
            if not token:
                continue
            
            ret = conn.api.get_time_price_series(
                exchange=exchange,
                token=token,
                starttime=start_dt.timestamp(),
                endtime=end_dt.timestamp(),
                interval=5  # 5-minute candles
            )
            
            if ret and isinstance(ret, list):
                key = f"{exchange}|{token}"
                candles_data[key] = {
                    'token': token,
                    'exchange': exchange,
                    'symbol': sym.get('symbol', sym.get('tradingsymbol', '')),
                    'candles': ret[-50:] if len(ret) > 50 else ret,  # Last 50 candles
                    'count': len(ret),
                }
                logger.info(f"   ✅ {key}: {len(ret)} candles")
            
        except Exception as e:
            logger.warning(f"   ⚠️ Failed {sym.get('symbol')}: {e}")
    
    output_file = os.path.join(output_dir, 'candles.json')
    with open(output_file, 'w') as f:
        json.dump(candles_data, f, indent=2)
    logger.info(f"   💾 Saved {len(candles_data)} candle sets to {output_file}")
    
    return candles_data


def capture_positions(conn, output_dir: str) -> Dict[str, Any]:
    """Capture current positions."""
    logger.info("📥 Capturing positions...")
    
    try:
        ret = conn.api.get_positions()
        
        if not ret or ret.get('stat') != 'Ok':
            logger.info("   No open positions")
            return {'positions': []}
        
        positions = ret.get('values', [])
        output_file = os.path.join(output_dir, 'positions.json')
        
        with open(output_file, 'w') as f:
            json.dump({'positions': positions, 'count': len(positions)}, f, indent=2)
        
        logger.info(f"   💾 Saved {len(positions)} positions")
        return {'positions': positions}
        
    except Exception as e:
        logger.error(f"❌ Failed to capture positions: {e}")
        return {'positions': []}


def main():
    parser = argparse.ArgumentParser(description='Capture live broker data for test suite')
    parser.add_argument('--output-dir', default='orbiter/tests/data', help='Output directory')
    parser.add_argument('--exchanges', default='NSE,NFO,BFO,MCX', help='Exchanges to capture')
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_dir = os.path.join(PROJECT_ROOT, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"📁 Output directory: {output_dir}")
    
    # Get broker connection
    conn = get_broker_client()
    
    exchanges = [e.strip() for e in args.exchanges.split(',')]
    
    # Capture scrip master for each exchange
    all_symbols = {}
    for exch in exchanges:
        if exch in EXCHANGE_MAP:
            data = capture_scrip_master(conn, exch, output_dir)
            all_symbols[exch] = data
    
    # Capture margins
    margins = capture_margins(conn, output_dir)
    
    # Capture sample candles (use first 30 NSE symbols)
    sample_symbols = []
    if 'NSE' in all_symbols:
        for token, info in list(all_symbols['NSE'].items())[:30]:
            sample_symbols.append(info)
    
    if sample_symbols:
        capture_candles(conn, sample_symbols, output_dir)
    
    # Capture positions
    positions = capture_positions(conn, output_dir)
    
    # Save summary
    summary = {
        'capture_time': datetime.now().isoformat(),
        'exchanges': {ex: len(data) for ex, data in all_symbols.items()},
        'margins_available': bool(margins),
        'positions_count': len(positions.get('positions', [])),
    }
    
    summary_file = os.path.join(output_dir, 'capture_summary.json')
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info("=" * 50)
    logger.info("✅ DATA CAPTURE COMPLETE!")
    logger.info(f"   Scrip masters: {summary['exchanges']}")
    logger.info(f"   Margins: {'Yes' if summary['margins_available'] else 'No'}")
    logger.info(f"   Positions: {summary['positions_count']}")
    logger.info(f"   Summary: {summary_file}")
    logger.info("=" * 50)
    
    conn.close()


if __name__ == '__main__':
    main()