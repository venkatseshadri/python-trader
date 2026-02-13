from typing import Dict, Any, List

class MarginCalculator:
    def __init__(self, scrip_master):
        self.master = scrip_master

    def calculate_span_for_spread(self, spread: Dict[str, Any], api, actid, product_type: str = "I", haircut: float = 0.20) -> Dict[str, Any]:
        """Calculate margin for a 2-leg spread"""
        def get_row(tsym):
            for row in self.master.DERIVATIVE_OPTIONS:
                if row.get('tradingsymbol') == tsym: return row
            return None

        atm_row, hedge_row = get_row(spread.get('atm_symbol')), get_row(spread.get('hedge_symbol'))
        if not atm_row or not hedge_row: return {'ok': False, 'reason': 'option_symbol_not_found'}

        def format_date(raw):
            try:
                from datetime import datetime
                return datetime.strptime(raw, "%Y-%m-%d").strftime("%d-%b-%Y").upper()
            except Exception: return str(raw)

        def make_pos(row, side):
            qty = int(spread.get('lot_size', 0))
            inst = row.get('instrument') or "OPTSTK"
            exch = "MCX" if inst in ("OPTCOM", "FUTCOM") else "NFO"
            return {
                "prd": "M" if product_type == "I" else product_type,
                "exch": exch, "instname": inst, "symname": row.get('symbol'),
                "exd": format_date(row.get('expiry')), "optt": row.get('option_type'),
                "strprc": f"{float(row.get('strike', 0)):.2f}",
                "buyqty": str(qty) if side == "B" else "0",
                "sellqty": str(qty) if side == "S" else "0",
                "netqty": str(qty) if side == "B" else str(-qty)
            }

        positionlist = [make_pos(hedge_row, "B"), make_pos(atm_row, "S")]
        try:
            ret = api.span_calculator(actid, positionlist)
            if not isinstance(ret, dict) or ret.get('stat') != 'Ok':
                return {'ok': False, 'reason': f"span_err:{ret.get('emsg', 'unknown')}"}
            
            span, expo = float(ret.get('span', 0.0)), float(ret.get('expo', 0.0))
            if span == 0 and expo == 0: return {'ok': False, 'reason': 'span_zero'}
            
            total = span + expo
            return {
                'ok': True, 'span': span, 'expo': expo, 'total_margin': total, 'haircut': haircut,
                'pledged_required': total / (1.0 - haircut),
                'span_trade': float(ret.get('span_trade', 0.0)), 'expo_trade': float(ret.get('expo_trade', 0.0)),
                'pre_trade': float(ret.get('pre_trade', 0.0)), 'add': float(ret.get('add', 0.0)),
                'add_trade': float(ret.get('add_trade', 0.0)), 'ten': float(ret.get('ten', 0.0)),
                'ten_trade': float(ret.get('ten_trade', 0.0)), 'del': float(ret.get('del', 0.0)),
                'del_trade': float(ret.get('del_trade', 0.0)), 'spl': float(ret.get('spl', 0.0)),
                'spl_trade': float(ret.get('spl_trade', 0.0))
            }
        except Exception as e: return {'ok': False, 'reason': f'span_exception:{e}'}

    def calculate_future_margin(self, future_details: Dict[str, Any], api, actid, product_type: str = "I", haircut: float = 0.20) -> Dict[str, Any]:
        """Calculate margin for a single future contract"""
        def get_row(tsym):
            for row in self.master.DERIVATIVE_OPTIONS:
                if row.get('tradingsymbol') == tsym: return row
            return None

        row = get_row(future_details.get('tsym'))
        if not row: return {'ok': False, 'reason': 'future_symbol_not_found'}

        def format_date(raw):
            try:
                from datetime import datetime
                return datetime.strptime(raw, "%Y-%m-%d").strftime("%d-%b-%Y").upper()
            except Exception: return str(raw)

        def make_pos(row, side):
            qty = int(future_details.get('lot_size', 0))
            inst = row.get('instrument') or "FUTSTK"
            exch = "MCX" if inst in ("OPTCOM", "FUTCOM") else "NFO"
            return {
                "prd": "M" if product_type == "I" else product_type,
                "exch": exch, "instname": inst, "symname": row.get('symbol'),
                "exd": format_date(row.get('expiry')), "optt": "XX",
                "strprc": "0.00",
                "buyqty": str(qty) if side == "B" else "0",
                "sellqty": str(qty) if side == "S" else "0",
                "netqty": str(qty) if side == "B" else str(-qty)
            }

        positionlist = [make_pos(row, "B")]
        try:
            ret = api.span_calculator(actid, positionlist)
            if not isinstance(ret, dict) or ret.get('stat') != 'Ok':
                return {'ok': False, 'reason': f"span_err:{ret.get('emsg', 'unknown')}"}
            
            span, expo = float(ret.get('span', 0.0)), float(ret.get('expo', 0.0))
            total = span + expo
            return {
                'ok': True, 'span': span, 'expo': expo, 'total_margin': total, 'haircut': haircut,
                'pledged_required': total / (1.0 - haircut)
            }
        except Exception as e: return {'ok': False, 'reason': f'span_exception:{e}'}
