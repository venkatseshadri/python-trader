import unittest
from unittest.mock import MagicMock, patch
from orbiter.core.broker.resolver import ContractResolver

class TestResolverSegmentIsolation(unittest.TestCase):
    def test_select_expiry_mcx_only_refreshes_mcx(self):
        """CRITICAL: Prove that an MCX symbol refresh does NOT trigger NFO download"""
        mock_master = MagicMock()
        mock_master.DERIVATIVE_OPTIONS = [] # Simulate empty master
        mock_master.DERIVATIVE_LOADED = False
        mock_master._last_refresh_time = 0 # Initialize with integer
        resolver = ContractResolver(mock_master)
        
        # Mock _time.time to bypass the 5-minute limit
        with patch('orbiter.core.broker.resolver._time.time', return_value=2000000000):
            # Try to select expiry for an MCX instrument (FUTCOM or OPTCOM)
            # Use 'OPTCOM' which is currently handled, and 'FUTCOM' which is failing
            resolver._select_expiry('CRUDEOIL', 'monthly', 'FUTCOM')
            
            # VERIFY: Should have called download_scrip_master with 'MCX'
            # FAILURE CASE: It was previously defaulting to 'NFO'
            mock_master.download_scrip_master.assert_any_call('MCX')
            
            # Ensure NFO was NEVER called
            for call in mock_master.download_scrip_master.call_args_list:
                self.assertNotEqual(call[0][0], 'NFO', "NFO master was incorrectly refreshed during MCX failure!")

if __name__ == "__main__":
    unittest.main()
