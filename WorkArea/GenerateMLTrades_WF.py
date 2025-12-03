# GenerateMLTrades_WF.py
import os
import math
import numpy as np
import pandas as pd

from config_loader import load_config  # type: ignore

# ---------------- CONFIG / CONSTANTS ---------------- #

cfg = load_config()

TARGET_DIR = cfg["TARGET_DIRECTORY"]
INVESTMENT_AMOUNT = cfg["INVESTMENT_AMOUNT"]
SYMBOL = cfg["SYMBOL"]

ANALYSIS_FILE_NAME = f"{SYMBOL}_Analysis.csv"
INPUT_FILE = os.path.join(TARGET_DIR, ANALYSIS_FILE_NAME)

WF_PRED_FILE = os.path.join(TARGET_DIR, f"{SYMBOL}_ML_WF_Predictions.csv")
OUTPUT_FILE = os.path.join(TARGET_DIR, f"{SYMBOL}_Trades_ML_WF.csv")

DATE_COL = "DATE"
OPEN_COL = "OPEN"          # from *_Analysis.csv
CLOSE_COL = "close"
VWAP_COL = "vwap"
LONG_TILL_NOW_COL = "Longs Till Now"
SHORT_TILL_NOW_COL = "Shorts Till Now"
OI_SUM_COL = "Daily_Open_Interest_Sum"


# ------------------------------------------------------------------------------------
# DATA CLEANING
# ------------------------------------------------------------------------------------
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = [DATE_COL, CLOSE_COL, LONG_TILL_NOW_COL,
                     SHORT_TILL_NOW_COL, OI_SUM_COL]
    optional_numeric_cols = [VWAP_COL, OPEN_COL]

    df.columns = df.columns.str.strip()

    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"Required column '{col}' not found in input file.")
        if col != DATE_COL:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[^\d\.\-]", "", regex=True),
                errors="coerce"
            )

    for col in optional_numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[^\d\.\-]", "", regex=True),
                errors="coerce"
            )

    # Parse date and sort
    df[DATE_COL] = pd.to_datetime(df[DATE_COL])
    df.sort_values(DATE_COL, inplace=True)

    # Forward fill numeric gaps where reasonable
    for col in [OPEN_COL, CLOSE_COL, VWAP_COL, LONG_TILL_NOW_COL,
                SHORT_TILL_NOW_COL, OI_SUM_COL]:
        if col in df.columns:
            df[col] = df[col].ffill()

    df.dropna(subset=[CLOSE_COL, LONG_TILL_NOW_COL,
                      SHORT_TILL_NOW_COL, OI_SUM_COL], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ------------------------------------------------------------------------------------
# TRADE SIMULATION (FROM ML_Signal, NO MODEL HERE)
# ------------------------------------------------------------------------------------
def simulate_trades_from_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Use precomputed ML_Signal (BUY/SELL/HOLD) to generate trades.

    Timeline:
      - On day t, ML_Signal[t] is based on a model trained only on data < t.
      - That signal is executed at **OPEN of day t+1**.
      - Quantities are sized using **compounding capital on trade close only**.
    """
    df = df.copy()

    if OPEN_COL not in df.columns:
        raise KeyError(f"Required column '{OPEN_COL}' (open price) not found for trade execution.")

    # Ensure OPEN/CLOSE numeric and no NaNs
    df.loc[:, OPEN_COL] = pd.to_numeric(df[OPEN_COL], errors="coerce").ffill()
    df.loc[:, CLOSE_COL] = pd.to_numeric(df[CLOSE_COL], errors="coerce").ffill()

    n = len(df)
    quantity_traded = np.zeros(n, dtype=float)
    position_arr = np.zeros(n, dtype=float)

    # Dynamic compounding capital (updated only when trade closes)
    dynamic_capital = float(INVESTMENT_AMOUNT)

    # Track entry price & qty of current trade for realized PnL
    entry_exec_price = None  # open price at entry
    entry_qty = 0.0          # absolute quantity (positive)

    position = 0.0

    signals_arr = df["ML_Signal"].to_numpy()
    opens = df[OPEN_COL].to_numpy()

    # Day 0: no prior signal to trade on; remains flat
    position_arr[0] = 0.0
    quantity_traded[0] = 0.0

    # ---------------- TRADE EXECUTION WITH COMPOUNDING ---------------- #
    for t in range(1, n):
        signal_prev = signals_arr[t - 1]
        exec_price = opens[t]
        qty_trade = 0.0

        # ----- 1) EXIT / FLATTEN at today's open based on yesterday's signal -----
        if position > 0 and signal_prev in ["SELL", "HOLD"]:
            # Closing LONG at exec_price
            if entry_exec_price is not None and entry_qty > 0:
                trade_pnl = (exec_price - entry_exec_price) * entry_qty
                dynamic_capital += trade_pnl
                if dynamic_capital < 0:
                    dynamic_capital = 0.0

            qty_trade += -position
            position = 0.0
            entry_exec_price = None
            entry_qty = 0.0

        elif position < 0 and signal_prev in ["BUY", "HOLD"]:
            # Closing SHORT at exec_price
            if entry_exec_price is not None and entry_qty > 0:
                trade_pnl = (entry_exec_price - exec_price) * entry_qty
                dynamic_capital += trade_pnl
                if dynamic_capital < 0:
                    dynamic_capital = 0.0

            qty_trade += -position
            position = 0.0
            entry_exec_price = None
            entry_qty = 0.0

        # ----- 2) ENTRY at today's open (only if flat) -----
        if position == 0.0 and exec_price > 0:
            if signal_prev == "BUY":
                qty = math.floor(dynamic_capital / exec_price)
                if qty > 0:
                    qty_trade += qty
                    position = qty
                    entry_exec_price = exec_price
                    entry_qty = qty  # positive

            elif signal_prev == "SELL":
                qty = math.floor(dynamic_capital / exec_price)
                if qty > 0:
                    qty_trade += -qty
                    position = -qty
                    entry_exec_price = exec_price
                    entry_qty = qty  # absolute qty

        quantity_traded[t] = qty_trade
        position_arr[t] = position

    df.loc[:, "Quantity_Traded"] = quantity_traded
    df.loc[:, "Position"] = position_arr

    # ---------------- P&L CALCULATION ---------------- #
    # Position is effective for the day; PnL is close-to-close using today's position
    df.loc[:, "Prev_Close"] = df[CLOSE_COL].shift(1).ffill()
    df.loc[:, "Daily_PnL"] = (df[CLOSE_COL] - df["Prev_Close"]) * df["Position"]

    # First day has no PnL
    if len(df) > 0:
        first_idx = df.index[0]
        df.loc[first_idx, "Daily_PnL"] = 0.0

    df.loc[:, "Cumulative_PnL"] = df["Daily_PnL"].cumsum()

    return df


# ------------------------------------------------------------------------------------
# MAIN PIPELINE
# ------------------------------------------------------------------------------------
def run_trading_pipeline():
    print(f"--- ML-based F&O Trade Generation (WALK-FORWARD) ---")
    print(f"Input Analysis File: {INPUT_FILE}")
    print(f"WF Predictions File: {WF_PRED_FILE}")

    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return

    if not os.path.exists(WF_PRED_FILE):
        print(f"ERROR: Walk-forward prediction file not found: {WF_PRED_FILE}")
        print("Run WalkForwardTrainer.py first.")
        return

    df_raw = pd.read_csv(INPUT_FILE, thousands=",")
    df_clean = clean_data(df_raw.copy())
    if df_clean.empty:
        print("ERROR: Data empty after cleaning.")
        return

    preds = pd.read_csv(WF_PRED_FILE, parse_dates=[DATE_COL])

    # Make sure DATE is datetime in both
    df_clean[DATE_COL] = pd.to_datetime(df_clean[DATE_COL])
    preds[DATE_COL] = pd.to_datetime(preds[DATE_COL])

    # Inner join: only dates where we have predictions
    df = pd.merge(df_clean, preds, on=DATE_COL, how="inner")
    df.sort_values(DATE_COL, inplace=True)
    df.reset_index(drop=True, inplace=True)

    if df.empty:
        print("ERROR: No overlapping dates between analysis and predictions.")
        return

    df_trades = simulate_trades_from_signals(df)

    # Build final output with familiar structure
    output_cols = [
        DATE_COL,
        OPEN_COL if OPEN_COL in df_trades.columns else None,
        CLOSE_COL,
        VWAP_COL if VWAP_COL in df_trades.columns else None,
        LONG_TILL_NOW_COL,
        SHORT_TILL_NOW_COL,
        OI_SUM_COL,
        "ML_Signal", "ML_Label", "ML_Conf",
        "Quantity_Traded", "Position",
        "Daily_PnL", "Cumulative_PnL",
    ]
    output_cols = [c for c in output_cols if c in df_trades.columns]

    df_trades.to_csv(OUTPUT_FILE, index=False)

    print(f"\n✔ Saved WALK-FORWARD ML trade file: {OUTPUT_FILE}")
    print(f"Final PnL (WF ML strategy): {df_trades['Cumulative_PnL'].iloc[-1]:,.2f}")


if __name__ == "__main__":
    run_trading_pipeline()
