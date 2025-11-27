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
OUTPUT_IMAGE_FILE = os.path.join(TARGET_DIR, f"{SYMBOL}_Trades_Chart.png")

DATE_COL = 'DATE'
CLOSE_COL = 'close'
LONG_TILL_NOW_COL = 'Longs Till Now'
SHORT_TILL_NOW_COL = 'Shorts Till Now'
OI_SUM_COL = 'Daily_Open_Interest_Sum'


# ------------------------------------------------------------------------------------
# CLEANING FUNCTION (VWAP INCLUDED)
# ------------------------------------------------------------------------------------
def clean_data(df):
    """Clean and ensure necessary columns are numeric and filled."""
    required_cols = [LONG_TILL_NOW_COL, SHORT_TILL_NOW_COL, OI_SUM_COL, CLOSE_COL]
    optional_numeric_cols = ['vwap']  # NEW COLUMN TO COPY

    df.columns = df.columns.str.strip()

    # Clean required columns
    for col in required_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            raise KeyError(f"Required column not found: '{col}'. Please check your input file headers.")

    # Clean optional columns
    for col in optional_numeric_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[^\d\.\-]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(method='ffill')

    df.dropna(subset=[OI_SUM_COL, LONG_TILL_NOW_COL, SHORT_TILL_NOW_COL, CLOSE_COL], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


# ------------------------------------------------------------------------------------
# OI MIN THRESHOLD CALC
# ------------------------------------------------------------------------------------
def calculate_dynamic_min_oi(df):
    if df[OI_SUM_COL].empty:
        return 0

    min_oi = df[OI_SUM_COL].quantile(0.25)
    if min_oi == 0:
        warnings.warn("Calculated MINIMUM_OI_SUM is 0. Using 1 to ensure a minimum threshold.")
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

        signal_to_append = 'HOLD'

        is_long_doubling = (ltn_prev > 1) and (ltn >= 2 * ltn_prev)
        is_short_doubling = (stn_prev > 1) and (stn >= 2 * stn_prev)
        is_within_range = (abs(ltn - stn) <= threshold)

        if is_long_doubling and is_within_range and (ltn > stn):
            if longs_increased:
                signal_to_append = 'BUY'

        elif is_short_doubling and is_within_range and (stn > ltn):
            if shorts_increased:
                signal_to_append = 'SELL'

        if signal_to_append == 'HOLD':
            if net_change > threshold and longs_increased:
                signal_to_append = 'BUY'
            elif net_change < -threshold and shorts_increased:
                signal_to_append = 'SELL'

        signals.append(signal_to_append)

    df['Signal'] = signals
    return df


# ------------------------------------------------------------------------------------
# TRADE SIMULATION
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

        signal_prev_day = df.loc[i - 1, 'Signal']
        ltn_prev_day = df.loc[i - 1, LONG_TILL_NOW_COL]
        stn_prev_day = df.loc[i - 1, SHORT_TILL_NOW_COL]
        position_held_overnight = df.loc[i - 1, 'Position']

        df.loc[i, 'Daily_PnL'] = (current_price - previous_price) * position_held_overnight

        position = position_held_overnight
        net_trade_qty = 0

        calculated_trade_qty = 0
        if current_price > 0:
            calculated_trade_qty = math.floor(investment_amount / current_price)

        if signal_prev_day == 'BUY':
            if ltn_prev_day > stn_prev_day:

                if position < 0:
                    net_trade_qty = -position
                    position = 0

                if ltn_prev_day > last_buy_trigger_ltn:
                    if position >= 0:
                        position += calculated_trade_qty
                        net_trade_qty += calculated_trade_qty

                    last_buy_trigger_ltn = ltn_prev_day

        elif signal_prev_day == 'SELL':
            if stn_prev_day > ltn_prev_day:

                if position > 0:
                    net_trade_qty = -position
                    position = 0

                if stn_prev_day > last_sell_trigger_stn:
                    if position <= 0:
                        position -= calculated_trade_qty
                        net_trade_qty -= calculated_trade_qty

                    last_sell_trigger_stn = stn_prev_day

        df.loc[i, 'Quantity_Traded'] = net_trade_qty
        df.loc[i, 'Position'] = position

    df['Cumulative_PnL'] = df['Daily_PnL'].cumsum()
    return df


# ------------------------------------------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------------------------------------------
def run_pipeline():
    print(f"--- F&O Trade Strategy Backtester & Plotter ---")
    print(f"Input Data: {INPUT_FILE}")

    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file not found: {INPUT_FILE}")
        return

    try:
        df = pd.read_csv(INPUT_FILE, thousands=',')
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

    try:
        df_cleaned = clean_data(df.copy())

        if df_cleaned.empty:
            print("Error: DataFrame empty after cleaning.")
            return

        MINIMUM_OI_SUM = calculate_dynamic_min_oi(df_cleaned)
        if MINIMUM_OI_SUM == 0:
            print("Error: Dynamic minimum OI is zero.")
            return

        df_signals = generate_signals(df_cleaned, DIFFERENCE_THRESHOLD_PCT, MINIMUM_OI_SUM)
        df_trades = simulate_trades(df_signals, INVESTMENT_AMOUNT)

        # -------------------------------
        # OUTPUT COLUMNS including VWAP
        # -------------------------------
        output_cols = [
            DATE_COL, CLOSE_COL, 'vwap',
            LONG_TILL_NOW_COL, SHORT_TILL_NOW_COL,
            OI_SUM_COL, 'Net_Position_Change', 'Signal_Threshold_Value',
            'Signal', 'Quantity_Traded', 'Position', 'Daily_PnL', 'Cumulative_PnL'
        ]

        final_output = df_trades[[c for c in output_cols if c in df_trades.columns]]
        final_output.to_csv(OUTPUT_FILE, index=False)

        print(f"\nSaved trade file: {OUTPUT_FILE}")
        print(f"Total trading days: {len(final_output)}")
        print(f"Final PnL: {final_output['Cumulative_PnL'].iloc[-1]:,.2f}")

    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    run_pipeline()
