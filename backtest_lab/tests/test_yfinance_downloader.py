import unittest
import os
import shutil
from python.backtest_lab.tools.yfinance_downloader import download_data

class TestYfinanceDownloader(unittest.TestCase):
    def setUp(self):
        self.test_output_dir = "python/backtest_lab/data/test_yfinance"
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def tearDown(self):
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    def test_download_data_success(self):
        # Using 1d data for a small range to ensure it's always available
        ticker = "^NSEI"
        interval = "1d"
        start = "2026-02-01"
        end = "2026-02-05"
        
        download_data(ticker, interval, start, end, self.test_output_dir)
        
        # Check if file exists
        expected_filename = f"{ticker.replace('=', '_')}_{interval}_{start}_{end}.csv"
        expected_path = os.path.join(self.test_output_dir, expected_filename)
        
        self.assertTrue(os.path.exists(expected_path), f"File {expected_path} was not created.")
        
        # Check if file has content
        with open(expected_path, 'r') as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1, "CSV file is empty.")

if __name__ == "__main__":
    unittest.main()
