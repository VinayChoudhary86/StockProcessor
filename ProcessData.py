# NSE34.py
"""
NSE_process_with_config.py

Full script: reads TARGET_DIRECTORY, EQUITY_FILE_NAME and DELIVERY_FILE_NAME
from configProcess.ini (via config_loader) and runs the analysis pipeline.
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd

from config_loader import load_config # type: ignore

# Load shared config ONCE
cfg = load_config()

TARGET_DIRECTORY = cfg["TARGET_DIRECTORY"]
EQUITY_FILE_NAME = cfg["EQUITY_FILE_NAME"]
DELIVERY_FILE_NAME = cfg["DELIVERY_FILE_NAME"]
SD_MULTIPLIER = cfg["SD_MULTIPLIER"]
TRADING_QTY = cfg["TRADING_QTY"]
SYMBOL = cfg["SYMBOL"]

print("Using configuration:")
print(" TARGET_DIRECTORY =", TARGET_DIRECTORY)
print(" EQUITY_FILE_NAME =", EQUITY_FILE_NAME)
print(" DELIVERY_FILE_NAME =", DELIVERY_FILE_NAME)
print(" SD_MULTIPLIER =", SD_MULTIPLIER)
print(" TRADING_QTY =", TRADING_QTY)

# ------------------------- CONSTANT / COLUMN NAMES ---------------------
EQUITY_CLOSE_PRICE_COL = 'close'
VWAP_COL = 'vwap'
DELIVERY_QTY_RAW_COL_CLEANED = 'Deliverable_Qty'
DELIVERY_QTY_FINAL_COL = 'Daily_Deliverable_Qty'
DELIVERY_VALUE_COL = 'Delivery'
NEW_5DAD_COL = '5DAD'
REL_DELIVERY_COL = '~Del'
PRICE_CHANGE_COL = '~Price'
OI_CHANGE_COL = '~OI'
DATE_COL_CANDIDATES = ['DATE', 'DATE_', 'TRADING_DATE', 'TRADE_DATE', 'TIMESTAMP', 'DATES', 'Date']

# ------------------------- MATRIX MAPPING ------------------------------
MATRIX_MAPPING = {
    (1,1,1): ('StrongLong','BUY'),
    (1,1,0): ('LastLegOfLong','WEAK_BUY'),
    (1,1,-1): ('ShortCovering','BUY'),
    (1,0,1): ('NewLongs','BUY'),
    (1,0,0): ('NoInterest','NO_TRADE'),
    (1,0,-1): ('WeakShortCovering','WEAK_BUY'),
    (1,-1,1): ('WeakerLongs','NO_TRADE'),
    (1,-1,0): ('NoLongPosition','NO_TRADE'),
    (1,-1,-1): ('WeakShortcovering','NO_TRADE'),
    (-1,1,1): ('StrongShort','SELL'),
    (-1,1,0): ('LastLegOfshort','WEAK_SELL'),
    (-1,1,-1): ('LongCovering','SELL'),
    (-1,0,1): ('NewShort','SELL'),
    (-1,0,0): ('NoInterest','NO_TRADE'),
    (-1,0,-1): ('WeakLongcovering','WEAK_SELL'),
    (-1,-1,1): ('WeakerShort','WEAK_SELL'),
    (-1,-1,0): ('NoShortPosition','NO_TRADE'),
    (-1,-1,-1): ('WeakLongCovering','WEAK_SELL')
}

# ------------------------- UTIL: CLEAN DF ------------------------------
def _clean_dataframe(df, date_col_candidates, date_col_name='DATE', dayfirst=True):
    """Cleans headers, standardizes date column and coerces dates."""
    df.columns = (
        df.columns.str.strip()
        .str.replace(' ', '_', regex=False)
        .str.replace('"', '', regex=False)
        .str.replace('.', '', regex=False)
    )
    df = df.loc[:, ~df.columns.duplicated()]
    found_date_col = next((col for col in df.columns if col.upper() in [c.upper() for c in date_col_candidates]), None)
    if found_date_col and found_date_col != date_col_name:
        df.rename(columns={found_date_col: date_col_name}, inplace=True)
    if date_col_name in df.columns:
        df[date_col_name] = pd.to_datetime(df[date_col_name], errors='coerce', dayfirst=dayfirst)
        df.dropna(subset=[date_col_name], inplace=True)
    return df

# ------------------ DIRECTIONAL SIGNAL UTILITY -------------------------
def get_directional_signal_with_sd(series_change, sd_multiplier):
    """
    Classifies each value into 1,0,-1 based on ±(sd_multiplier * stddev).
    Returns (pd.Series of ints, threshold float).
    If not enough data (<10 non-nulls) returns zeros.
    """
    s = series_change.copy()
    valid = s.dropna()
    if len(valid) < 10:
        return pd.Series(0, index=s.index).astype(int), 0.0
    std_dev = valid.std()
    threshold = std_dev * sd_multiplier
    def classify(x):
        try:
            if x > threshold: return 1
            if x < -threshold: return -1
            return 0
        except Exception:
            return 0
    classified = s.apply(classify).fillna(0).astype(int)
    return classified, threshold

# ---------------------- I. PROCESS ANALYSIS DATA -----------------------
def process_analysis_data(target_directory, equity_file_name, delivery_file_name, sd_multiplier=SD_MULTIPLIER, trading_qty=TRADING_QTY):
    """Aggregates, cleans, computes metrics and saves analysis CSV."""
    print("--- 1. Starting Data Processing and Calculation ---")
    equity_file_path = os.path.join(target_directory, equity_file_name)
    delivery_file_path = os.path.join(target_directory, delivery_file_name)

    if not os.path.exists(equity_file_path) or not os.path.exists(delivery_file_path):
        raise FileNotFoundError(f"Required files not found in {target_directory}:\n {equity_file_path}\n {delivery_file_path}")

    # Aggregate F&O files if any (optional)
    fao_files = glob.glob(os.path.join(target_directory, '*FAO*.csv'))
    aggregated_fao_df = pd.DataFrame(columns=['DATE', 'Daily_F&O_Volume_Sum', 'Daily_Open_Interest_Sum'])
    if fao_files:
        list_of_dataframes = []
        for fn in fao_files:
            try:
                df_tmp = pd.read_csv(fn, encoding='utf-8-sig')
                df_tmp = _clean_dataframe(df_tmp, DATE_COL_CANDIDATES)
                list_of_dataframes.append(df_tmp)
            except Exception as e:
                print(f"Skipping F&O file {fn} due to: {e}")
        if list_of_dataframes:
            master_df = pd.concat(list_of_dataframes, ignore_index=True)
            fao_id_cols = ['DATE','EXPIRY_DATE','OPTION_TYPE','STRIKE_PRICE']
            cols_for_dedup = [c for c in fao_id_cols if c in master_df.columns]
            for col in ['Volume','OPEN_INTEREST']:
                if col in master_df.columns:
                    cleaned = (master_df[col].astype(str)
                               .str.replace(',', '', regex=False)
                               .str.replace(r'[^\d\.\-]', '', regex=True)
                               .str.strip())
                    master_df[col] = pd.to_numeric(cleaned, errors='coerce').fillna(0)
            if len(cols_for_dedup) == 4:
                master_df.drop_duplicates(subset=cols_for_dedup, keep='first', inplace=True)
            if 'DATE' in master_df.columns:
                aggregated_fao_df = master_df.groupby('DATE').agg({'Volume':'sum','OPEN_INTEREST':'sum'}).reset_index()
                aggregated_fao_df.rename(columns={'Volume':'Daily_F&O_Volume_Sum','OPEN_INTEREST':'Daily_Open_Interest_Sum'}, inplace=True)

    print("Reading:", equity_file_path)
    equity_df = pd.read_csv(equity_file_path, encoding='utf-8-sig')
    equity_df = _clean_dataframe(equity_df, DATE_COL_CANDIDATES)

    print("Reading:", delivery_file_path)
    delivery_df = pd.read_csv(delivery_file_path, encoding='utf-8-sig')
    delivery_df = _clean_dataframe(delivery_df, DATE_COL_CANDIDATES)

    if DELIVERY_QTY_RAW_COL_CLEANED in delivery_df.columns:
        delivery_df[DELIVERY_QTY_FINAL_COL] = delivery_df[DELIVERY_QTY_RAW_COL_CLEANED]
    else:
        candidates = ['Deliverable Qty', 'Deliverable_Qty', 'DeliverableQty', 'Deliverable Qty']
        found = next((c for c in candidates if c in delivery_df.columns), None)
        if found:
            delivery_df[DELIVERY_QTY_FINAL_COL] = delivery_df[found]
        else:
            delivery_df[DELIVERY_QTY_FINAL_COL] = 0

    if 'DATE' not in delivery_df.columns and 'Date' in delivery_df.columns:
        delivery_df.rename(columns={'Date':'DATE'}, inplace=True)

    delivery_df = delivery_df[['DATE', DELIVERY_QTY_FINAL_COL]].copy()

    final_df = equity_df.merge(aggregated_fao_df, on='DATE', how='left')
    final_df = final_df.merge(delivery_df, on='DATE', how='left')

    final_df['Daily_Open_Interest_Sum'] = final_df.get('Daily_Open_Interest_Sum', 0).fillna(0)
    final_df[DELIVERY_QTY_FINAL_COL] = final_df[DELIVERY_QTY_FINAL_COL].fillna(0)

    if VWAP_COL not in final_df.columns:
        for cand in ['vwap','VWAP','Vwap']:
            if cand in final_df.columns:
                final_df.rename(columns={cand:VWAP_COL}, inplace=True)
                break
        else:
            final_df[VWAP_COL] = 0.0
    final_df[VWAP_COL] = final_df[VWAP_COL].fillna(0)

    final_df.sort_values('DATE', inplace=True)

    if EQUITY_CLOSE_PRICE_COL not in final_df.columns:
        for cand in ['close','Close','CLOSE','ltp','LTP','Last Price','LastPrice']:
            if cand in final_df.columns:
                final_df.rename(columns={cand:EQUITY_CLOSE_PRICE_COL}, inplace=True)
                break
        else:
            raise KeyError("Close price column not found in equity file. Expected 'close' or similar.")

    prev_close = final_df[EQUITY_CLOSE_PRICE_COL].shift(1)
    final_df['Price_Pct_Change'] = ((final_df[EQUITY_CLOSE_PRICE_COL] - prev_close) / prev_close.replace(0,np.nan)) * 100

    delivery_qty_cleaned = (
        final_df[DELIVERY_QTY_FINAL_COL].astype(str)
        .str.replace(',', '', regex=False)
        .str.replace(r'[^\d\.\-]', '', regex=True)
        .replace('', '0')
        .astype(float)
        .fillna(0)
    )

    vwap_cleaned = (
        final_df[VWAP_COL].astype(str)
        .str.replace(',', '', regex=False)
        .str.replace(r'[^\d\.\-]', '', regex=True)
        .replace('', '0')
        .astype(float)
        .fillna(0)
    )

    final_df['Del_Inter'] = delivery_qty_cleaned * vwap_cleaned
    final_df[DELIVERY_VALUE_COL] = final_df['Del_Inter'] / 10000000.0

    prev_oi = final_df['Daily_Open_Interest_Sum'].shift(1)
    final_df['OI_Pct_Change'] = ((final_df['Daily_Open_Interest_Sum'] - prev_oi) / prev_oi.replace(0,1e-6)) * 100
    final_df['Absolute_OI_Change'] = final_df['Daily_Open_Interest_Sum'] - prev_oi

    final_df['Longs'] = 0.0; final_df['Shorts'] = 0.0
    price_up = final_df['Price_Pct_Change'] > 0
    price_down = final_df['Price_Pct_Change'] < 0
    oi_up = final_df['Absolute_OI_Change'] > 0
    oi_down = final_df['Absolute_OI_Change'] < 0

    final_df[NEW_5DAD_COL] = final_df[DELIVERY_VALUE_COL].shift(1).rolling(window=5, min_periods=5).mean()
    final_df[REL_DELIVERY_COL] = np.where(final_df[NEW_5DAD_COL] != 0,
                                         ((final_df[DELIVERY_VALUE_COL]) / final_df[NEW_5DAD_COL]) * 100.0,
                                         np.nan)

    for col in ['Price_Pct_Change','OI_Pct_Change', REL_DELIVERY_COL, DELIVERY_VALUE_COL, NEW_5DAD_COL]:
        if col in final_df.columns:
            final_df[col] = final_df[col].round(2)
    for col in ['Absolute_OI_Change','Longs','Shorts','Longs Till Now','Shorts Till Now']:
        if col in final_df.columns:
            final_df[col] = final_df[col].round(0)

    final_df.rename(columns={'Price_Pct_Change': PRICE_CHANGE_COL, 'OI_Pct_Change': OI_CHANGE_COL}, inplace=True)

    price_series = final_df[PRICE_CHANGE_COL].fillna(0)
    del_series = final_df[REL_DELIVERY_COL].fillna(0)
    oi_series = final_df[OI_CHANGE_COL].fillna(0)

    price_dir, _ = get_directional_signal_with_sd(price_series, sd_multiplier)
    del_dir, _ = get_directional_signal_with_sd(del_series, sd_multiplier)
    oi_dir, _ = get_directional_signal_with_sd(oi_series, sd_multiplier)

    final_df['Price_Dir'] = price_dir
    final_df['Delivery_Dir'] = del_dir
    final_df['OI_Dir'] = oi_dir

    final_df['Scenario_Tuple'] = list(zip(final_df['Price_Dir'], final_df['Delivery_Dir'], final_df['OI_Dir']))

    def map_scenario_tuple(x):
        return MATRIX_MAPPING.get(x, ('Unknown','NO TRADE'))
    mapped = final_df['Scenario_Tuple'].apply(map_scenario_tuple)
    final_df['F&O_Conclusion'] = mapped.apply(lambda t: t[0])
    final_df['Trade_Signal'] = mapped.apply(lambda t: t[1])

    # ------------------ NEW LONGS / SHORTS LOGIC (BASED ON F&O_Conclusion) ------------------
    final_df['Longs'] = 0
    final_df['Shorts'] = 0

    long_conditions = ["NewLongs", "LongCovering", "StrongLong", "LastLegOfLong"]
    short_conditions = ["NewShorts", "ShortCovering", "StrongShort", "LastLegOfShort"]

    final_df.loc[final_df['F&O_Conclusion'].isin(long_conditions), 'Longs'] = \
        final_df['Absolute_OI_Change']

    final_df.loc[final_df['F&O_Conclusion'].isin(short_conditions), 'Shorts'] = \
        final_df['Absolute_OI_Change']

    final_df['Longs'] = final_df['Longs'].fillna(0)
    final_df['Shorts'] = final_df['Shorts'].fillna(0)

    final_df['Longs Till Now'] = final_df['Longs'].cumsum()
    final_df['Shorts Till Now'] = final_df['Shorts'].cumsum()

    BLANK_COL = ' '
    COLS_TO_MOVE_TO_END = ['Del_Inter', DELIVERY_VALUE_COL, NEW_5DAD_COL, BLANK_COL,
                           PRICE_CHANGE_COL, REL_DELIVERY_COL, OI_CHANGE_COL,
                           'Absolute_OI_Change','Longs','Shorts','Longs Till Now','Shorts Till Now',
                           'Price_Dir','Delivery_Dir','OI_Dir','Scenario_Tuple','F&O_Conclusion','Trade_Signal']

    all_cols = final_df.columns.tolist()
    cols_to_keep_first = [c for c in all_cols if c not in COLS_TO_MOVE_TO_END]

    final_df[BLANK_COL] = np.nan
    final_order = cols_to_keep_first + [c for c in COLS_TO_MOVE_TO_END if c in final_df.columns]
    final_df = final_df.loc[:, final_order]

    # ---------------- SAVE CSV ----------------
    output_filename_csv = os.path.join(target_directory, f"{SYMBOL}_Analysis.csv")
    final_df.to_csv(output_filename_csv, index=False)
    print(f"Data analysis saved to: {output_filename_csv}")

    # ---------------- SAVE STYLED EXCEL (HEADER BLUE, TEXT WHITE, FROZEN HEADER) ----------------
    output_filename_xlsx = os.path.join(target_directory, f"{SYMBOL}_Analysis_Excel.xlsx")

    with pd.ExcelWriter(output_filename_xlsx, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False, sheet_name='Analysis')

        workbook  = writer.book
        worksheet = writer.sheets['Analysis']

        from openpyxl.styles import PatternFill, Font

        # Blue background, white bold font
        header_fill = PatternFill(start_color="0000FF", end_color="0000FF", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        # Style header row
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font

        # Freeze header row
        worksheet.freeze_panes = "A2"

    print(f"Excel with colored frozen header saved to: {output_filename_xlsx}")

    return final_df.reset_index(drop=True)

# --------------------------- ENTRY POINT --------------------------------
if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1400)
    pd.set_option('display.float_format', '{:.2f}'.format)

    analysis_df = process_analysis_data(TARGET_DIRECTORY, EQUITY_FILE_NAME, DELIVERY_FILE_NAME, SD_MULTIPLIER, TRADING_QTY)

    if analysis_df is not None and not analysis_df.empty:
        print("Analysis produced rows:", len(analysis_df))
    else:
        print("No analysis output produced; check input files and config.")
