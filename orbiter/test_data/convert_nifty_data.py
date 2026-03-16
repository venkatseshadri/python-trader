#!/usr/bin/env python3
"""
Convert Nifty intraday CSV data to mock broker JSON format

Usage:
    python convert_nifty_data.py --input /home/trading_ceo/python-trader/nifty_data --output orbiter/test_data/nifty_full.json
"""
import os
import sys
import json
import argparse
from pathlib import Path

# Map of Nifty 50 symbols to their tokens (from Shoonya/NSE)
# These are the tokens used in the strategy's instruments.json
SYMBOL_TOKEN_MAP = {
    'NIFTY 50': '26000',
    'NIFTY BANK': '26009',
    'NIFTY': '26000',
    'BANKNIFTY': '26009',
    'RELIANCE': '2885',
    'INFY': '1594',
    'HDFCBANK': '1333',
    'SBIN': '24524',
    'BAJFINANCE': '317',
    'TCS': '11536',
    'ICICIBANK': '4963',
    'KOTAKBANK': '1922',
    'LT': '18564',
    'ITC': '29251',
    'HINDUNILVR': '1394',
    'MARUTI': '10999',
    'ASIANPAINT': '236',
    'AXISBANK': '5900',
    'M&M': '13285',
    'WIPRO': '3787',
    'TITAN': '3506',
    'TATAMOTORS': '3456',
    'BPCL': '526',
    'COALINDIA': '20374',
    'DRREDDY': '881',
    'GRASIM': '1232',
    'HCLTECH': '7229',
    'HINDALCO': '1363',
    'IOC': '1624',
    'NTPC': '27176',
    'POWERGRID': '14977',
    'ADANIPORTS': '15083',
    'UPL': '11287',
    'DLF': '14732',
    'JSWSTEEL': '11723',
    'BHARTIARTL': '10604',
    'BAJAJHLDNG': '16675',
    'BAJAJFINSV': '16675',
    'CIPLA': '25076',
    'AMBUJCEM': '26720',
    'VEDL': '472894',
    'SHREECEM': '31048',
    'HDFCLIFE': '467',
    'ADANIENT': '11287',
    'ADANIGREEN': '47170',
    'ADANIENSOL': '475184',
    'ADANIPOWER': '12096',
    'BEL': '28176',
    'BOSCHLTD': '6006',
    'BRITANNIA': '54798',
    'CANBK': '10242',
    'CHOLAFIN': '20269',
    'DABUR': '29568',
    'GAIL': '4717',
    'Godrej Consumer': '34992',
    'INDUSINDBK': '40816',
    'Jindal Steel': '应激504',
    'LIC': '30428',
    'MARICO': '29503',
    'Nestle': '27968',
    'ONGC': '2475',
    'Petronet': '30952',
    'SBILIFE': '34066',
    'Sun Pharma': '37569',
    'Tata Steel': '30385',
    'Tech Mahindra': '33841',
    'Unitdspr': '11184',
    'VBL': '37188',
    'ZYDUSLIFE': '38143',
    'BANKBARODA': '54346',
    'EICHERMOT': '910',
    'APOLLOHOSP': '15760',
    'ATGL': '47190',
}


def convert_csv_to_candles(csv_path, symbol_name, limit=None):
    """Convert a CSV file to candle format - optimized"""
    candles = []
    
    try:
        with open(csv_path, 'r') as f:
            next(f)  # Skip header
            
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break
                    
                parts = line.strip().split(',')
                if len(parts) < 6:
                    continue
                
                date_str = parts[0]  # "2015-02-02 09:15:00"
                
                # Quick filter: only include market hours (9:15 - 15:30)
                # Format: "2015-02-02 09:15:00" - check 12th and 13th chars
                if len(date_str) >= 14:
                    hour = int(date_str[11:13])
                    minute = int(date_str[14:16])
                    if hour < 9 or (hour == 15 and minute > 30) or hour > 15:
                        continue
                
                candles.append({
                    'time': date_str,
                    'into': parts[1],
                    'inth': parts[2],
                    'intl': parts[3],
                    'intc': parts[4],
                    'intv': parts[5],
                    'oi': '0'
                })
    
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
    
    return candles


def main():
    parser = argparse.ArgumentParser(description='Convert Nifty CSV data to mock broker JSON')
    parser.add_argument('--input', '-i', required=True, help='Input directory with CSV files')
    parser.add_argument('--output', '-o', default='orbiter/test_data/nifty_full.json', help='Output JSON file')
    parser.add_argument('--limit', '-l', type=int, default=None, help='Limit number of candles per symbol (for testing)')
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_file = Path(args.output)
    
    print(f"Scanning {input_dir}...")
    
    result = {}
    csv_files = list(input_dir.glob("*_minute.csv"))
    print(f"Found {len(csv_files)} CSV files")
    
    for csv_file in csv_files:
        # Extract symbol name (e.g., "RELIANCE" from "RELIANCE_minute.csv")
        symbol = csv_file.stem.replace('_minute', '')
        
        # Get token (use symbol as token if not in map)
        token = SYMBOL_TOKEN_MAP.get(symbol, symbol)
        
        print(f"Converting {symbol} (token: {token})...", end=" ")
        
        candles = convert_csv_to_candles(csv_file, symbol, limit=args.limit)
        
        if candles:
            # Create key as "NSE_SYMBOL"
            key = f"NSE_{symbol}"
            result[key] = {
                'symbol': symbol,
                'token': token,
                'exchange': 'NSE',
                'candles': candles
            }
            print(f"{len(candles)} candles")
        else:
            print("no data")
    
    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✅ Saved {len(result)} instruments to {output_file}")
    
    # Print summary
    total_candles = sum(len(v['candles']) for v in result.values())
    print(f"Total candles: {total_candles:,}")


if __name__ == '__main__':
    main()
