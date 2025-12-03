# WalkForwardTrainer.py
import os
import pickle
from typing import List, Tuple

import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix

from config_loader import load_config  # type: ignore
from utils_progress import print_progress_bar  # type: ignore

# ---------------- CONFIG / CONSTANTS ---------------- #

cfg = load_config()

TARGET_DIR = cfg["TARGET_DIRECTORY"]
SYMBOL = cfg["SYMBOL"]

ANALYSIS_FILE_NAME = f"{SYMBOL}_Analysis.csv"
INPUT_FILE = os.path.join(TARGET_DIR, ANALYSIS_FILE_NAME)
WF_PRED_FILE = os.path.join(TARGET_DIR, f"{SYMBOL}_ML_WF_Predictions.csv")

DATE_COL = "DATE"
OPEN_COL = "OPEN"
CLOSE_COL = "close"
VWAP_COL = "vwap"
LONG_TILL_NOW_COL = "Longs Till Now"
SHORT_TILL_NOW_COL = "Shorts Till Now"
OI_SUM_COL = "Daily_Open_Interest_Sum"

# Same class mapping as TrainMLModel.py / GenerateMLTrades.py
CLASS_MAP = {-1: 0, 0: 1, 1: 2}
INV_CLASS_MAP = {v: k for k, v in CLASS_MAP.items()}

# Walk-forward settings
MIN_TRAIN_SIZE = 200     # minimum days before first prediction
PROB_LONG = 0.55
PROB_SHORT = 0.55


# ------------------------------------------------------------------------------------
# DATA CLEANING  (same logic as TrainMLModel / GenerateMLTrades)
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
# FEATURE ENGINEERING  (same as before)
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


def get_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    feature_cols = [
        "ret_1", "ret_3", "ret_5",
        "vol_10",
        "gap_ema10", "gap_ema20", "gap_ema50", "gap_vwap",
        "long_diff", "short_diff", "oi_diff",
        "long_ratio", "short_ratio",
        "long_5ch", "short_5ch"
    ]
    X = df[feature_cols].copy()
    return X, feature_cols


# ------------------------------------------------------------------------------------
# LABEL BUILDING (ONCE, FOR EVALUATION ONLY)
# ------------------------------------------------------------------------------------
def add_labels(df: pd.DataFrame,
               up_thresh: float = 0.002,
               down_thresh: float = -0.002) -> pd.DataFrame:
    """
    Add Label column to df using next-day return.
    We do NOT drop last row here; last label may be meaningless (no future close)
    but we never train/predict on the last index anyway.
    """
    future_ret = df[CLOSE_COL].shift(-1) / df[CLOSE_COL] - 1.0
    df["future_ret"] = future_ret

    labels = np.zeros(len(df), dtype=int)
    labels[future_ret > up_thresh] = 1
    labels[future_ret < down_thresh] = -1

    df["Label"] = labels.astype(int)
    return df


# ------------------------------------------------------------------------------------
# WALK-FORWARD TRAINING
# ------------------------------------------------------------------------------------
def walk_forward_train(df: pd.DataFrame) -> pd.DataFrame:
    """
    Daily walk-forward:
      - For each day t (from MIN_TRAIN_SIZE to n-2):
          train on [0 .. t-1]
          predict for t
    Ensures the model has never seen day t or later when predicting for t.
    """
    df = df.copy()
    X_all, feature_cols = get_feature_matrix(df)

    n = len(df)
    if n < MIN_TRAIN_SIZE + 2:
        raise ValueError(f"Not enough data for walk-forward (need at least {MIN_TRAIN_SIZE + 2}, have {n})")

    records = []

    print(f"\n--- WALK-FORWARD TRAINING (Daily Retrain) ---")
    print(f"Total rows: {n}, first prediction will start at index {MIN_TRAIN_SIZE}")

    total_steps = n - 1 - MIN_TRAIN_SIZE  # last usable index is n-2
    step = 0

    for t in range(MIN_TRAIN_SIZE, n - 1):
        step += 1
        print_progress_bar(step, total_steps, label="Walk-forward")

        # TRAIN: use rows [0 .. t-1]
        train_idx = list(range(0, t))
        X_train = X_all.iloc[train_idx]
        y_train = df["Label"].iloc[train_idx].map(CLASS_MAP)

        # Just in case, drop any NaNs from y_train
        mask = ~y_train.isna()
        X_train = X_train[mask]
        y_train = y_train[mask]

        if len(X_train) < MIN_TRAIN_SIZE:
            # Safety fallback, though this should not normally trigger
            continue

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

        model.fit(X_train, y_train)

        # PREDICT for day t (single row)
        X_pred = X_all.iloc[[t]]
        proba = model.predict_proba(X_pred)[0]
        pred_class_mapped = int(np.argmax(proba))
        pred_conf = float(np.max(proba))
        pred_label = INV_CLASS_MAP[pred_class_mapped]

        # Convert label + confidence to ML_Signal (BUY/SELL/HOLD)
        if pred_label == 1 and pred_conf >= PROB_LONG:
            signal = "BUY"
        elif pred_label == -1 and pred_conf >= PROB_SHORT:
            signal = "SELL"
        else:
            signal = "HOLD"

        true_label = int(df["Label"].iloc[t])

        records.append({
            "DATE": df[DATE_COL].iloc[t],
            "ML_Label": pred_label,
            "ML_Conf": pred_conf,
            "ML_Signal": signal,
            "True_Label": true_label,
        })

    preds_df = pd.DataFrame(records)
    preds_df.sort_values("DATE", inplace=True)
    preds_df.reset_index(drop=True, inplace=True)

    # Basic evaluation (True_Label vs ML_Label)
    if not preds_df.empty:
        print("\n\n--- WALK-FORWARD EVALUATION (Out-of-sample each day) ---")
        print(classification_report(preds_df["True_Label"], preds_df["ML_Label"]))
        print("Confusion Matrix:")
        print(confusion_matrix(preds_df["True_Label"], preds_df["ML_Label"], labels=[-1, 0, 1]))

    return preds_df


# ------------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------------
def run_walk_forward():
    print(f"--- Walk-Forward Trainer ---")
    print(f"Input Analysis File: {INPUT_FILE}")
    print(f"Output Predictions:  {WF_PRED_FILE}")

    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Input file not found: {INPUT_FILE}")
        return

    df_raw = pd.read_csv(INPUT_FILE, thousands=",")
    df_clean = clean_data(df_raw.copy())
    if df_clean.empty:
        print("ERROR: Data empty after cleaning.")
        return

    df_feat = add_features(df_clean.copy())
    df_feat = add_labels(df_feat, up_thresh=0.002, down_thresh=-0.002)

    preds_df = walk_forward_train(df_feat)

    preds_df.to_csv(WF_PRED_FILE, index=False)
    print(f"\n✔ Walk-forward predictions saved to: {WF_PRED_FILE}")


if __name__ == "__main__":
    run_walk_forward()
