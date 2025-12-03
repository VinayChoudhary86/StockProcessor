# TrainMLModel.py
import os
from typing import List, Tuple
import pickle

import numpy as np
import pandas as pd

from config_loader import load_config  # type: ignore
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix

# ---------------- CONFIG / CONSTANTS ---------------- #

cfg = load_config()

TARGET_DIR = cfg["TARGET_DIRECTORY"]
SYMBOL = cfg["SYMBOL"]

ANALYSIS_FILE_NAME = f"{SYMBOL}_Analysis.csv"
INPUT_FILE = os.path.join(TARGET_DIR, ANALYSIS_FILE_NAME)
MODEL_FILE = os.path.join(TARGET_DIR, f"MODEL_{SYMBOL}.pkl")

DATE_COL = "DATE"
OPEN_COL = "OPEN"          # from *_Analysis.csv
CLOSE_COL = "close"
VWAP_COL = "vwap"
LONG_TILL_NOW_COL = "Longs Till Now"
SHORT_TILL_NOW_COL = "Shorts Till Now"
OI_SUM_COL = "Daily_Open_Interest_Sum"

# Class mapping (must match GenerateMLTrades.py)
CLASS_MAP = {-1: 0, 0: 1, 1: 2}
INV_CLASS_MAP = {v: k for k, v in CLASS_MAP.items()}


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

    y_train_mapped = y_train.map(CLASS_MAP)
    y_test_mapped = y_test.map(CLASS_MAP)

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
    y_pred = pd.Series(y_pred_mapped).map(INV_CLASS_MAP)

    print("\n--- ML MODEL EVALUATION (LAST 30% PERIOD) ---")
    print(classification_report(y_test, y_pred))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred, labels=[-1, 0, 1]))

    return model


# ------------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------------
def run_training_pipeline():
    print(f"--- ML MODEL TRAINING (XGBoost) ---")
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

    # Save model and feature columns together
    bundle = {
        "model": model,
        "feature_cols": feature_cols,
    }

    with open(MODEL_FILE, "wb") as f:
        pickle.dump(bundle, f)

    print(f"\n✔ Saved trained model to: {MODEL_FILE}")


if __name__ == "__main__":
    run_training_pipeline()
