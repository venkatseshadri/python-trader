import datetime
from typing import Optional

class BaseParser:
    @staticmethod
    def parse_expiry_date(raw: str) -> Optional[datetime.date]:
        if not raw: return None
        for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try: return datetime.datetime.strptime(raw, fmt).date()
            except ValueError: continue
        return None

    @staticmethod
    def get_col_idx(headers, name: str) -> Optional[int]:
        return headers.index(name) if name in headers else None
