import pandas as pd
import os

def create_excel_report(trades_df, output_path):
    if trades_df.empty:
        print("⚠️ No trades to export to Excel.")
        return

    # Map internal columns to sample report columns
    # Internal: Time, Stock, Action, Price, PnL_Rs, Reason
    # Target: Instrument, underlying, expiry, instrument_type, strike, option_type, txn_type, condition_type, condition_category, entry_time, quantity, price, underlying_price, amount, type_of_position
    
    # We will create a simplified version that matches the spirit of the sample
    
    export_df = pd.DataFrame()
    
    # Assuming 'Stock' is the Underlying for now
    export_df['Instrument'] = trades_df['Stock'] 
    export_df['underlying'] = trades_df['Stock']
    export_df['txn_type'] = trades_df['Action'].apply(lambda x: 'BUY' if 'ENTRY' in x else 'SELL')
    export_df['entry_time'] = trades_df['Time']
    export_df['price'] = trades_df['Price']
    export_df['amount'] = trades_df.get('PnL_Rs', 0) # PnL is amount for Exit
    export_df['condition_category'] = trades_df.get('Reason', 'Normal')
    
    # Save
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Positions')
        
    print(f"✅ Excel Report Generated: {output_path}")
