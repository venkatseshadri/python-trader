import pytest
from core.broker.master.base import BaseParser
import datetime

def test_parse_expiry_date():
    parser = BaseParser()
    assert parser.parse_expiry_date("14-Feb-2026") == datetime.date(2026, 2, 14)
    assert parser.parse_expiry_date("14-02-2026") == datetime.date(2026, 2, 14)
    assert parser.parse_expiry_date("2026-02-14") == datetime.date(2026, 2, 14)
    assert parser.parse_expiry_date("") is None
    assert parser.parse_expiry_date("invalid") is None

def test_get_col_idx():
    headers = ["Symbol", "Token", "Expiry"]
    parser = BaseParser()
    assert parser.get_col_idx(headers, "Symbol") == 0
    assert parser.get_col_idx(headers, "Expiry") == 2
    assert parser.get_col_idx(headers, "Price") is None
