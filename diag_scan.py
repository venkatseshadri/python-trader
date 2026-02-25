
import os
import sys
import pytz
from datetime import datetime
import time

# Setup Path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, 'orbiter'))
sys.path.append(os.path.join(base_dir, 'ShoonyaApi-py'))

from core.broker import BrokerClient
from core.engine.state import OrbiterState
from core.engine.evaluator import Evaluator
import orbiter.config.config as cfg
import orbiter.config.nfo.config as nfo
import orbiter.filters as filters

def scan_universe():
    print("🚀 INITIALIZING DIAGNOSTIC SCAN (v3.16.2)...")
    # Path is relative to project root, which ConnectionManager expects to be orbiter_root
    # But ConnectionManager thinks orbiter_root is project/orbiter.
    # So we pass ../ShoonyaApi-py/cred.yml
    client = BrokerClient("../ShoonyaApi-py/cred.yml", segment_name='nfo')
    if not client.login():
        print("❌ Login failed.")
        return
    
    universe = nfo.SYMBOLS_FUTURE_UNIVERSE
    # Link token 51714 to NIFTY for the evaluator
    client.master.TOKEN_TO_SYMBOL['51714'] = 'NIFTY'
    client.master.TOKEN_TO_SYMBOL['NFO|51714'] = 'NIFTY'

    full_config = {**vars(cfg), **vars(nfo), 'SIMULATION': True, 'VERBOSE_LOGS': False}
    state = OrbiterState(client, universe, filters, full_config, segment_name='nfo')
    evaluator = Evaluator()

    print(f"📊 Scanning Universe: {len(universe)} symbols...")
    # Prime more to find a trade
    client.prime_candles(universe)

    results = []
    for token in universe:
        # Resolve Score
        score = evaluator.evaluate_filters(state, token)
        if score != 0:
            data = client.SYMBOLDICT.get(token, {})
            symbol = data.get('t') or client.get_symbol(token.split('|')[-1])
            adx = state.filter_results_cache.get(token, {}).get('adx', 0)
            results.append((symbol, score, adx))

    # Sort by absolute score
    results.sort(key=lambda x: abs(x[1]), reverse=True)

    print("\n🎯 --- TOP SIGNALS ---")
    for symbol, score, adx in results[:10]:
        regime = "TRENDING" if adx >= 25 else "SIDEWAYS"
        print(f"📈 {str(symbol):12} | Score: {score:>+5.2f} | ADX: {adx:4.1f} ({regime})")

if __name__ == "__main__":
    scan_universe()
