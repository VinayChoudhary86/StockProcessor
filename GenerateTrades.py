# Trader_11.py

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
DIFFERENCE_THRESHOLD_PCT_INI = cfg["DIFFERENCE_THRESHOLD_PCT"]
DIFFERENCE_THRESHOLD_PCT = DIFFERENCE_THRESHOLD_PCT_INI / 100.0
SYMBOL = cfg["SYMBOL"]

ANALYSIS_FILE_NAME = f"{SYMBOL}_Analysis.csv"
INPUT_FILE = os.path.join(TARGET_DIR, ANALYSIS_FILE_NAME)
OUTPUT_FILE = os.path.join(TARGET_DIR, f"{SYMBOL}_Trades.csv")

DATE_COL = 'DATE'
CLOSE_COL = 'close'
LONG_TILL_NOW_COL = 'Longs Till Now'
SHORT_TILL_NOW_COL = 'Shorts Till Now'
OI_SUM_COL = 'Daily_Open_Interest_Sum'


# ------------------------------------------------------------------------------------
# CLEANING FUNCTION
# ------------------------------------------------------------------------------------
def clean_data(df):
    """Clean and ensure necessary columns are numeric and filled."""
    required_cols = [LONG_TILL_NOW_COL, SHORT_TILL_NOW_COL, OI_SUM_COL, CLOSE_COL]
    optional_numeric_cols = ['vwap']

    df.columns = df.columns.str.strip()

    # Clean required columns
    for col in required_cols:
        if col in df.columns:
            # Use pd.to_numeric with coerce for robust cleaning
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce').fillna(0)
        else:
            raise KeyError(f"Required column not found: '{col}'.")

    # Clean optional numeric columns
    for col in optional_numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True), errors='coerce').fillna(method='ffill')

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
    df['Signal_Threshold_Value'] = df[OI_SUM_COL] * threshold_pct

    df['LTN_Prev'] = df[LONG_TILL_NOW_COL].shift(1).fillna(0)
    df['STN_Prev'] = df[SHORT_TILL_NOW_COL].shift(1).fillna(0)

    signals = []

    for _, row in df.iterrows():
        daily_oi_sum = row[OI_SUM_COL]
        ltn, stn = row[LONG_TILL_NOW_COL], row[SHORT_TILL_NOW_COL]
        ltn_prev, stn_prev = row['LTN_Prev'], row['STN_Prev']
        net_change = row['Net_Position_Change']
        threshold = row['Signal_Threshold_Value']

        if daily_oi_sum < min_oi_sum:
            signals.append('HOLD')
            continue

        longs_increased = ltn > ltn_prev
        shorts_increased = stn > stn_prev

        signal = 'HOLD'

        is_long_doubling = (ltn_prev > 1) and (ltn >= 2 * ltn_prev)
        is_short_doubling = (stn_prev > 1) and (stn >= 2 * stn_prev)
        is_within_range = abs(ltn - stn) <= threshold

        if is_long_doubling and is_within_range and (ltn > stn) and longs_increased:
            signal = 'BUY'
        elif is_short_doubling and is_within_range and (stn > ltn) and shorts_increased:
            signal = 'SELL'
        else:
            if net_change > threshold and longs_increased:
                signal = 'BUY'
            elif net_change < -threshold and shorts_increased:
                signal = 'SELL'

        signals.append(signal)

    df['Signal'] = signals
    return df


# ------------------------------------------------------------------------------------
# TRADE SIMULATION (VWAP FILTER + ONE-POSITION-ONLY RULE)
# ------------------------------------------------------------------------------------
def simulate_trades(df, investment_amount):

    df['Quantity_Traded'] = 0
    df['Position'] = 0
    df['Daily_PnL'] = 0.0

    last_buy_trigger_ltn = 0
    last_sell_trigger_stn = 0

    for i in range(1, len(df)):
        current_price = df.loc[i, CLOSE_COL]
        previous_price = df.loc[i - 1, CLOSE_COL]

        signal_prev = df.loc[i - 1, 'Signal']
        ltn_prev = df.loc[i - 1, LONG_TILL_NOW_COL]
        stn_prev = df.loc[i - 1, SHORT_TILL_NOW_COL]
        
        # Position at the START of the current day (end of previous day)
        position = df.loc[i - 1, 'Position'] 

        # Calculate PnL based on the position held from the previous day
        df.loc[i, 'Daily_PnL'] = (current_price - previous_price) * position

        net_trade_qty = 0
        calculated_trade_qty = math.floor(investment_amount / current_price) if current_price > 0 else 0

        # ------------------------------------------------------------------
        # VWAP FILTER
        # ------------------------------------------------------------------
        vwap = df.loc[i, 'vwap'] if 'vwap' in df.columns else None
        allow_buy = allow_sell = True

        if vwap and vwap > 0:
            # Note: This is checking the current price vs current VWAP for a new trade/exit
            diff_pct = abs(current_price - vwap) / vwap * 100
            allow_buy = (diff_pct <= 0.5) or (current_price > vwap)
            allow_sell = (diff_pct <= 0.5) or (current_price < vwap)

        # ------------------------------------------------------------------
        # COMBINED EXIT/ENTRY LOGIC
        # ------------------------------------------------------------------
        
        # --- 1. EXIT LOGIC (If a position is held and an opposite signal appears) ---
        
        # Exit Short Position (position < 0) on a BUY signal
        if position < 0 and signal_prev == 'BUY' and allow_buy:
            net_trade_qty = abs(position) # Buy to cover the short
            position = 0                  # Position is now flat
            last_sell_trigger_stn = 0     # Reset sell trigger
            
        # Exit Long Position (position > 0) on a SELL signal
        elif position > 0 and signal_prev == 'SELL' and allow_sell:
            net_trade_qty = -position     # Sell to close the long
            position = 0                  # Position is now flat
            last_buy_trigger_ltn = 0      # Reset buy trigger
        
        # --- 2. ENTRY LOGIC (Only if position is flat) ---
        
        elif position == 0:
            
            # BUY Entry
            if signal_prev == 'BUY' and allow_buy:
                if ltn_prev > stn_prev and ltn_prev > last_buy_trigger_ltn:
                    net_trade_qty = calculated_trade_qty
                    position += calculated_trade_qty
                    last_buy_trigger_ltn = ltn_prev

            # SELL Entry
            elif signal_prev == 'SELL' and allow_sell:
                if stn_prev > ltn_prev and stn_prev > last_sell_trigger_stn:
                    net_trade_qty = -calculated_trade_qty
                    position -= calculated_trade_qty
                    last_sell_trigger_stn = stn_prev

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

    # The clean_data function uses pd.to_numeric(errors='coerce') which is more robust
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
        'Signal', 'Quantity_Traded', 'Position', 'Daily_PnL', 'Cumulative_PnL'
    ]

    df_trades[[c for c in output_cols if c in df_trades.columns]].to_csv(OUTPUT_FILE, index=False)

    print(f"\nSaved trade file: {OUTPUT_FILE}")
    print(f"Final PnL: {df_trades['Cumulative_PnL'].iloc[-1]:,.2f}")


if __name__ == "__main__":
    run_pipeline()