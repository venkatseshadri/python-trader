import unittest
from unittest.mock import MagicMock
from orbiter.core.broker.resolver import ContractResolver
import datetime

class TestResolver(unittest.TestCase):
    def setUp(self):
        # Create a mock ScripMaster
        self.master = MagicMock()
        # Mock DERIVATIVE_OPTIONS as a plain list
        self.master.DERIVATIVE_OPTIONS = []
        self.master.DERIVATIVE_LOADED = True
        self.master._parse_expiry_date = lambda x: datetime.date.fromisoformat(x) if x else None
        
        self.resolver = ContractResolver(self.master)

    def test_import_stability(self):
        """Verify that _select_expiry doesn't crash due to missing imports (like 'time')"""
        try:
            # This should call select_expiry and not crash on 'time.time()'
            res = self.resolver._select_expiry("CRUDEOIL", "monthly", "OPTCOM")
            self.assertIsNone(res)
        except NameError as e:
            self.fail(f"Resolver crashed with NameError: {e}")
        except Exception:
            pass

    def test_last_thursday_logic(self):
        """Verify the Thursday detection logic used for monthly expiry"""
        # Feb 26, 2026 is a Thursday
        d = datetime.date(2026, 2, 26)
        self.assertTrue(self.resolver._is_last_thursday(d))
        
        # Feb 19, 2026 is a Thursday but not the LAST one
        d2 = datetime.date(2026, 2, 19)
        self.assertFalse(self.resolver._is_last_thursday(d2))

if __name__ == "__main__":
    unittest.main()
