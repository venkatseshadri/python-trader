import unittest
from unittest.mock import MagicMock, patch
from orbiter.bot.sheets import log_scan_metrics, log_buy_signals
import datetime

class TestSheetsLogic(unittest.TestCase):

    @patch('orbiter.bot.sheets.Credentials')
    @patch('orbiter.bot.sheets.gspread.authorize')
    def test_log_scan_metrics_nfo_vs_mcx(self, mock_authorize, mock_creds):
        # Setup Mock Sheet
        mock_client = mock_authorize.return_value
        mock_book = mock_client.open.return_value
        mock_sheet = MagicMock()
        mock_book.worksheet.return_value = mock_sheet
        
        # Use ACTUAL header from sheets.py
        mock_sheet.row_values.return_value = SCAN_METRICS_HEADER
        mock_sheet.get_all_values.return_value = [SCAN_METRICS_HEADER]

        # 1. Prepare Mix of NFO and MCX Metrics
        metrics = [
            {
                'token': 'NFO|59346',
                'symbol': 'HDFCLIFE24FEB26F',
                'company_name': 'HDFCLIFE',
                'day_open': 600.0, 'day_high': 610.0, 'day_low': 590.0, 'day_close': 605.0, 'ltp': 608.0,
                'filters': {'ef1_orb': {'score': 5.0, 'orb_open': 600.0}},
                'span_pe': {'span': 150000.0, 'ok': True},
                'span_ce': {'span': 145000.0, 'ok': True},
                'trade_taken': False
            },
            {
                'token': 'MCX|467013',
                'symbol': 'CRUDEOIL19FEB26',
                'company_name': 'CRUDEOIL',
                'day_open': 5700.0, 'day_high': 5800.0, 'day_low': 5650.0, 'day_close': 5750.0, 'ltp': 5790.0,
                'filters': {'ef1_orb': {'score': 7.5, 'orb_open': 5700.0}},
                'span_pe': {'ok': False}, # MCX doesn't have PE/CE spreads in same way
                'span_ce': {'ok': False},
                'trade_taken': True
            }
        ]

        # 2. Execute
        log_scan_metrics(metrics, tab_name="scan_metrics_mcx")

        # 3. Verify
        # Check if the worksheet was opened with the correct name
        mock_book.worksheet.assert_called_with("scan_metrics_mcx")
        mock_sheet.append_rows.assert_called_once()
        rows = mock_sheet.append_rows.call_args[0][0]
        
        nfo_row = rows[0]
        mcx_row = rows[1]

        # Check NFO SPAN PE (should be index 4 based on header mock)
        self.assertEqual(nfo_row[header_idx(mock_sheet, "SPAN PE")], "₹150000.00")
        self.assertEqual(nfo_row[header_idx(mock_sheet, "Symbol")], "HDFCLIFE24FEB26F")

        # Check MCX Symbol and Trade Taken
        self.assertEqual(mcx_row[header_idx(mock_sheet, "Symbol")], "CRUDEOIL19FEB26")
        self.assertEqual(mcx_row[header_idx(mock_sheet, "Trade Taken")], "YES")

    @patch('orbiter.bot.sheets.Credentials')
    @patch('orbiter.bot.sheets.gspread.authorize')
    def test_log_buy_signals_nfo_vs_mcx(self, mock_authorize, mock_creds):
        # Setup Mock Sheet
        mock_client = mock_authorize.return_value
        mock_book = mock_client.open.return_value
        mock_sheet = MagicMock()
        mock_book.worksheet.return_value = mock_sheet
        
        # 1. Prepare Signals
        signals = [
            {
                'token': 'NFO|12345', 'symbol': 'RELIANCE24FEB26F', 'company_name': 'RELIANCE',
                'ltp': 2500.0, 'score': 45.5, 'strategy': 'PUT_CREDIT_SPREAD',
                'atm_symbol': 'REL2500PE', 'hedge_symbol': 'REL2400PE',
                'atm_premium_entry': 20.0, 'hedge_premium_entry': 5.0,
                'total_margin': 150000.0
            },
            {
                'token': 'MCX|467013', 'symbol': 'CRUDEOIL19FEB26', 'company_name': 'CRUDEOIL',
                'ltp': 5700.0, 'score': 50.0, 'strategy': 'FUTURE_LONG',
                'lot_size': 100, 'total_margin': 380000.0
            }
        ]

        # 2. Execute
        log_buy_signals(signals)

        # 3. Verify
        mock_sheet.append_rows.assert_called_once()
        rows = mock_sheet.append_rows.call_args[0][0]
        
        nfo_row = rows[0]
        mcx_row = rows[1]

        # NFO: Check strategy and ATM symbol
        self.assertEqual(nfo_row[TRADE_LOG_HEADER.index("Strategy")], "PUT_CREDIT_SPREAD")
        self.assertEqual(nfo_row[TRADE_LOG_HEADER.index("ATM Symbol")], "REL2500PE")

        # MCX: Check strategy and ensure ATM symbol is empty
        self.assertEqual(mcx_row[TRADE_LOG_HEADER.index("Strategy")], "FUTURE_LONG")
        self.assertEqual(mcx_row[TRADE_LOG_HEADER.index("ATM Symbol")], "")
        self.assertEqual(mcx_row[TRADE_LOG_HEADER.index("Total Margin")], "₹380000.00")

def header_idx(mock_sheet, name):
    # This is a helper for the scan_metrics test
    header = mock_sheet.row_values(1)
    return header.index(name)

from orbiter.bot.sheets import TRADE_LOG_HEADER, SCAN_METRICS_HEADER

if __name__ == '__main__':
    unittest.main()
