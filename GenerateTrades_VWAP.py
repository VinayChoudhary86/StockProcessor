# GenerateTrades.py

import os
import math
import warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from config_loader import load_config  # type: ignore

# --- Load config ONCE ---
cfg = load_config()

TARGET_DIR = cfg["TARGET_DIRECTORY"]
INVESTMENT_AMOUNT = cfg["INVESTMENT_AMOUNT"]

# --- OI THRESHOLD CONSTANTS (Kept for compatibility, but now ignored for trading) ---
DIFFERENCE_THRESHOLD_PCT_INI = cfg["DIFFERENCE_THRESHOLD_PCT"]
DIFFERENCE_THRESHOLD_PCT = DIFFERENCE_THRESHOLD_PCT_INI / 100.0
SYMBOL = cfg["SYMBOL"]

# --- VWAP & RISK MANAGEMENT CONSTANTS (LOADED FROM CONFIG) ---
VWAP_ENTRY_THRESHOLD_PCT_INI = cfg.get("VWAP_ENTRY_THRESHOLD_PCT", 0.5)
# STOP LOSS AND TAKE PROFIT ARE NOW LOADED FROM CONFIG
STOP_LOSS_PCT_INI = cfg.get("STOP_LOSS_PCT", 15) 
TAKE_PROFIT_PCT_INI = cfg.get("TAKE_PROFIT_PCT", 50) # UPDATED default to 30.0


ANALYSIS_FILE_NAME = f"{SYMBOL}_Analysis.csv"
INPUT_FILE = os.path.join(TARGET_DIR, ANALYSIS_FILE_NAME)
OUTPUT_FILE = os.path.join(TARGET_DIR, f"{SYMBOL}_Trades.csv")

DATE_COL = 'DATE'
CLOSE_COL = 'close'
LONG_TILL_NOW_COL = 'Longs Till Now'
SHORT_TILL_NOW_COL = 'Shorts Till Now'
OI_SUM_COL = 'Daily_Open_Interest_Sum'
TRADE_SIGNAL_COL = 'Trade_Signal'


# ------------------------------------------------------------------------------------
# CLEANING FUNCTION
# ------------------------------------------------------------------------------------
def clean_data(df):
    """Clean and ensure necessary columns are numeric and filled."""
    required_cols = [LONG_TILL_NOW_COL, SHORT_TILL_NOW_COL, OI_SUM_COL, CLOSE_COL, TRADE_SIGNAL_COL]
    
    optional_numeric_cols = ['vwap']

    df.columns = df.columns.str.strip()

    # Clean required columns
    for col in required_cols:
        if col in df.columns:
            if col in [LONG_TILL_NOW_COL, SHORT_TILL_NOW_COL, OI_SUM_COL, CLOSE_COL]:
                # Robust cleaning for numeric columns
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce').fillna(0)
            elif col == TRADE_SIGNAL_COL:
                 # Clean and standardize the Trade_Signal column
                 df[col] = df[col].astype(str).str.upper().str.strip().replace({'NAN': 'HOLD', 'NONE': 'HOLD'}, regex=False)
        else:
            if col == TRADE_SIGNAL_COL:
                warnings.warn(f"'{TRADE_SIGNAL_COL}' column not found. Defaulting to 'HOLD'.")
                df[col] = 'HOLD'
            else:
                 raise KeyError(f"Required column not found: '{col}'.")


    # Clean optional numeric columns
    for col in optional_numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce').fillna(method='ffill')

    # Ensure critical numeric columns are not NaN
    df.dropna(subset=[OI_SUM_COL, LONG_TILL_NOW_COL, SHORT_TILL_NOW_COL, CLOSE_COL], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


# ------------------------------------------------------------------------------------
# MINIMUM OI
# ------------------------------------------------------------------------------------
def calculate_dynamic_min_oi(df):
    if df[OI_SUM_COL].empty:
        return 0

    min_oi = df[OI_SUM_COL].quantile(0.25)
    if min_oi == 0:
        warnings.warn("MIN_OI is 0, setting to 1.")
        return 1

    return int(min_oi)


# ------------------------------------------------------------------------------------
# SIGNAL GENERATION
# ------------------------------------------------------------------------------------
def generate_signals(df, threshold_pct, min_oi_sum):
    df['Net_Position_Change'] = df[LONG_TILL_NOW_COL] - df[SHORT_TILL_NOW_COL]
    df['Signal_Threshold_Value'] = 0.0
    df['LTN_Prev'] = df[LONG_TILL_NOW_COL].shift(1).fillna(0)
    df['STN_Prev'] = df[SHORT_TILL_NOW_COL].shift(1).fillna(0)
    df['Signal'] = 'HOLD' 
    return df


# ------------------------------------------------------------------------------------
# TRADE SIMULATION (PURE VWAP & FIXED SL/TP)
# ------------------------------------------------------------------------------------
def simulate_trades(df, investment_amount):

    df['Quantity_Traded'] = 0
    df['Position'] = 0
    df['Daily_PnL'] = 0.0
    
    # State tracking columns
    df['Entry_Price'] = 0.0
    df['Entry_Type'] = None 

    # Convert percentage values from config to decimal for calculations
    VWAP_ENTRY_THRESHOLD_DEC = VWAP_ENTRY_THRESHOLD_PCT_INI / 100.0 
    
    # Fixed SL/TP percentages loaded from config and converted to decimal
    STOP_LOSS_PCT = STOP_LOSS_PCT_INI / 100.0 
    TAKE_PROFIT_PCT = TAKE_PROFIT_PCT_INI / 100.0 

    for i in range(1, len(df)):
        current_price = df.loc[i, CLOSE_COL]
        previous_price = df.loc[i - 1, CLOSE_COL]

        # Restore state from previous day
        position = df.loc[i - 1, 'Position'] 
        entry_price_prev = df.loc[i - 1, 'Entry_Price']
        
        # Carry forward the entry state by default
        df.loc[i, 'Entry_Price'] = entry_price_prev
        df.loc[i, 'Entry_Type'] = df.loc[i - 1, 'Entry_Type']
        
        # Calculate PnL based on the position held from the previous day
        df.loc[i, 'Daily_PnL'] = (current_price - previous_price) * position

        net_trade_qty = 0
        current_position = position
        calculated_trade_qty = math.floor(investment_amount / current_price) if current_price > 0 else 0
        vwap = df.loc[i, 'vwap'] if 'vwap' in df.columns else None

        # ------------------------------------------------------------------
        # COMBINED EXIT/ENTRY LOGIC
        # ------------------------------------------------------------------
        
        is_exiting = False
        
        # --- 1. EXIT LOGIC (SL/TP - Highest Priority) ---
        if current_position != 0 and entry_price_prev > 0:
            
            # Stop Loss (SL) and Take Profit (TP) calculations
            sl_price_long = entry_price_prev * (1 - STOP_LOSS_PCT)
            tp_price_long = entry_price_prev * (1 + TAKE_PROFIT_PCT)

            if current_position > 0: # Long position exit check
                if current_price < sl_price_long:
                    # Stop Loss
                    net_trade_qty = -current_position
                    is_exiting = True
                elif current_price > tp_price_long:
                    # Take Profit
                    net_trade_qty = -current_position
                    is_exiting = True
            
            # NOTE: Short position exit logic removed, as only long trades are taken.

        # --- FINAL POSITION/STATE UPDATE AFTER EXITS ---
        if is_exiting:
            position = 0 
            df.loc[i, 'Entry_Price'] = 0.0
            df.loc[i, 'Entry_Type'] = None # Reset state
        
        # --- 2. ENTRY LOGIC (Only if position is flat - PURE VWAP SUPPORT: LONG ONLY) ---
        
        elif current_position == 0:
            
            if vwap and vwap > 0:
                vwap_diff = current_price - vwap
                vwap_diff_pct = abs(vwap_diff) / vwap

                # VWAP Buy Entry (Price near VWAP and below it = Support)
                is_vwap_support_buy = (vwap_diff < 0) and (vwap_diff_pct <= VWAP_ENTRY_THRESHOLD_DEC)

                # VWAP Sell Entry (Price near VWAP and above it = Resistance) - REMOVED

                if is_vwap_support_buy:
                    net_trade_qty = calculated_trade_qty
                    position += calculated_trade_qty
                    df.loc[i, 'Entry_Price'] = current_price
                    df.loc[i, 'Entry_Type'] = 'VWAP'
                
                # elif is_vwap_resistance_sell: # Logic for short entry is removed.
                #     ...

        # ------------------------------------------------------------------

        # Update the DataFrame for the current row 'i'
        df.loc[i, 'Quantity_Traded'] = net_trade_qty
        df.loc[i, 'Position'] = position

    df['Cumulative_PnL'] = df['Daily_PnL'].cumsum()
    return df


# ------------------------------------------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------------------------------------------
def run_pipeline():
    print(f"--- F&O Trade Strategy Backtester ---")
    print(f"Input Data: {INPUT_FILE}")

    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found.")
        return

    df = pd.read_csv(INPUT_FILE, thousands=',')

    df_clean = clean_data(df.copy()) 
    if df_clean.empty:
        print("ERROR: Data empty after cleaning.")
        return

    min_oi = calculate_dynamic_min_oi(df_clean)
    if min_oi == 0:
        print("ERROR: OI threshold invalid.")
        return

    df_signals = generate_signals(df_clean, DIFFERENCE_THRESHOLD_PCT, min_oi)
    df_trades = simulate_trades(df_signals, INVESTMENT_AMOUNT)

    output_cols = [
        DATE_COL, CLOSE_COL, 'vwap',
        LONG_TILL_NOW_COL, SHORT_TILL_NOW_COL,
        OI_SUM_COL, 'Net_Position_Change', 'Signal_Threshold_Value',
        TRADE_SIGNAL_COL, 
        'Signal', 'Quantity_Traded', 'Position', 
        'Entry_Price', 'Entry_Type', 
        'Daily_PnL', 'Cumulative_PnL'
    ]

    # Filter output columns to only include those present in the final DataFrame
    df_trades[[c for c in output_cols if c in df_trades.columns]].to_csv(OUTPUT_FILE, index=False)

    print(f"\nSaved trade file: {OUTPUT_FILE}")
    print(f"Final PnL: {df_trades['Cumulative_PnL'].iloc[-1]:,.2f}")


if __name__ == "__main__":
    run_pipeline()