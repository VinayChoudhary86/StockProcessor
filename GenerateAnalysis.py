# GenerateAnalysis.py
"""
GenerateAnalysis.py

- Aggregates Equity / Delivery / F&O (same preprocessing as TrainModel / ProcessData)
- Computes all derived columns (~Price, ~Del, ~OI, Delivery, 5DAD, etc.)
- Reads ML thresholds from configProcess.ini under [THRESHOLDS_<SYMBOL>]
- Applies thresholds to generate:
    - LONG_TRIGGER / SHORT_TRIGGER
    - Longs / Shorts / Longs Till Now / Shorts Till Now
- Writes:
    SYMBOL_Analysis.csv
    SYMBOL_Analysis_Excel.xlsx
- NO ML training, NO threshold extraction here.
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd
import configparser

from config_loader import load_config  # type: ignore


def clean_numeric(series):
    return (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace(r"[^\d\.\-]", "", regex=True)
        .str.strip()
        .replace("-", "0")
        .replace("", "0")
        .astype(float)
        .fillna(0.0)
    )



# ---------------- CONFIG / CONSTANTS ---------------- #

cfg = load_config()

TARGET_DIRECTORY = cfg.get("TARGET_DIRECTORY")
SD_MULTIPLIER = float(cfg.get("SD_MULTIPLIER", 1.0))
TRADING_QTY = cfg.get("TRADING_QTY", 0)
SYMBOL = cfg.get("SYMBOL", "SYMBOL")
CONFIG_PATH = cfg.get("CONFIG_PATH", None)  # optional path override

if CONFIG_PATH is None:
    CONFIG_PATH = os.path.join(os.getcwd(), "configProcess.ini")

print("Using configuration (GenerateAnalysis.py):")
print(" TARGET_DIRECTORY =", TARGET_DIRECTORY)
print(" SD_MULTIPLIER   =", SD_MULTIPLIER)
print(" TRADING_QTY     =", TRADING_QTY)
print(" SYMBOL          =", SYMBOL)
print(" CONFIG_PATH     =", CONFIG_PATH)

EQUITY_CLOSE_PRICE_COL = "close"
VWAP_COL = "vwap"
DELIVERY_QTY_RAW_COL_CLEANED = "Deliverable_Qty"
DELIVERY_QTY_FINAL_COL = "Daily_Deliverable_Qty"
DELIVERY_VALUE_COL = "Delivery"
NEW_5DAD_COL = "5DAD"
REL_DELIVERY_COL = "~Del"
PRICE_CHANGE_COL = "~Price"
OI_CHANGE_COL = "~OI"
DATE_COL_CANDIDATES = [
    "DATE",
    "DATE_",
    "TRADING_DATE",
    "TRADE_DATE",
    "TIMESTAMP",
    "DATES",
    "Date",
]

MATRIX_MAPPING = {
    (1, 1, 1): ("StrongLong", "BUY"),
    (1, 1, 0): ("LastLegOfLong", "WEAK_BUY"),
    (1, 1, -1): ("ShortCovering", "BUY"),
    (1, 0, 1): ("NewLongs", "BUY"),
    (1, 0, 0): ("NoInterest", "NO_TRADE"),
    (1, 0, -1): ("WeakShortCovering", "WEAK_BUY"),
    (1, -1, 1): ("WeakerLongs", "NO_TRADE"),
    (1, -1, 0): ("NoLongPosition", "NO_TRADE"),
    (1, -1, -1): ("WeakShortcovering", "NO_TRADE"),
    (-1, 1, 1): ("StrongShort", "SELL"),
    (-1, 1, 0): ("LastLegOfshort", "WEAK_SELL"),
    (-1, 1, -1): ("LongCovering", "SELL"),
    (-1, 0, 1): ("NewShort", "SELL"),
    (-1, 0, 0): ("NoInterest", "NO_TRADE"),
    (-1, 0, -1): ("WeakLongcovering", "WEAK_SELL"),
    (-1, -1, 1): ("WeakerShort", "WEAK_SELL"),
    (-1, -1, 0): ("NoShortPosition", "NO_TRADE"),
    (-1, -1, -1): ("WeakLongCovering", "WEAK_SELL"),
}


# ------------------------- UTIL: CLEAN DF ------------------------------

def _clean_dataframe(df, date_col_candidates, date_col_name="DATE", dayfirst=True):
    """Cleans headers, standardizes date column and coerces dates (dd-first)."""
    df.columns = (
        df.columns.str.strip()
        .str.replace(" ", "_", regex=False)
        .str.replace('"', "", regex=False)
        .str.replace(".", "", regex=False)
    )
    df = df.loc[:, ~df.columns.duplicated()]
    found_date_col = next(
        (col for col in df.columns if col.upper() in [c.upper() for c in date_col_candidates]),
        None,
    )
    if found_date_col and found_date_col != date_col_name:
        df.rename(columns={found_date_col: date_col_name}, inplace=True)
    if date_col_name in df.columns:
        df[date_col_name] = pd.to_datetime(
            df[date_col_name], errors="coerce", dayfirst=dayfirst
        )
        df.dropna(subset=[date_col_name], inplace=True)
    return df


def get_directional_signal_with_sd(series_change, sd_multiplier):
    """
    Classifies each value into 1,0,-1 based on ±(sd_multiplier * stddev).
    Returns (pd.Series of ints, threshold float).
    If not enough data (<10 non-nulls) returns zeros.
    """
    import numpy as np

    s = series_change.copy()
    valid = s.dropna()
    if len(valid) < 10:
        return pd.Series(0, index=s.index).astype(int), 0.0
    std_dev = valid.std()
    threshold = std_dev * sd_multiplier

    def classify(x):
        try:
            if x > threshold:
                return 1
            if x < -threshold:
                return -1
            return 0
        except Exception:
            return 0

    classified = s.apply(classify).fillna(0).astype(int)
    return classified, threshold


# ---------------------- BUILD BASE DATAFRAME ---------------------------

def build_base_dataframe(target_directory, sd_multiplier=SD_MULTIPLIER):
    """
    Same aggregation and derived metrics as TrainModel / ProcessData,
    but NO ML here. Returns final_df.
    """
    print("--- GenerateAnalysis: Building base dataframe ---")

    # Equity
    equity_pattern = os.path.join(target_directory, "Quote-Equity-*.csv")
    equity_files = glob.glob(equity_pattern)

    if not equity_files:
        raise FileNotFoundError(
            f"No equity files found matching pattern '{equity_pattern}' in {target_directory}"
        )

    equity_df_list = []
    print(f"Found {len(equity_files)} equity file(s).")
    for fn in equity_files:
        try:
            print(f"Reading equity: {os.path.basename(fn)}")
            df_tmp = pd.read_csv(fn, encoding="utf-8-sig")
            df_tmp = _clean_dataframe(df_tmp, DATE_COL_CANDIDATES)
            for col in df_tmp.columns:
                if df_tmp[col].dtype == "object":
                    df_tmp[col] = df_tmp[col].str.replace(",", "", regex=False)
            df_tmp = df_tmp.apply(pd.to_numeric, errors="ignore")
            equity_df_list.append(df_tmp)
        except Exception as e:
            print(f"Skipping equity file {fn} due to: {e}")

    if not equity_df_list:
        raise ValueError("Could not load any valid equity dataframes.")

    equity_df = pd.concat(equity_df_list, ignore_index=True)
    if "DATE" in equity_df.columns:
        equity_df.drop_duplicates(subset=["DATE"], keep="first", inplace=True)

    # Delivery
    delivery_pattern = os.path.join(target_directory, "*-EQ-N.csv")
    delivery_files = glob.glob(delivery_pattern)

    if not delivery_files:
        warnings.warn(
            f"No delivery files found matching pattern '{delivery_pattern}'. "
            "Delivery quantities will be zero.",
            UserWarning,
        )
        delivery_df = pd.DataFrame(columns=["DATE", DELIVERY_QTY_FINAL_COL])
    else:
        delivery_df_list = []
        print(f"Found {len(delivery_files)} delivery file(s).")
        for fn in delivery_files:
            try:
                print(f"Reading delivery: {os.path.basename(fn)}")
                df_tmp = pd.read_csv(fn, encoding="utf-8-sig")
                df_tmp = _clean_dataframe(df_tmp, DATE_COL_CANDIDATES)
                for col in df_tmp.columns:
                    if df_tmp[col].dtype == "object":
                        df_tmp[col] = df_tmp[col].str.replace(",", "", regex=False)
                df_tmp = df_tmp.apply(pd.to_numeric, errors="ignore")
                delivery_df_list.append(df_tmp)
            except Exception as e:
                print(f"Skipping delivery file {fn} due to: {e}")

        if delivery_df_list:
            delivery_df = pd.concat(delivery_df_list, ignore_index=True)
            if "DATE" in delivery_df.columns:
                delivery_df.drop_duplicates(subset=["DATE"], keep="first", inplace=True)

            if DELIVERY_QTY_RAW_COL_CLEANED in delivery_df.columns:
                delivery_df[DELIVERY_QTY_FINAL_COL] = delivery_df[DELIVERY_QTY_RAW_COL_CLEANED]
            else:
                candidates = ["Deliverable Qty", "DeliverableQty", "Deliverable Qty"]
                found = next((c for c in candidates if c in delivery_df.columns), None)
                if found:
                    delivery_df.rename(columns={found: DELIVERY_QTY_FINAL_COL}, inplace=True)
                else:
                    delivery_df[DELIVERY_QTY_FINAL_COL] = 0

            delivery_df = delivery_df[["DATE", DELIVERY_QTY_FINAL_COL]].copy()
        else:
            delivery_df = pd.DataFrame(columns=["DATE", DELIVERY_QTY_FINAL_COL])

    # F&O
    fao_files = glob.glob(os.path.join(target_directory, "*FAO*.csv"))
    aggregated_fao_df = pd.DataFrame(
        columns=["DATE", "Daily_F&O_Volume_Sum", "Daily_Open_Interest_Sum"]
    )

    if fao_files:
        list_of_dataframes = []
        for fn in fao_files:
            try:
                df_tmp = pd.read_csv(fn, encoding="utf-8-sig")
                df_tmp = _clean_dataframe(df_tmp, DATE_COL_CANDIDATES)
                list_of_dataframes.append(df_tmp)
            except Exception as e:
                print(f"Skipping F&O file {fn} due to: {e}")

        if list_of_dataframes:
            master_df = pd.concat(list_of_dataframes, ignore_index=True)
            fao_id_cols = ["DATE", "EXPIRY_DATE", "OPTION_TYPE", "STRIKE_PRICE"]
            cols_for_dedup = [c for c in fao_id_cols if c in master_df.columns]
            for col in ["Volume", "OPEN_INTEREST"]:
                if col in master_df.columns:
                    master_df[col] = clean_numeric(master_df[col])
            if len(cols_for_dedup) == 4:
                master_df.drop_duplicates(subset=cols_for_dedup, keep="first", inplace=True)
            if "DATE" in master_df.columns:
                aggregated_fao_df = (
                    master_df.groupby("DATE")
                    .agg({"Volume": "sum", "OPEN_INTEREST": "sum"})
                    .reset_index()
                )
                aggregated_fao_df.rename(
                    columns={
                        "Volume": "Daily_F&O_Volume_Sum",
                        "OPEN_INTEREST": "Daily_Open_Interest_Sum",
                    },
                    inplace=True,
                )

    # Normalize dates
    if "DATE" in equity_df.columns:
        equity_df["DATE"] = pd.to_datetime(equity_df["DATE"], errors="coerce")
    if "DATE" in delivery_df.columns:
        delivery_df["DATE"] = pd.to_datetime(delivery_df["DATE"], errors="coerce")
    if not aggregated_fao_df.empty and "DATE" in aggregated_fao_df.columns:
        aggregated_fao_df["DATE"] = pd.to_datetime(aggregated_fao_df["DATE"], errors="coerce")

    # Merge
    final_df = equity_df.merge(aggregated_fao_df, on="DATE", how="left")
    final_df = final_df.merge(delivery_df, on="DATE", how="left")

    final_df["Daily_Open_Interest_Sum"] = clean_numeric(
        final_df.get("Daily_Open_Interest_Sum", 0)
    )
    final_df[DELIVERY_QTY_FINAL_COL] = final_df[DELIVERY_QTY_FINAL_COL].fillna(0)

    if VWAP_COL not in final_df.columns:
        for cand in ["vwap", "VWAP", "Vwap"]:
            if cand in final_df.columns:
                final_df.rename(columns={cand: VWAP_COL}, inplace=True)
                break
        else:
            final_df[VWAP_COL] = 0.0
    final_df[VWAP_COL] = final_df[VWAP_COL].fillna(0)

    final_df.sort_values("DATE", inplace=True)

    if EQUITY_CLOSE_PRICE_COL not in final_df.columns:
        for cand in ["close", "Close", "CLOSE", "ltp", "LTP", "Last Price", "LastPrice"]:
            if cand in final_df.columns:
                final_df.rename(columns={cand: EQUITY_CLOSE_PRICE_COL}, inplace=True)
                break
        else:
            raise KeyError(
                "Close price column not found in equity file. Expected 'close' or similar."
            )

    final_df[EQUITY_CLOSE_PRICE_COL] = clean_numeric(final_df[EQUITY_CLOSE_PRICE_COL])

    prev_close = final_df[EQUITY_CLOSE_PRICE_COL].shift(1)
    final_df["Price_Pct_Change"] = (
        (final_df[EQUITY_CLOSE_PRICE_COL] - prev_close)
        / prev_close.replace(0, np.nan)
        * 100
    )

    delivery_qty_cleaned = clean_numeric(final_df[DELIVERY_QTY_FINAL_COL])

    vwap_cleaned = clean_numeric(final_df[VWAP_COL])

    final_df["Del_Inter"] = delivery_qty_cleaned * vwap_cleaned
    final_df[DELIVERY_VALUE_COL] = final_df["Del_Inter"] / 10000000.0

    prev_oi = final_df["Daily_Open_Interest_Sum"].shift(1)
    final_df["OI_Pct_Change"] = (
        (final_df["Daily_Open_Interest_Sum"] - prev_oi)
        / prev_oi.replace(0, 1e-6)
        * 100
    )
    final_df["Absolute_OI_Change"] = final_df["Daily_Open_Interest_Sum"] - prev_oi

    final_df["Longs"] = 0.0
    final_df["Shorts"] = 0.0

    final_df[NEW_5DAD_COL] = (
        final_df[DELIVERY_VALUE_COL].shift(1).rolling(window=5, min_periods=5).mean()
    )
    final_df[REL_DELIVERY_COL] = np.where(
        final_df[NEW_5DAD_COL] != 0,
        (final_df[DELIVERY_VALUE_COL] / final_df[NEW_5DAD_COL]) * 100.0,
        np.nan,
    )

    for col in [
        "Price_Pct_Change",
        "OI_Pct_Change",
        REL_DELIVERY_COL,
        DELIVERY_VALUE_COL,
        NEW_5DAD_COL,
    ]:
        if col in final_df.columns:
            final_df[col] = final_df[col].round(2)
    for col in [
        "Absolute_OI_Change",
        "Longs",
        "Shorts",
        "Longs Till Now",
        "Shorts Till Now",
    ]:
        if col in final_df.columns:
            final_df[col] = final_df[col].round(0)

    final_df.rename(
        columns={"Price_Pct_Change": PRICE_CHANGE_COL, "OI_Pct_Change": OI_CHANGE_COL},
        inplace=True,
    )

    price_series = final_df[PRICE_CHANGE_COL].fillna(0)
    del_series = final_df[REL_DELIVERY_COL].fillna(0)
    oi_series = final_df[OI_CHANGE_COL].fillna(0)

    price_dir, _ = get_directional_signal_with_sd(price_series, sd_multiplier)
    del_dir, _ = get_directional_signal_with_sd(del_series, sd_multiplier)
    oi_dir, _ = get_directional_signal_with_sd(oi_series, sd_multiplier)

    final_df["Price_Dir"] = price_dir
    final_df["Delivery_Dir"] = del_dir
    final_df["OI_Dir"] = oi_dir

    final_df["Scenario_Tuple"] = list(
        zip(final_df["Price_Dir"], final_df["Delivery_Dir"], final_df["OI_Dir"])
    )

    def map_scenario_tuple(x):
        return MATRIX_MAPPING.get(x, ("Unknown", "NO_TRADE"))

    mapped = final_df["Scenario_Tuple"].apply(map_scenario_tuple)
    final_df["F&O_Conclusion"] = mapped.apply(lambda t: t[0])
    final_df["Trade_Signal"] = mapped.apply(lambda t: t[1])

    return final_df.reset_index(drop=True)


# ---------------------- LOAD THRESHOLDS FROM CONFIG -------------------

def load_thresholds_from_config():
    section = f"THRESHOLDS_{SYMBOL}"
    config = configparser.ConfigParser()

    if not os.path.exists(CONFIG_PATH):
        print(f"Config file not found: {CONFIG_PATH}")
        return {}

    config.read(CONFIG_PATH)
    if not config.has_section(section):
        print(f"Threshold section [{section}] not found in config.")
        return {}

    thresholds = {}
    for k, v in config.items(section):
        try:
            thresholds[k] = float(v)
        except Exception:
            pass

    print(f"\nLoaded thresholds from [{section}]:")
    for k, v in thresholds.items():
        print(f"  {k} = {v}")

    return thresholds


# ---------------------- APPLY THRESHOLDS & WRITE FILES ----------------

def apply_thresholds_and_generate_files(target_directory, sd_multiplier=SD_MULTIPLIER):
    final_df = build_base_dataframe(target_directory, sd_multiplier)
    thresholds = load_thresholds_from_config()

    price_long = thresholds.get("price_long", None)
    del_long = thresholds.get("del_long", None)
    oi_long = thresholds.get("oi_long", None)

    price_short = thresholds.get("price_short", None)
    del_short = thresholds.get("del_short", None)
    oi_short = thresholds.get("oi_short", None)

    # Bool columns
    final_df["Above_Price_Thr"] = (
        final_df[PRICE_CHANGE_COL] > price_long if price_long is not None else False
    )
    final_df["Above_Del_Thr"] = (
        final_df[REL_DELIVERY_COL] > del_long if del_long is not None else False
    )
    final_df["Above_OI_Thr"] = (
        final_df[OI_CHANGE_COL] > oi_long if oi_long is not None else False
    )

    final_df["Below_Price_Thr"] = (
        final_df[PRICE_CHANGE_COL] < price_short if price_short is not None else False
    )
    final_df["Below_Del_Thr"] = (
        final_df[REL_DELIVERY_COL] < del_short if del_short is not None else False
    )
    final_df["Below_OI_Thr"] = (
        final_df[OI_CHANGE_COL] < oi_short if oi_short is not None else False
    )

    final_df["LONG_TRIGGER"] = (
        final_df["Above_Price_Thr"] & final_df["Above_Del_Thr"] & final_df["Above_OI_Thr"]
    )
    final_df["SHORT_TRIGGER"] = (
        final_df["Below_Price_Thr"] & final_df["Below_Del_Thr"] & final_df["Below_OI_Thr"]
    )

    # Longs / Shorts from Absolute_OI_Change when trigger is True
    final_df["Longs"] = 0.0
    final_df["Shorts"] = 0.0

    final_df.loc[final_df["LONG_TRIGGER"], "Longs"] = (
        final_df.loc[final_df["LONG_TRIGGER"], "Absolute_OI_Change"].abs()
    )
    final_df.loc[final_df["SHORT_TRIGGER"], "Shorts"] = (
        final_df.loc[final_df["SHORT_TRIGGER"], "Absolute_OI_Change"].abs()
    )

    final_df["Longs Till Now"] = final_df["Longs"].cumsum()
    final_df["Shorts Till Now"] = final_df["Shorts"].cumsum()

    # Same layout / output as original ProcessData
    DATE_DISPLAY_COL = "Date Display (dd-MM-yyyy)"
    final_df[DATE_DISPLAY_COL] = final_df["DATE"].dt.strftime("%d-%m-%Y")

    BLANK_COL = " "
    COLS_TO_MOVE_TO_END = [
        "Del_Inter",
        DELIVERY_VALUE_COL,
        NEW_5DAD_COL,
        BLANK_COL,
        PRICE_CHANGE_COL,
        REL_DELIVERY_COL,
        OI_CHANGE_COL,
        "Absolute_OI_Change",
        "Longs",
        "Shorts",
        "Longs Till Now",
        "Shorts Till Now",
        "Price_Dir",
        "Delivery_Dir",
        "OI_Dir",
        "Scenario_Tuple",
        "F&O_Conclusion",
        "Trade_Signal",
        "Above_Price_Thr",
        "Above_Del_Thr",
        "Above_OI_Thr",
        "Below_Price_Thr",
        "Below_Del_Thr",
        "Below_OI_Thr",
        "LONG_TRIGGER",
        "SHORT_TRIGGER",
        DATE_DISPLAY_COL,
    ]

    all_cols = final_df.columns.tolist()
    cols_to_keep_first = [c for c in all_cols if c not in COLS_TO_MOVE_TO_END]

    final_df[BLANK_COL] = np.nan
    final_order = cols_to_keep_first + [c for c in COLS_TO_MOVE_TO_END if c in final_df.columns]
    final_df = final_df.loc[:, final_order]

    # Save CSV
    output_filename_csv = os.path.join(target_directory, f"{SYMBOL}_Analysis.csv")
    final_df.to_csv(output_filename_csv, index=False)
    print(f"Data analysis saved to: {output_filename_csv}")

    # Save Excel with styling
    output_filename_xlsx = os.path.join(target_directory, f"{SYMBOL}_Analysis_Excel.xlsx")
    try:
        with pd.ExcelWriter(output_filename_xlsx, engine="openpyxl") as writer:
            final_df.to_excel(writer, index=False, sheet_name="Analysis")

            workbook = writer.book
            worksheet = writer.sheets["Analysis"]

            from openpyxl.styles import PatternFill, Font

            header_fill = PatternFill(start_color="0000FF", end_color="0000FF", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)

            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font

            worksheet.freeze_panes = "A2"

        print(f"Excel with colored frozen header saved to: {output_filename_xlsx}")
    except ImportError:
        warnings.warn("openpyxl not installed. Skipping Excel styling.", UserWarning)
    except Exception as e:
        print(f"Could not save styled Excel file: {e}")

    return final_df


# --------------------------- ENTRY POINT --------------------------------

if __name__ == "__main__":
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1400)
    pd.set_option("display.float_format", "{:.2f}".format)

    df = apply_thresholds_and_generate_files(TARGET_DIRECTORY, SD_MULTIPLIER)
    if df is not None and not df.empty:
        print("Analysis produced rows:", len(df))
    else:
        print("No analysis output produced; check input files and config.")
