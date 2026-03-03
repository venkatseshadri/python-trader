"""
Tests for Multi-Broker Support
=============================
Tests Shoonya, Flattrade, and Simulation broker configurations
"""
import unittest
import sys
import os
import tempfile
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from broker_config import (
    get_broker_config,
    is_simulation_mode,
    BROKER_ENDPOINTS,
    DEFAULT_BROKER
)
from api_helper import ShoonyaApiPy, FlattradeApiPy, Order


class TestBrokerConfig(unittest.TestCase):
    """Test broker configuration module"""
    
    def test_get_shoonya_config(self):
        config = get_broker_config("shoonya")
        self.assertEqual(config["name"], "Shoonya (Finvasia)")
        self.assertIn("api.shoonya.com", config["rest"])
        self.assertIn("api.shoonya.com", config["websocket"])
    
    def test_get_flattrade_config(self):
        config = get_broker_config("flattrade")
        self.assertEqual(config["name"], "Flattrade")
        self.assertIn("pi.flattrade.in", config["rest"])
        self.assertIn("pi.flattrade.in", config["websocket"])
    
    def test_get_simulation_config(self):
        config = get_broker_config("simulation")
        self.assertEqual(config["name"], "Simulation Mode")
        self.assertIsNone(config["rest"])
        self.assertIsNone(config["websocket"])
    
    def test_default_broker(self):
        config = get_broker_config(None)
        self.assertEqual(config["name"], "Shoonya (Finvasia)")
    
    def test_invalid_broker_raises_error(self):
        with self.assertRaises(ValueError):
            get_broker_config("invalid_broker")
    
    def test_broker_case_insensitive(self):
        config1 = get_broker_config("SHOONYA")
        config2 = get_broker_config("shoonya")
        config3 = get_broker_config("Shoonya")
        self.assertEqual(config1, config2)
        self.assertEqual(config2, config3)


class TestSimulationMode(unittest.TestCase):
    """Test simulation mode detection"""
    
    def test_simulation_mode_detection(self):
        self.assertTrue(is_simulation_mode("simulation"))
        self.assertTrue(is_simulation_mode("SIMULATION"))
        self.assertTrue(is_simulation_mode("Simulation"))
    
    def test_shoonya_not_simulation(self):
        self.assertFalse(is_simulation_mode("shoonya"))
        self.assertFalse(is_simulation_mode("SHOONYA"))
    
    def test_flattrade_not_simulation(self):
        self.assertFalse(is_simulation_mode("flattrade"))
        self.assertFalse(is_simulation_mode("FLATTRADE"))


class TestBrokerEndpoints(unittest.TestCase):
    """Test that all brokers have required fields"""
    
    def test_all_brokers_have_required_fields(self):
        for broker, config in BROKER_ENDPOINTS.items():
            self.assertIn("name", config, "Missing 'name' for {}".format(broker))
            self.assertIn("rest", config, "Missing 'rest' for {}".format(broker))
            self.assertIn("websocket", config, "Missing 'websocket' for {}".format(broker))
            self.assertIn("broker_code", config, "Missing 'broker_code' for {}".format(broker))


class TestShoonyaApiPy(unittest.TestCase):
    """Test Shoonya API wrapper"""
    
    def test_shoonya_api_initialization(self):
        api = ShoonyaApiPy(broker="shoonya")
        self.assertEqual(api.broker, "shoonya")
        self.assertEqual(api.broker_name, "Shoonya (Finvasia)")
        self.assertFalse(api.is_simulation)
        self.assertIn("api.shoonya.com", api.host)
    
    def test_flattrade_api_initialization(self):
        api = ShoonyaApiPy(broker="flattrade")
        self.assertEqual(api.broker, "flattrade")
        self.assertEqual(api.broker_name, "Flattrade")
        self.assertFalse(api.is_simulation)
        self.assertIn("pi.flattrade.in", api.host)
    
    def test_simulation_api_initialization(self):
        api = ShoonyaApiPy(broker="simulation")
        self.assertEqual(api.broker, "simulation")
        self.assertEqual(api.broker_name, "Simulation Mode")
        self.assertTrue(api.is_simulation)
        self.assertIsNone(api.host)
    
    def test_simulation_get_funds(self):
        api = ShoonyaApiPy(broker="simulation")
        funds = api.get_funds()
        self.assertEqual(funds["stat"], "Ok")
        self.assertEqual(funds["cash"], "100000")
        self.assertEqual(funds["mode"], "SIMULATION")
    
    def test_simulation_get_positions(self):
        api = ShoonyaApiPy(broker="simulation")
        positions = api.get_positions()
        self.assertEqual(positions, [])
    
    def test_simulation_get_order_history(self):
        api = ShoonyaApiPy(broker="simulation")
        history = api.get_order_history()
        self.assertEqual(history, [])


class TestFlattradeApiPy(unittest.TestCase):
    """Test Flattrade API wrapper"""
    
    def test_flattrade_api(self):
        api = FlattradeApiPy()
        self.assertEqual(api.broker, "flattrade")
        self.assertFalse(api.is_simulation)


class TestOrderClass(unittest.TestCase):
    """Test Order class"""
    
    def test_order_creation(self):
        order = Order(
            buy_or_sell="BUY",
            product_type="I",
            exchange="NSE",
            tradingsymbol="RELIANCE",
            price_type="L",
            quantity=10,
            price=2500.00
        )
        self.assertEqual(order.buy_or_sell, "BUY")
        self.assertEqual(order.product_type, "I")
        self.assertEqual(order.exchange, "NSE")
        self.assertEqual(order.tradingsymbol, "RELIANCE")
        self.assertEqual(order.price_type, "L")
        self.assertEqual(order.quantity, 10)
        self.assertEqual(order.price, 2500.00)


class TestCredFileBrokerSelection(unittest.TestCase):
    """Test broker selection from cred file"""
    
    def test_load_broker_from_creds(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({
                'broker': 'flattrade',
                'user': 'test_user',
                'pwd': 'test_pass'
            }, f)
            cred_file = f.name
        
        try:
            api = ShoonyaApiPy(cred_file=cred_file)
            self.assertEqual(api.broker, 'flattrade')
        finally:
            os.unlink(cred_file)
    
    def test_default_to_shoonya_when_missing(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({
                'user': 'test_user',
                'pwd': 'test_pass'
            }, f)
            cred_file = f.name
        
        try:
            api = ShoonyaApiPy(cred_file=cred_file)
            self.assertEqual(api.broker, 'shoonya')
        finally:
            os.unlink(cred_file)


if __name__ == "__main__":
    unittest.main(verbosity=2)
