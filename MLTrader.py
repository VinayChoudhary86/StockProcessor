import os
import math
from typing import List, Tuple

import numpy as np
import pandas as pd

from config_loader import load_config  # type: ignore

# ML imports
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix

# ---------------- CONFIG / CONSTANTS ---------------- #

cfg = load_config()

TARGET_DIR = cfg["TARGET_DIRECTORY"]
INVESTMENT_AMOUNT = cfg["INVESTMENT_AMOUNT"]
SYMBOL = cfg["SYMBOL"]

ANALYSIS_FILE_NAME = f"{SYMBOL}_Analysis.csv"
INPUT_FILE = os.path.join(TARGET_DIR, ANALYSIS_FILE_NAME)
OUTPUT_FILE = os.path.join(TARGET_DIR, f"{SYMBOL}_Trades_ML.csv")

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
# FEATURE ENGINEERING
# ------------------------------------------------------------------------------------
def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build ML features from price, VWAP, OI, longs, shorts etc.
    All features are based on current and past data only (no lookahead).
    """
    # Returns
    df["ret_1"] = df[CLOSE_COL].pct_change().fillna(0.0)
    df["ret_3"] = df[CLOSE_COL].pct_change(3).fillna(0.0)
    df["ret_5"] = df[CLOSE_COL].pct_change(5).fillna(0.0)

    # Volatility (10-day rolling std of 1-day returns)
    df["vol_10"] = df["ret_1"].rolling(10).std().fillna(0.0)

    # EMAs
    df["ema_10"] = df[CLOSE_COL].ewm(span=10, adjust=False).mean()
    df["ema_20"] = df[CLOSE_COL].ewm(span=20, adjust=False).mean()
    df["ema_50"] = df[CLOSE_COL].ewm(span=50, adjust=False).mean()

    # Gaps vs EMA
    df["gap_ema10"] = (df[CLOSE_COL] - df["ema_10"]) / df["ema_10"]
    df["gap_ema20"] = (df[CLOSE_COL] - df["ema_20"]) / df["ema_20"]
    df["gap_ema50"] = (df[CLOSE_COL] - df["ema_50"]) / df["ema_50"]

    # VWAP gap (if available)
    if VWAP_COL in df.columns:
        df["gap_vwap"] = (df[CLOSE_COL] - df[VWAP_COL]) / df[VWAP_COL]
    else:
        df["gap_vwap"] = 0.0

    # OI-based features
    df["long_diff"] = df[LONG_TILL_NOW_COL].diff().fillna(0.0)
    df["short_diff"] = df[SHORT_TILL_NOW_COL].diff().fillna(0.0)
    df["oi_diff"] = df[OI_SUM_COL].diff().fillna(0.0)

    total_ls = df[LONG_TILL_NOW_COL] + df[SHORT_TILL_NOW_COL] + 1e-6
    df["long_ratio"] = df[LONG_TILL_NOW_COL] / total_ls
    df["short_ratio"] = df[SHORT_TILL_NOW_COL] / total_ls

    # Rolling OI trend (5-day change)
    df["long_5ch"] = df[LONG_TILL_NOW_COL].pct_change(5).fillna(0.0)
    df["short_5ch"] = df[SHORT_TILL_NOW_COL].pct_change(5).fillna(0.0)

    # Replace inf / NaN in features
    feature_cols = [
        "ret_1", "ret_3", "ret_5",
        "vol_10",
        "gap_ema10", "gap_ema20", "gap_ema50", "gap_vwap",
        "long_diff", "short_diff", "oi_diff",
        "long_ratio", "short_ratio",
        "long_5ch", "short_5ch"
    ]
    for col in feature_cols:
        df[col] = df[col].replace([np.inf, -np.inf], 0.0).fillna(0.0)

    return df


def build_labels(df: pd.DataFrame,
                 up_thresh: float = 0.002,
                 down_thresh: float = -0.002) -> pd.DataFrame:
    """
    Multi-class labels:
      +1 -> next-day return > up_thresh
       0 -> between down_thresh and up_thresh
      -1 -> next-day return < down_thresh
    """
    future_ret = df[CLOSE_COL].shift(-1) / df[CLOSE_COL] - 1.0
    df["future_ret"] = future_ret

    labels = np.zeros(len(df), dtype=int)

    labels[future_ret > up_thresh] = 1
    labels[future_ret < down_thresh] = -1

    df["Label"] = labels

    # Drop last row (no future_ret)
    df = df.iloc[:-1].copy()
    return df


def get_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    feature_cols = [
        "ret_1", "ret_3", "ret_5",
        "vol_10",
        "gap_ema10", "gap_ema20", "gap_ema50", "gap_vwap",
        "long_diff", "short_diff", "oi_diff",
        "long_ratio", "short_ratio",
        "long_5ch", "short_5ch"
    ]
    X = df[feature_cols].copy()
    y = df["Label"].copy()
    return X, y, feature_cols


# ------------------------------------------------------------------------------------
# MODEL TRAINING
# ------------------------------------------------------------------------------------
def train_xgb_model(X: pd.DataFrame, y: pd.Series) -> XGBClassifier:
    """
    Train XGBoost multi-class classifier on time series (simple split).
    Uses first 70% as train, last 30% as validation for basic metrics.
    """
    n = len(X)
    split_idx = int(n * 0.7)  # 70% train, 30% test (time-based)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    # Map classes -1,0,1 to {0,1,2} for XGBoost
    class_map = {-1: 0, 0: 1, 1: 2}
    inv_class_map = {v: k for k, v in class_map.items()}

    y_train_mapped = y_train.map(class_map)
    y_test_mapped = y_test.map(class_map)

    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        tree_method="hist",
        random_state=42,
    )

    model.fit(X_train, y_train_mapped)

    # Basic evaluation
    y_pred_mapped = model.predict(X_test)
    y_pred = pd.Series(y_pred_mapped).map(inv_class_map)

    print("\n--- ML MODEL EVALUATION (LAST 30% PERIOD) ---")
    print(classification_report(y_test, y_pred))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred, labels=[-1, 0, 1]))

    return model


# ------------------------------------------------------------------------------------
# TRADING STRATEGY BASED ON MODEL PREDICTIONS
# ------------------------------------------------------------------------------------
def simulate_trades_with_model(df: pd.DataFrame,
                               model: XGBClassifier,
                               X: pd.DataFrame,
                               prob_long: float = 0.55,
                               prob_short: float = 0.55) -> pd.DataFrame:
    """
    Use model predictions to generate trades.

    Timeline:
      - On day t, model uses day-t data → produces ML_Signal[t].
      - That signal is executed at **OPEN of day t+1**.
      - Quantities are sized as floor(INVESTMENT_AMOUNT / next_day_open).
      - P&L is computed close-to-close using the position effective for that day.
    """

    df = df.copy()

    # Map {0,1,2} back to {-1,0,1}
    inv_class_map = {0: -1, 1: 0, 2: 1}

    proba = model.predict_proba(X)
    pred_class_mapped = np.argmax(proba, axis=1)
    pred_conf = proba.max(axis=1)
    pred_label = np.array([inv_class_map[c] for c in pred_class_mapped])

    df.loc[:, "ML_Label"] = pred_label
    df.loc[:, "ML_Conf"] = pred_conf

    # Convert label + confidence into trading signal
    signals = []
    for lbl, conf in zip(pred_label, pred_conf):
        if lbl == 1 and conf >= prob_long:
            signals.append("BUY")
        elif lbl == -1 and conf >= prob_short:
            signals.append("SELL")
        else:
            signals.append("HOLD")
    df.loc[:, "ML_Signal"] = signals

    if OPEN_COL not in df.columns:
        raise KeyError(f"Required column '{OPEN_COL}' (open price) not found for trade execution.")

    # Ensure OPEN numeric and no NaNs
    df.loc[:, OPEN_COL] = pd.to_numeric(df[OPEN_COL], errors="coerce").ffill()
    df.loc[:, CLOSE_COL] = pd.to_numeric(df[CLOSE_COL], errors="coerce").ffill()

    n = len(df)
    quantity_traded = np.zeros(n, dtype=float)
    position_arr = np.zeros(n, dtype=float)

    position = 0.0

    signals_arr = df["ML_Signal"].to_numpy()
    opens = df[OPEN_COL].to_numpy()

    # Day 0: no prior signal to trade on; remains flat
    position_arr[0] = 0.0
    quantity_traded[0] = 0.0

    # For day t >= 1: execute signal from day t-1 at OPEN[t]
    for t in range(1, n):
        signal_prev = signals_arr[t - 1]
        exec_price = opens[t]
        qty_trade = 0.0

        # ----- EXIT / FLATTEN at today's open based on yesterday's signal -----
        if position > 0:
            if signal_prev in ["SELL", "HOLD"]:
                qty_trade += -position
                position = 0.0

        elif position < 0:
            if signal_prev in ["BUY", "HOLD"]:
                qty_trade += -position
                position = 0.0

        # ----- ENTRY at today's open (only if flat) -----
        if position == 0.0:
            if signal_prev == "BUY":
                if exec_price > 0:
                    qty = math.floor(INVESTMENT_AMOUNT / exec_price)
                else:
                    qty = 0
                if qty > 0:
                    qty_trade += qty
                    position = qty

            elif signal_prev == "SELL":
                if exec_price > 0:
                    qty = math.floor(INVESTMENT_AMOUNT / exec_price)
                else:
                    qty = 0
                if qty > 0:
                    qty_trade += -qty
                    position = -qty

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
def run_pipeline():
    print(f"--- ML-based F&O Trade Strategy (XGBoost) ---")
    print(f"Input Data: {INPUT_FILE}")

    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return

    df_raw = pd.read_csv(INPUT_FILE, thousands=",")

    df_clean = clean_data(df_raw.copy())
    if df_clean.empty:
        print("ERROR: Data empty after cleaning.")
        return

    print(f"Rows after cleaning: {len(df_clean)}")

    df_feat = add_features(df_clean.copy())
    df_labeled = build_labels(df_feat.copy(), up_thresh=0.002, down_thresh=-0.002)

    X, y, feature_cols = get_feature_matrix(df_labeled)

    if len(X) < 200:
        print("ERROR: Not enough data for ML training (need at least ~200 rows).")
        return

    model = train_xgb_model(X, y)

    df_trades = simulate_trades_with_model(
        df_labeled, model, X,
        prob_long=0.55, prob_short=0.55
    )

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

    print(f"\nSaved ML trade file: {OUTPUT_FILE}")
    print(f"Final PnL (ML strategy): {df_trades['Cumulative_PnL'].iloc[-1]:,.2f}")


if __name__ == "__main__":
    run_pipeline()
