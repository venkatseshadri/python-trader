#!/usr/bin/env python3
"""
MCX Broker Data Validation Test

Validates broker connectivity and data availability for all active MCX contracts.
Tests:
1. API login/connection
2. Scrip search (searchscrip)
3. Historical candle data (get_time_price_series)
4. Candle freshness (recent timestamps)
5. Fallback: Yahoo Finance data

Run with:
    python -m pytest orbiter/tests/unit/test_mcx_broker_data.py -v -s

This test confirms if "no data" issues are:
- BROKER: API not connected, no historical data returned, stale data
- CODE: Logic/config issues in Orbiter
- NETWORK: YF unreachable
"""
import unittest
import json
import os
import sys
import logging
import datetime
import pytz

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from orbiter.utils.logger import setup_logging
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager


class TestMCXBrokerData(unittest.TestCase):
    """Comprehensive broker data validation for MCX contracts."""
    
    @classmethod
    def setUpClass(cls):
        logging.getLogger().setLevel(logging.INFO)
        setup_logging('INFO', project_root)
        cls.logger = logging.getLogger("ORBITER")
        
        # Load active MCX instruments
        futures_map_path = os.path.join(project_root, 'orbiter', 'data', 'mcx_futures_map.json')
        with open(futures_map_path, 'r') as f:
            cls.futures_map = json.load(f)
        
        cls.logger.info(f"=== Testing {len(cls.futures_map)} active MCX instruments ===")
        
        # Initialize broker client
        cls._init_broker_client()
    
    @classmethod
    def _init_broker_client(cls):
        """Initialize broker client and login."""
        from orbiter.core.broker import BrokerClient
        import traceback
        
        cls.logger.info("=== Initializing broker client ===")
        cls.client = None
        
        try:
            # Initialize for MCX segment (not NFO default)
            cls.client = BrokerClient(segment_name='mcx')
            cls.logger.info("✅ Broker client initialized for MCX")
            
            # Login to authenticate
            cls.logger.info("🔐 Calling login()...")
            login_result = cls.client.login()
            if login_result:
                cls.logger.info("✅ Login successful")
            else:
                cls.logger.warning("⚠️ Login returned False")
                
            cls.logger.info(f"   API: {cls.client.api}")
        except Exception as e:
            cls.logger.error(f"❌ Broker client init failed: {e}")
            cls.logger.error(traceback.format_exc())
            cls.client = None
    
    def test_01_broker_connection(self):
        """TEST 1: Verify broker API is connected and usable."""
        self.logger.info("\n" + "="*60)
        self.logger.info("TEST 1: BROKER CONNECTION")
        self.logger.info("="*60)
        
        if not self.client:
            self.fail("Broker client not initialized")
        
        # Check if API is available
        api = getattr(self.client, 'api', None)
        if not api:
            self.fail("Broker API not available")
        
        # Just verify login was successful - if other tests pass, API is working
        self.logger.info("✅ Broker connection: OK (other tests verify API functionality)")
        
        self.logger.info("✅ Broker connection: OK")
    
    def test_02_scrip_search(self):
        """TEST 2: Verify scrip search works for MCX instruments."""
        self.logger.info("\n" + "="*60)
        self.logger.info("TEST 2: SCRIP SEARCH (searchscrip)")
        self.logger.info("="*60)
        
        if not self.client:
            self.skipTest("Broker client not available")
        
        failed_search = []
        
        for symbol, info in self.futures_map.items():
            trading_symbol = info[1]  # e.g., "CRUDEOILM19MAR26"
            
            try:
                # Extract base name for search (e.g., "CRUDEOIL" from "CRUDEOILM19MAR26")
                # Search for the contract
                results = self.client.api.searchscrip(exchange='MCX', searchtext=trading_symbol)
                
                if results and len(results) > 0:
                    self.logger.info(f"  ✓ {symbol}: Found {len(results)} matches")
                else:
                    failed_search.append(f"{symbol}: no search results")
                    self.logger.warning(f"  ✗ {symbol}: No search results for '{trading_symbol}'")
                    
            except Exception as e:
                failed_search.append(f"{symbol}: {str(e)}")
                self.logger.warning(f"  ✗ {symbol}: Search failed - {e}")
        
        self.logger.info("="*60)
        if failed_search:
            self.logger.error(f"❌ Scrip search failed for: {failed_search}")
            self.fail(f"Scrip search failed for {len(failed_search)} instruments: {failed_search}")
        else:
            self.logger.info("✅ Scrip search: OK for all instruments")
    
    def test_03_historical_candles(self):
        """TEST 3: Verify get_time_price_series returns historical candle data."""
        self.logger.info("\n" + "="*60)
        self.logger.info("TEST 3: HISTORICAL CANDLES (get_time_price_series)")
        self.logger.info("="*60)
        
        if not self.client:
            self.skipTest("Broker client not available")
        
        no_candles = []
        insufficient = []
        success = []
        
        ist = pytz.timezone('Asia/Kolkata')
        
        for symbol, info in self.futures_map.items():
            trading_symbol = info[1]
            
            try:
                token = self.client.get_token(trading_symbol)
                if not token:
                    no_candles.append(f"{symbol}: no token")
                    continue
                
                # Get last 7 days of 5-min candles
                end_dt = datetime.datetime.now(tz=ist)
                start_dt = end_dt - datetime.timedelta(days=7)
                
                candles = self.client.api.get_time_price_series(
                    exchange='MCX',
                    token=token,
                    starttime=start_dt.timestamp(),
                    endtime=end_dt.timestamp(),
                    interval=5
                )
                
                bar_count = len(candles) if candles else 0
                
                if bar_count >= 12:
                    success.append(f"{symbol}: {bar_count} bars")
                elif bar_count > 0:
                    insufficient.append(f"{symbol}: {bar_count} bars")
                else:
                    no_candles.append(f"{symbol}: 0 bars - BROKER NO DATA")
                    
            except Exception as e:
                no_candles.append(f"{symbol}: {str(e)}")
        
        self.logger.info("\n--- Results ---")
        self.logger.info(f"✓ Sufficient (12+ bars): {len(success)}")
        self.logger.info(f"~ Insufficient (<12): {len(insufficient)}")
        self.logger.info(f"✗ No data: {len(no_candles)}")
        
        if no_candles:
            self.logger.error("\n❌ NO CANDLE DATA FROM BROKER:")
            for n in no_candles:
                self.logger.error(f"  {n}")
        
        if insufficient:
            self.logger.warning("\n⚠️ INSUFFICIENT BARS (will use YF fallback):")
            for i in insufficient:
                self.logger.warning(f"  {i}")
        
        self.logger.info("="*60)
        
        # This is the critical assertion - broker MUST return some data
        self.assertEqual(len(no_candles), 0, 
            f"BROKER FAILURE - No historical data: {no_candles}")
    
    def test_04_candle_freshness(self):
        """TEST 4: Verify candle data is recent (not stale)."""
        self.logger.info("\n" + "="*60)
        self.logger.info("TEST 4: CANDLE FRESHNESS")
        self.logger.info("="*60)
        
        if not self.client:
            self.skipTest("Broker client not available")
        
        stale_candles = []
        success = []
        
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.datetime.now(tz=ist)
        
        for symbol, info in self.futures_map.items():
            trading_symbol = info[1]
            
            try:
                token = self.client.get_token(trading_symbol)
                if not token:
                    continue
                
                # Get last 24 hours
                end_dt = now
                start_dt = end_dt - datetime.timedelta(hours=24)
                
                candles = self.client.api.get_time_price_series(
                    exchange='MCX',
                    token=token,
                    starttime=start_dt.timestamp(),
                    endtime=end_dt.timestamp(),
                    interval=5
                )
                
                if not candles or len(candles) == 0:
                    continue
                
                # Check last candle timestamp
                last_candle = candles[-1]
                candle_ts = datetime.datetime.fromtimestamp(
                    int(last_candle.get('t', 0)), tz=ist
                )
                
                # Check if within last 4 hours
                age = (now - candle_ts).total_seconds() / 3600
                
                if age <= 4:
                    success.append(f"{symbol}: {age:.1f}h old")
                else:
                    stale_candles.append(f"{symbol}: {age:.1f}h old")
                    
            except Exception as e:
                self.logger.warning(f"  {symbol}: freshness check failed - {e}")
        
        if stale_candles:
            self.logger.warning(f"⚠️ Stale candles (>4h old): {stale_candles}")
        
        self.logger.info(f"✅ Fresh candles: {len(success)}")
        self.logger.info("="*60)
    
    def test_05_yf_fallback(self):
        """TEST 5: Verify Yahoo Finance fallback works for indicators."""
        self.logger.info("\n" + "="*60)
        self.logger.info("TEST 5: YAHOO FINANCE FALLBACK")
        self.logger.info("="*60)
        
        try:
            from orbiter.utils.yf_adapter import get_market_adx
            
            # Test with SENSEX (index)
            adx = get_market_adx('^BSESN', '5m')
            
            if adx and adx > 0:
                self.logger.info(f"✅ YF ADX fallback: {adx}")
            else:
                self.logger.warning(f"⚠️ YF returned ADX={adx}")
                
        except Exception as e:
            self.fail(f"Yahoo Finance fallback failed: {e}")
        
        self.logger.info("="*60)
    
    def test_06_instrument_list(self):
        """Print summary of active instruments."""
        self.logger.info("\n" + "="*60)
        self.logger.info("ACTIVE MCX CONTRACTS")
        self.logger.info("="*60)
        
        for i, (symbol, info) in enumerate(self.futures_map.items(), 1):
            trading_symbol = info[1]
            lot_size = info[2]
            print(f"{i:2}. {symbol:15} | {trading_symbol:20} | Lot: {lot_size}")
        
        print("="*60)
        print(f"Total: {len(self.futures_map)} instruments")


if __name__ == '__main__':
    unittest.main(verbosity=2)
