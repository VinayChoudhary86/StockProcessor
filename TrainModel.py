"""
TrainModel.py  (FIXED ML MODEL)

Replaces the old ML-based threshold generator with a robust,
distribution-based statistical model.

Corrects:
    - Negative delivery thresholds
    - Positive OI thresholds for shorts
    - Inverted long/short logic
    - Abnormal scaled outputs
    - Zero-shorts problem due to impossible thresholds

This version integrates perfectly with GenerateAnalysis.py
and writes realistic thresholds into configProcess.ini.
"""

import os
import configparser
import numpy as np
import pandas as pd

from config_loader import load_config  # type: ignore
from GenerateAnalysis import (        # type: ignore
    build_base_dataframe,
    PRICE_CHANGE_COL,
    REL_DELIVERY_COL,
    OI_CHANGE_COL,
    NEW_5DAD_COL,
    DELIVERY_VALUE_COL,
    VWAP_COL,
    SYMBOL,
    CONFIG_PATH,
    TARGET_DIRECTORY,
    SD_MULTIPLIER,
)

# =============================================================
# Utility functions
# =============================================================

def _safe_series(df: pd.DataFrame, col: str) -> pd.Series:
    """Return valid numeric column."""
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce").dropna()


def _long_short_from_signed(series: pd.Series,
                            long_q: float = 0.6,
                            short_q: float = 0.4):
    """
    Compute thresholds for signed values like ~Price, ~OI etc.

    - long threshold is upper percentile of positive values
    - short threshold is lower percentile of negative values
    """
    series = series.replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return 0.0, 0.0

    pos = series[series > 0]
    neg = series[series < 0]

    # Long
    if len(pos) >= 10:
        long_thr = float(pos.quantile(long_q))
    else:
        long_thr = float(series.quantile(0.7))

    # Short
    if len(neg) >= 10:
        short_thr = float(neg.quantile(short_q))
    else:
        short_thr = float(series.quantile(0.3))

    # Fix signs
    if long_thr <= 0 and (series > 0).any():
        long_thr = float(pos.median())
    if short_thr >= 0 and (series < 0).any():
        short_thr = float(neg.median())

    # Final fallback
    if long_thr <= 0:
        long_thr = float(series.quantile(0.7))
    if short_thr >= 0:
        short_thr = float(series.quantile(0.3)) * -1

    return long_thr, short_thr


def _pos_neg_threshold(series: pd.Series,
                       long_q: float = 0.6,
                       short_q: float = 0.4):
    """
    Positive–negative threshold extractor for absolute values and OI change.
    """
    series = series.replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return 0.0, 0.0

    pos = series[series > 0]
    neg = series[series < 0]

    # Long
    if len(pos) >= 10:
        long_thr = float(pos.quantile(long_q))
    else:
        long_thr = float(series.quantile(0.7))

    # Short
    if len(neg) >= 10:
        short_thr = float(neg.quantile(short_q))
    else:
        short_thr = float(series.quantile(0.3))

    if long_thr <= 0 and len(pos):
        long_thr = float(pos.median())
    if short_thr >= 0 and len(neg):
        short_thr = float(neg.median())

    return long_thr, short_thr


# =============================================================
# Threshold computation
# =============================================================

def compute_thresholds(df: pd.DataFrame) -> dict:
    """
    Computes all thresholds for LONG and SHORT detection.
    """

    th = {}

    # Base columns
    s_price = _safe_series(df, PRICE_CHANGE_COL)
    s_del   = _safe_series(df, REL_DELIVERY_COL)
    s_oi    = _safe_series(df, OI_CHANGE_COL)
    s_absoi = _safe_series(df, "Absolute_OI_Change")
    s_vwap  = _safe_series(df, VWAP_COL)
    s_5dad  = _safe_series(df, NEW_5DAD_COL)
    s_delv  = _safe_series(df, DELIVERY_VALUE_COL)

    # Price thresholds
    th["price_long"], th["price_short"] = _long_short_from_signed(s_price)

    # Delivery thresholds (~Del)
    if not s_del.empty:
        th["del_long"] = float(s_del.quantile(0.6))
        th["del_short"] = float(s_del.quantile(0.3))
    else:
        th["del_long"] = 100
        th["del_short"] = 80

    # OI thresholds
    th["oi_long"], th["oi_short"] = _long_short_from_signed(s_oi)

    # Absolute OI thresholds
    th["absolute_oi_change_long"], th["absolute_oi_change_short"] = _pos_neg_threshold(s_absoi)

    # VWAP thresholds (for reference)
    if not s_vwap.empty:
        median_vwap = float(s_vwap.median())
        th["vwap_long"] = median_vwap * 1.01
        th["vwap_short"] = median_vwap * 0.99
    else:
        th["vwap_long"] = 0
        th["vwap_short"] = 0

    # 5D Avg Delivery thresholds
    if not s_5dad.empty:
        th["5dad_long"] = float(s_5dad.quantile(0.6))
        th["5dad_short"] = float(s_5dad.quantile(0.4))
    else:
        th["5dad_long"] = 0
        th["5dad_short"] = 0

    # Delivery value thresholds
    if not s_delv.empty:
        th["delivery_long"] = float(s_delv.quantile(0.6))
        th["delivery_short"] = float(s_delv.quantile(0.4))
    else:
        th["delivery_long"] = 0
        th["delivery_short"] = 0

    return th


# =============================================================
# Write thresholds into config
# =============================================================

def write_thresholds_to_config(th: dict):
    cfg = configparser.ConfigParser()
    if os.path.exists(CONFIG_PATH):
        cfg.read(CONFIG_PATH)

    section = f"THRESHOLDS_{SYMBOL}"

    if cfg.has_section(section):
        cfg.remove_section(section)

    cfg.add_section(section)

    for k, v in th.items():
        cfg.set(section, k, f"{v:.6f}")

    with open(CONFIG_PATH, "w") as f:
        cfg.write(f)

    print(f"✔ Updated thresholds saved under [{section}] in:")
    print(f"  {CONFIG_PATH}")


# =============================================================
# Main
# =============================================================

def main():
    print("=== Building dataframe for ML training ===")
    df = build_base_dataframe(TARGET_DIRECTORY, SD_MULTIPLIER)
    print(f"Loaded {len(df)} rows.")

    if df.empty:
        print("No data → abort.")
        return

    print("=== Computing statistical thresholds ===")
    thresholds = compute_thresholds(df)

    for k, v in thresholds.items():
        print(f"{k:30s} = {v:.6f}")

    print("=== Writing thresholds to config ===")
    write_thresholds_to_config(thresholds)

    print("✔ Done.")


if __name__ == "__main__":
    main()
