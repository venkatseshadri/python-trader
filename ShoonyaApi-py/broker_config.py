"""
Broker Configuration Module
==========================
Supports multiple brokers: Shoonya, Flattrade, Simulation

Usage in cred.yml:
------------------
# For Shoonya:
broker: shoonya
user: YOUR_USER
...

# For Flattrade:
broker: flattrade
user: YOUR_USER
...

# For Simulation (paper trading without API):
broker: simulation
"""

BROKER_ENDPOINTS = {
    'shoonya': {
        'name': 'Shoonya (Finvasia)',
        'rest': 'https://api.shoonya.com/NorenWClientTP/',
        'websocket': 'wss://api.shoonya.com/NorenWSTP/',
        'broker_code': 'shoonya'
    },
    'flattrade': {
        'name': 'Flattrade',
        'rest': 'https://pi.flattrade.in/NorenWClientTP/',
        'websocket': 'wss://pi.flattrade.in/NorenWSTP/',
        'broker_code': 'flattrade'
    },
    'simulation': {
        'name': 'Simulation Mode',
        'rest': None,
        'websocket': None,
        'broker_code': 'simulation'
    }
}

DEFAULT_BROKER = 'shoonya'

def get_broker_config(broker_name=None):
    """Get broker configuration by name"""
    if not broker_name:
        broker_name = DEFAULT_BROKER
    
    broker_name = broker_name.lower().strip()
    
    if broker_name not in BROKER_ENDPOINTS:
        raise ValueError(f"Unknown broker: {broker_name}. Available: {list(BROKER_ENDPOINTS.keys())}")
    
    return BROKER_ENDPOINTS[broker_name]

def is_simulation_mode(broker_name):
    """Check if running in simulation mode"""
    return broker_name.lower().strip() == 'simulation'
