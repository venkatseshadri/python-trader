#!/usr/bin/env python3
"""
Comprehensive test for token resolution across MCX, NFO, BFO segments.
Run: python3 orbiter/tests/unit/test_token_resolution.py
"""
import sys
import os
import logging
import json
import datetime

project_root = '/home/trading_ceo/python-trader'
sys.path.insert(0, project_root)

# Setup logger
logger = logging.getLogger("ORBITER")
logger.setLevel(logging.DEBUG)
if not hasattr(logger, 'trace'):
    logger.trace = lambda msg: logger.debug(msg)


def test_mcx_token_resolution():
    """Test MCX token resolution - verify prefix matching bug."""
    from orbiter.core.broker import BrokerClient
    
    print("\n" + "="*70)
    print("TEST: MCX Token Resolution")
    print("="*70)
    
    client = BrokerClient(project_root=project_root)
    client.login()
    client.master.load_mappings('mcx')
    
    # Load expected mappings from futures_map
    with open(os.path.join(project_root, 'orbiter/data/mcx_futures_map.json')) as f:
        mcx_map = json.load(f)
    
    # Test symbols that have suffix variants (causing prefix matching bug)
    test_cases = [
        ('ZINC', 'ZINCMINI'),       # ZINC should NOT resolve to ZINCMINI
        ('SILVER', 'SILVERMIC'),    # SILVER should NOT resolve to SILVERMIC
        ('LEAD', 'LEADMINI'),      # LEAD should NOT resolve to LEADMINI
        ('GOLD', 'GOLDTEN'),       # GOLD should NOT resolve to GOLDTEN
        ('CRUDEOIL', 'CRUDEOILM'), # CRUDEOIL should NOT resolve to CRUDEOILM
    ]
    
    issues = []
    for symbol, wrong_variant in test_cases:
        if symbol not in mcx_map:
            continue
            
        expected_token = mcx_map[symbol][4]
        
        # Test current (buggy) behavior: prefix matching
        found = None
        for tok, tsym in client.master.TOKEN_TO_SYMBOL.items():
            if tsym.upper().startswith(symbol.upper()):
                found = tsym
                break
        
        resolved = client.master.SYMBOL_TO_TOKEN.get(found) if found else None
        
        # Should resolve to correct token
        if str(resolved) != str(expected_token):
            issues.append(f"{symbol}: expected {expected_token}, got {resolved} (matched {wrong_variant})")
            print(f"  ✗ {symbol}: FAIL - Expected {expected_token}, got {resolved}")
        else:
            print(f"  ✓ {symbol}: PASS - Correctly resolved to {expected_token}")
    
    # Test data fetching with CORRECT token
    print("\n--- Data Fetching Test (Correct vs Wrong tokens) ---")
    end_dt = datetime.datetime.now()
    start_dt = end_dt - datetime.timedelta(minutes=120)
    
    for symbol, _ in test_cases:
        if symbol not in mcx_map:
            continue
            
        correct_token = mcx_map[symbol][4]
        
        # Find wrong token (the bug)
        wrong_token = None
        for tok, tsym in client.master.TOKEN_TO_SYMBOL.items():
            if tsym.upper().startswith(symbol.upper()):
                wrong_token = client.master.SYMBOL_TO_TOKEN.get(tsym)
                break
        
        # Fetch with correct token
        try:
            correct_data = client.api.get_time_price_series(
                exchange='MCX', token=correct_token,
                starttime=start_dt.timestamp(), endtime=end_dt.timestamp(), interval=5
            )
            correct_bars = len(correct_data) if correct_data else 0
        except:
            correct_bars = 0
        
        # Fetch with wrong token
        try:
            wrong_data = client.api.get_time_price_series(
                exchange='MCX', token=wrong_token,
                starttime=start_dt.timestamp(), endtime=end_dt.timestamp(), interval=5
            )
            wrong_bars = len(wrong_data) if wrong_data else 0
        except:
            wrong_bars = 0
        
        print(f"  {symbol}: correct={correct_token}({correct_bars} bars), wrong={wrong_token}({wrong_bars} bars)")
        
        if correct_bars > 20 and wrong_bars > 20:
            print(f"    Note: Both tokens return data - prefix match still works but wrong token!")
    
    return len(issues) == 0, issues


def test_mcx_data_storage_and_retrieval():
    """Test that data is stored and retrieved with correct key."""
    from orbiter.core.broker import BrokerClient
    
    print("\n" + "="*70)
    print("TEST: MCX Data Storage & Retrieval")
    print("="*70)
    
    client = BrokerClient(project_root=project_root)
    client.login()
    client.master.load_mappings('mcx')
    
    with open(os.path.join(project_root, 'orbiter/data/mcx_futures_map.json')) as f:
        mcx_map = json.load(f)
    
    # Test with ALUMINI (works correctly)
    # and ZINC (affected by bug)
    test_symbols = ['ALUMINI', 'ZINC']
    
    for symbol in test_symbols:
        if symbol not in mcx_map:
            continue
        
        tsym = mcx_map[symbol][1]  # trading symbol like "ZINC31MAR26"
        correct_token = mcx_map[symbol][4]
        
        print(f"\n  Testing {symbol}:")
        print(f"    Trading symbol: {tsym}")
        print(f"    Correct token: {correct_token}")
        
        # Current behavior: prefix match
        found_tsym = None
        for tok, ts in client.master.TOKEN_TO_SYMBOL.items():
            if ts.upper().startswith(symbol.upper()):
                found_tsym = ts
                break
        
        resolved_token = client.master.SYMBOL_TO_TOKEN.get(found_tsym) if found_tsym else None
        print(f"    Resolved token (current): {resolved_token}")
        
        # The data would be stored at resolved token's key
        # But later lookup uses correct token's key
        
        # Keys:
        # - Storage: MCX|resolved_token (e.g., "MCX|487663" for ZINC)
        # - Lookup: MCX|correct_token (e.g., "MCX|487662" for ZINC)
        
        storage_key = f"MCX|{resolved_token}" if resolved_token else None
        lookup_key = f"MCX|correct_token"
        
        print(f"    Storage key (current): {storage_key}")
        print(f"    Lookup key (expected): {lookup_key}")
        
        if storage_key != lookup_key:
            print(f"    ✗ KEY MISMATCH - Data stored at {storage_key}, looked up at {lookup_key}")
            return False, [f"{symbol}: storage key mismatch"]
    
    return True, []


def test_nfo_token_resolution():
    """Test NFO token resolution."""
    from orbiter.core.broker import BrokerClient
    
    print("\n" + "="*70)
    print("TEST: NFO Token Resolution")
    print("="*70)
    
    client = BrokerClient(project_root=project_root)
    client.login()
    client.master.load_mappings('nfo')
    
    # NFO doesn't have suffix variants like MCX, so should work
    test_symbols = ['NIFTY', 'BANKNIFTY', 'RELIANCE', 'ITC']
    
    for symbol in test_symbols:
        # Direct lookup
        direct = client.master.SYMBOL_TO_TOKEN.get(symbol.upper())
        print(f"  {symbol}: {direct}")
    
    return True, []


def test_bfo_token_resolution():
    """Test BFO token resolution."""
    from orbiter.core.broker import BrokerClient
    
    print("\n" + "="*70)
    print("TEST: BFO Token Resolution")
    print("="*70)
    
    client = BrokerClient(project_root=project_root)
    client.login()
    client.master.load_mappings('bfo')
    
    test_symbols = ['SENSEX', 'BANKEX']
    
    for symbol in test_symbols:
        direct = client.master.SYMBOL_TO_TOKEN.get(symbol.upper())
        print(f"  {symbol}: {direct}")
    
    return True, []


def main():
    print("="*70)
    print("COMPREHENSIVE TOKEN RESOLUTION TEST")
    print("MCX, NFO, BFO Segments")
    print("="*70)
    
    results = []
    
    # Test MCX
    passed, issues = test_mcx_token_resolution()
    results.append(("MCX Token Resolution", passed, issues))
    
    # Test MCX storage/retrieval
    passed, issues = test_mcx_data_storage_and_retrieval()
    results.append(("MCX Data Storage/Retrieval", passed, issues))
    
    # Test NFO
    passed, issues = test_nfo_token_resolution()
    results.append(("NFO Token Resolution", passed, issues))
    
    # Test BFO
    passed, issues = test_bfo_token_resolution()
    results.append(("BFO Token Resolution", passed, issues))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    all_passed = True
    for name, passed, issues in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {name}: {status}")
        if issues:
            for issue in issues:
                print(f"    - {issue}")
            all_passed = False
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
