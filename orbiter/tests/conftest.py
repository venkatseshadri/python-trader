"""
Pytest configuration and fixtures for orbiter tests.

This module provides:
1. Custom pytest markers
2. Fixtures for captured test data (from live broker)
3. Fallback mock data when captured data not available

Usage:
    1. First time: Run capture_test_data.py to capture live data
    2. Subsequent runs: Tests automatically use captured data
"""

import os
import sys
import json
import logging
import pytest

# Setup path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("TEST_FIXTURES")

# Data directory
DATA_DIR = os.path.join(PROJECT_ROOT, 'orbiter', 'tests', 'data')


# === Custom Markers ===

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "broker: tests that require live broker connection")
    config.addinivalue_line("markers", "data: tests that require real market data files")
    config.addinivalue_line("markers", "integration: tests that require full system integration")
    config.addinivalue_line("markers", "captured: tests that prefer captured data over live")
    config.addinivalue_line("markers", "live: tests that require live broker connection (cannot use captured)")


# === Test Data Loader ===

class CapturedDataManager:
    """Load captured test data from files."""
    
    def __init__(self):
        self.data = {}
        self.data_dir = DATA_DIR
        self._loaded = False
    
    def load(self, force: bool = False) -> dict:
        """Load all captured data from files."""
        if self._loaded and not force:
            return self.data
        
        logger.info(f"📂 Loading test data from: {self.data_dir}")
        
        # Check if captured data exists
        if not os.path.exists(os.path.join(self.data_dir, 'capture_summary.json')):
            logger.info("⚠️ No captured data found - tests will use mocks")
            return self.data
        
        # Load each data file
        data_files = [
            'scrip_nse.json',
            'scrip_nfo.json', 
            'scrip_bfo.json',
            'scrip_mcx.json',
            'margins.json',
            'candles.json',
            'positions.json',
        ]
        
        for filename in data_files:
            filepath = os.path.join(self.data_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        key = filename.replace('.json', '')
                        self.data[key] = json.load(f)
                        logger.info(f"   ✅ Loaded {filename}: {len(self.data[key])} items")
                except Exception as e:
                    logger.warning(f"   ⚠️ Failed to load {filename}: {e}")
        
        self._loaded = True
        return self.data
    
    def get_scrip(self, exchange: str) -> dict:
        """Get scrip data for exchange."""
        self.load()
        key = f'scrip_{exchange.lower()}'
        return self.data.get(key, {})
    
    def get_margins(self) -> dict:
        """Get margin data."""
        self.load()
        return self.data.get('margins', {})
    
    def get_candles(self) -> dict:
        """Get candle data."""
        self.load()
        return self.data.get('candles', {})
    
    def get_positions(self) -> dict:
        """Get positions data."""
        self.load()
        return self.data.get('positions', {})
    
    def has_data(self) -> bool:
        """Check if captured data exists."""
        return os.path.exists(os.path.join(self.data_dir, 'capture_summary.json'))


# Global loader instance
_loader = None

def get_test_data_loader() -> CapturedDataManager:
    """Get test data loader singleton."""
    global _loader
    if _loader is None:
        _loader = CapturedDataManager()
    return _loader


# === Pytest Fixtures ===

@pytest.fixture(scope="session")
def test_data():
    """Load all captured test data for the session."""
    loader = get_test_data_loader()
    data = loader.load()
    yield data
    # No cleanup needed - read-only


@pytest.fixture(scope="session")
def has_captured_data():
    """Check if captured data files exist."""
    return os.path.exists(os.path.join(DATA_DIR, 'capture_summary.json'))


@pytest.fixture
def scrip_nse(test_data):
    """NSE scrip master data (captured or mock)."""
    data = test_data.get('scrip_nse', {})
    if not data:
        # Fallback to minimal mock
        return {
            '12345': {
                'token': '12345',
                'symbol': 'RECLTD',
                'tradingsymbol': 'RECLTD',
                'exchange': 'NSE',
                'lotsize': 1,
                'instrument': 'EQ',
            }
        }
    return data


@pytest.fixture
def scrip_nfo(test_data):
    """NFO scrip master data (captured or mock)."""
    data = test_data.get('scrip_nfo', {})
    if not data:
        return {
            '173883': {
                'token': '173883',
                'symbol': 'ZYDUSLIFE',
                'tradingsymbol': 'ZYDUSLIFE26MAY26P1280',
                'exchange': 'NFO',
                'lotsize': 900,
                'instrument': 'OPTSTK',
                'option_type': 'PE',
                'strike_price': 1280,
                'expiry': '26-MAY-2026',
            }
        }
    return data


@pytest.fixture
def scrip_bfo(test_data):
    """BFO scrip master data (captured or mock)."""
    return test_data.get('scrip_bfo', {})


@pytest.fixture
def scrip_mcx(test_data):
    """MCX scrip master data (captured or mock)."""
    return test_data.get('scrip_mcx', {})


@pytest.fixture
def captured_margins(test_data):
    """Margin data (captured or mock)."""
    data = test_data.get('margins', {})
    if not data:
        return {
            'cash': 100000,
            'available_balance': 75000,
            'available_margin': 50000,
            'utilized_margin': 25000,
        }
    return data


@pytest.fixture
def captured_candles(test_data):
    """Candle data (captured or mock)."""
    return test_data.get('candles', {})


@pytest.fixture
def captured_positions(test_data):
    """Positions data (captured or mock)."""
    return test_data.get('positions', {})


# === Fallback Mock Fixtures ===

@pytest.fixture
def mock_scrip_data():
    """Strict mock scrip data - no live fallback."""
    return {
        '12345': {
            'token': '12345',
            'symbol': 'RECLTD',
            'tradingsymbol': 'RECLTD',
            'exchange': 'NSE',
            'lotsize': 1,
            'instrument': 'EQ',
        },
        '45678': {
            'token': '45678',
            'symbol': 'SBIN',
            'tradingsymbol': 'SBIN',
            'exchange': 'NSE',
            'lotsize': 1,
            'instrument': 'EQ',
        },
    }


@pytest.fixture
def mock_margins():
    """Strict mock margin data - no live fallback."""
    return {
        'cash': 100000,
        'available_balance': 75000,
        'available_margin': 50000,
        'utilized_margin': 25000,
        'available_margin_sqr': 45000,
    }


@pytest.fixture
def mock_candles():
    """Strict mock candle data - no live fallback."""
    return {
        'NSE|12345': {
            'token': '12345',
            'exchange': 'NSE',
            'symbol': 'RECLTD',
            'candles': [
                {'time': '2024-01-01 09:15:00', 'into': 100.0, 'inth': 105.0, 'intl': 99.0, 'intc': 103.0, 'v': '1000'},
                {'time': '2024-01-01 09:20:00', 'into': 103.0, 'inth': 107.0, 'intl': 102.0, 'intc': 106.0, 'v': '1500'},
                {'time': '2024-01-01 09:25:00', 'into': 106.0, 'inth': 108.0, 'intl': 104.0, 'intc': 105.0, 'v': '2000'},
            ]
        }
    }


@pytest.fixture
def mock_positions():
    """Strict mock positions data - no live fallback."""
    return {
        'positions': [],
        'count': 0,
    }