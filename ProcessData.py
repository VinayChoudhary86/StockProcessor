# ProcessData.py
"""
NSE_process_with_config.py (renamed / patched)
Full script: reads TARGET_DIRECTORY, SD_MULTIPLIER, and SYMBOL 
from configProcess.ini (via config_loader) and runs the analysis pipeline,
aggregating equity files and delivery/FAO files, computing metrics,
and training/applying an ML pipeline to predict Longs/Shorts buildup.
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, KFold, cross_val_score

# Assuming config_loader is in the same directory or accessible via PYTHONPATH
from config_loader import load_config # type: ignore
from sklearn.preprocessing import StandardScaler # Added import for clarity

# Load shared config ONCE
cfg = load_config()

TARGET_DIRECTORY = cfg.get("TARGET_DIRECTORY")
EQUITY_FILE_NAME = cfg.get("EQUITY_FILE_NAME") # Loaded but may be ignored
DELIVERY_FILE_NAME = cfg.get("DELIVERY_FILE_NAME") # Loaded but may be ignored
SD_MULTIPLIER = float(cfg.get("SD_MULTIPLIER", 1.0))
TRADING_QTY = cfg.get("TRADING_QTY", 0)
SYMBOL = cfg.get("SYMBOL", "SYMBOL")

print("Using configuration (Note: EQUITY_FILE_NAME and DELIVERY_FILE_NAME may be overwritten by patterns):")
print(" TARGET_DIRECTORY =", TARGET_DIRECTORY)
print(" SD_MULTIPLIER =", SD_MULTIPLIER)
print(" TRADING_QTY =", TRADING_QTY)
print(" SYMBOL =", SYMBOL)

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

# ------------------------- MATRIX MAPPING (kept for fallback/explainability) --------------
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

# --- FIX: Robust Conversion Function ---
def robust_to_numeric(series):
    """
    Converts series data by stripping commas and coercing to numeric, handling errors.
    This is the core fix for 'ValueError: could not convert string to float: "13,594.83"'.
    """
    return pd.to_numeric(series.astype(str).str.replace(',', '', regex=False), errors='coerce') 
# ----------------------------------------


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
def process_analysis_data(target_directory, sd_multiplier=SD_MULTIPLIER, trading_qty=TRADING_QTY):
    """
    Aggregates data from multiple files based on patterns, cleans, 
    computes metrics, trains ML models (Option D) to predict Longs/Shorts
    and saves analysis CSV/Excel.
    """
    print("--- 1. Starting Data Processing and Calculation (Aggregating Files) ---")

    # --- 1.1 Load Equity Data (Files starting with "Quote-Equity-") ---
    equity_pattern = os.path.join(target_directory, "Quote-Equity-*.csv")
    equity_files = glob.glob(equity_pattern)
    
    if not equity_files:
        raise FileNotFoundError(f"No equity files found matching pattern '{equity_pattern}' in {target_directory}")

    equity_df_list = []
    print(f"Found {len(equity_files)} equity file(s).")
    for fn in equity_files:
        try:
            print(f"Reading equity: {os.path.basename(fn)}")
            df_tmp = pd.read_csv(fn, encoding='utf-8-sig')
            df_tmp = _clean_dataframe(df_tmp, DATE_COL_CANDIDATES)
            equity_df_list.append(df_tmp)
        except Exception as e:
            print(f"Skipping equity file {fn} due to: {e}")
            
    if not equity_df_list:
        raise ValueError("Could not load any valid equity dataframes.")

    # Merge and deduplicate equity data
    equity_df = pd.concat(equity_df_list, ignore_index=True)
    if 'DATE' in equity_df.columns:
        equity_df.drop_duplicates(subset=['DATE', EQUITY_CLOSE_PRICE_COL], keep='first', inplace=True)
    print(f"Successfully loaded and merged {len(equity_df_list)} equity dataframes. Total rows: {len(equity_df)}")

    # --- 1.2 Load Delivery Data (Files ending with "-EQ-N.csv") ---
    delivery_pattern = os.path.join(target_directory, "*-EQ-N.csv")
    delivery_files = glob.glob(delivery_pattern)
    
    if not delivery_files:
        warnings.warn(f"No delivery files found matching pattern '{delivery_pattern}'. Delivery quantities will be zero.", UserWarning)
        delivery_df = pd.DataFrame(columns=['DATE', DELIVERY_QTY_FINAL_COL])
    else:
        delivery_df_list = []
        print(f"Found {len(delivery_files)} delivery file(s).")
        for fn in delivery_files:
            try:
                print(f"Reading delivery: {os.path.basename(fn)}")
                df_tmp = pd.read_csv(fn, encoding='utf-8-sig')
                df_tmp = _clean_dataframe(df_tmp, DATE_COL_CANDIDATES)
                delivery_df_list.append(df_tmp)
            except Exception as e:
                print(f"Skipping delivery file {fn} due to: {e}")

        if delivery_df_list:
            delivery_df = pd.concat(delivery_df_list, ignore_index=True)
            if 'DATE' in delivery_df.columns:
                delivery_df.drop_duplicates(subset=['DATE'], keep='first', inplace=True)
            print(f"Successfully loaded and merged {len(delivery_df_list)} delivery dataframes. Total rows: {len(delivery_df)}")
            
            # Standardize the delivery quantity column
            if DELIVERY_QTY_RAW_COL_CLEANED in delivery_df.columns:
                delivery_df[DELIVERY_QTY_FINAL_COL] = delivery_df[DELIVERY_QTY_RAW_COL_CLEANED]
            else:
                candidates = ['Deliverable Qty', 'DeliverableQty', 'Deliverable Qty']
                found = next((c for c in candidates if c in delivery_df.columns), None)
                if found:
                    delivery_df.rename(columns={found: DELIVERY_QTY_FINAL_COL}, inplace=True)
                else:
                    delivery_df[DELIVERY_QTY_FINAL_COL] = 0
            
            delivery_df = delivery_df[['DATE', DELIVERY_QTY_FINAL_COL]].copy()
        else:
            delivery_df = pd.DataFrame(columns=['DATE', DELIVERY_QTY_FINAL_COL])

    # --- 1.3 Aggregate F&O files (Existing Logic) ---
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
            
            # FIX: Use robust_to_numeric for F&O volume/OI
            for col in ['Volume','OPEN_INTEREST']:
                if col in master_df.columns:
                    master_df[col] = robust_to_numeric(master_df[col]).fillna(0)
                    
            if len(cols_for_dedup) == 4:
                master_df.drop_duplicates(subset=cols_for_dedup, keep='first', inplace=True)
            if 'DATE' in master_df.columns:
                aggregated_fao_df = master_df.groupby('DATE').agg({'Volume':'sum','OPEN_INTEREST':'sum'}).reset_index()
                aggregated_fao_df.rename(columns={'Volume':'Daily_F&O_Volume_Sum','OPEN_INTEREST':'Daily_Open_Interest_Sum'}, inplace=True)
    
    # --- 1.4 Merge and Compute Metrics ---
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

    # =========================================================================
    # FIX: Robust Numeric Conversion for core raw columns
    # =========================================================================
    # 1. Close Price
    final_df[EQUITY_CLOSE_PRICE_COL] = robust_to_numeric(final_df[EQUITY_CLOSE_PRICE_COL])
    # FIX: Replaced .fillna(method='ffill') with .ffill().fillna(0)
    final_df[EQUITY_CLOSE_PRICE_COL] = final_df[EQUITY_CLOSE_PRICE_COL].ffill().fillna(0) # Line 257

    # 2. VWAP
    final_df[VWAP_COL] = robust_to_numeric(final_df[VWAP_COL])
    # FIX: Replaced .fillna(method='ffill') with .ffill().fillna(0)
    final_df[VWAP_COL] = final_df[VWAP_COL].ffill().fillna(0) # Line 261
    
    # 3. Delivery Quantity
    final_df[DELIVERY_QTY_FINAL_COL] = robust_to_numeric(final_df[DELIVERY_QTY_FINAL_COL]).fillna(0)
    
    # NOTE: The explicit cleaning for F&O volume/OI was done in section 1.3

    prev_close = final_df[EQUITY_CLOSE_PRICE_COL].shift(1)
    final_df['Price_Pct_Change'] = ((final_df[EQUITY_CLOSE_PRICE_COL] - prev_close) / prev_close.replace(0,np.nan)) * 100

    # Simplify Del_Inter calculation using the now-numeric columns
    final_df['Del_Inter'] = final_df[DELIVERY_QTY_FINAL_COL] * final_df[VWAP_COL]
    final_df[DELIVERY_VALUE_COL] = final_df['Del_Inter'] / 10000000.0

    prev_oi = final_df['Daily_Open_Interest_Sum'].shift(1)
    final_df['OI_Pct_Change'] = ((final_df['Daily_Open_Interest_Sum'] - prev_oi) / prev_oi.replace(0,1e-6)) * 100
    final_df['Absolute_OI_Change'] = final_df['Daily_Open_Interest_Sum'] - prev_oi

    final_df['Longs'] = 0.0; final_df['Shorts'] = 0.0
    
    # Calculate 5-Day Average Delivery
    final_df[NEW_5DAD_COL] = final_df[DELIVERY_VALUE_COL].shift(1).rolling(window=5, min_periods=5).mean()
    # Calculate Relative Delivery
    final_df[REL_DELIVERY_COL] = np.where(final_df[NEW_5DAD_COL] != 0,
                                         ((final_df[DELIVERY_VALUE_COL]) / final_df[NEW_5DAD_COL]) * 100.0,
                                         np.nan)

    # Rounding columns
    for col in ['Price_Pct_Change','OI_Pct_Change', REL_DELIVERY_COL, DELIVERY_VALUE_COL, NEW_5DAD_COL]:
        if col in final_df.columns:
            final_df[col] = final_df[col].round(2)
    for col in ['Absolute_OI_Change','Longs','Shorts','Longs Till Now','Shorts Till Now']:
        if col in final_df.columns:
            final_df[col] = final_df[col].round(0)

    final_df.rename(columns={'Price_Pct_Change': PRICE_CHANGE_COL, 'OI_Pct_Change': OI_CHANGE_COL}, inplace=True)

    # Directional Signals (existing SD-based dirs, preserved for features & fallback)
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

    # ------------------ START: MACHINE-LEARNING LONGS/SHORTS (Option D) ------------------
    # Requirements: scikit-learn, joblib. Optional: xgboost for better performance.
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        from sklearn.metrics import classification_report, mean_absolute_error
        # StandardScaler is already imported
        import joblib
        try:
            from xgboost import XGBClassifier, XGBRegressor  # optional, faster/more performant
            XGB_AVAILABLE = True
        except Exception:
            XGB_AVAILABLE = False
    except Exception as e:
        # If sklearn/joblib not installed, gracefully fallback to rule-based logic
        print("sklearn or joblib not available:", e)
        XGB_AVAILABLE = False
        # Fallback simple logic (same as original)
        final_df['Longs'] = 0
        final_df['Shorts'] = 0
        long_conditions = ["NewLongs", "LongCovering", "StrongLong", "LastLegOfLong"]
        short_conditions = ["NewShort", "ShortCovering", "StrongShort", "LastLegOfshort"] 
        final_df.loc[final_df['F&O_Conclusion'].isin(long_conditions), 'Longs'] = final_df['Absolute_OI_Change']
        final_df.loc[final_df['F&O_Conclusion'].isin(short_conditions), 'Shorts'] = final_df['Absolute_OI_Change']
        final_df['Longs'] = final_df['Longs'].fillna(0)
        final_df['Shorts'] = final_df['Shorts'].fillna(0)
        final_df['Longs Till Now'] = final_df['Longs'].cumsum()
        final_df['Shorts Till Now'] = final_df['Shorts'].cumsum()
    else:
        # ML hyperparameters (tweak these as required)
        FUTURE_DAYS = int(cfg.get("ML_FUTURE_DAYS", 3))        # N: predict OI/returns over next N days
        RETURN_THRESHOLD = float(cfg.get("ML_RETURN_THRESHOLD", 0.01))  # 1% future return threshold for label creation
        OI_QUANTILE = float(cfg.get("ML_OI_QUANTILE", 0.6))      # percentile to choose OI change threshold
        MIN_TRAIN_ROWS = int(cfg.get("ML_MIN_TRAIN_ROWS", 200))   # min historical rows needed to train a model
        RANDOM_STATE = int(cfg.get("ML_RANDOM_STATE", 42))

        # Prepare a copy for ML preparation
        ml_df = final_df.copy()

        # Ensure necessary numeric columns exist
        for c in [EQUITY_CLOSE_PRICE_COL, 'Daily_Open_Interest_Sum', 'Absolute_OI_Change', DELIVERY_VALUE_COL, NEW_5DAD_COL, REL_DELIVERY_COL]:
            if c not in ml_df.columns:
                ml_df[c] = 0.0

        # Create future targets
        ml_df['future_close'] = ml_df[EQUITY_CLOSE_PRICE_COL].shift(-FUTURE_DAYS)
        ml_df['future_oi'] = ml_df['Daily_Open_Interest_Sum'].shift(-FUTURE_DAYS)

        ml_df['future_return_pct'] = ((ml_df['future_close'] - ml_df[EQUITY_CLOSE_PRICE_COL]) / ml_df[EQUITY_CLOSE_PRICE_COL]).replace([np.inf, -np.inf], np.nan)
        ml_df['future_oi_change'] = (ml_df['future_oi'] - ml_df['Daily_Open_Interest_Sum'])

        # Drop rows without future info (they can't be labeled)
        ml_df_labels = ml_df.dropna(subset=['future_return_pct', 'future_oi_change']).copy()

        # Build OI threshold for label creation using positive future OI changes' quantile
        positive_future_oi = ml_df_labels.loc[ml_df_labels['future_oi_change'] > 0, 'future_oi_change']
        if len(positive_future_oi) > 0:
            oi_thresh = positive_future_oi.quantile(OI_QUANTILE)
        else:
            oi_thresh = ml_df_labels['future_oi_change'].median() if len(ml_df_labels) > 0 else 0.0

        # Create multiclass label:
        # 1 => Long buildup (future_oi_change > oi_thresh AND future_return_pct > RETURN_THRESHOLD)
        # -1 => Short buildup (future_oi_change > oi_thresh AND future_return_pct < -RETURN_THRESHOLD)
        # 0 => otherwise
        def create_label(row):
            if row['future_oi_change'] > oi_thresh:
                if row['future_return_pct'] > RETURN_THRESHOLD:
                    return 1
                if row['future_return_pct'] < -RETURN_THRESHOLD:
                    return -1
            return 0

        if len(ml_df_labels) == 0:
            # No labels available: fallback to rule-based
            print("ML: No rows available for label construction. Falling back to rule-based Longs/Shorts.")
            final_df['Longs'] = 0
            final_df['Shorts'] = 0
            long_conditions = ["NewLongs", "LongCovering", "StrongLong", "LastLegOfLong"]
            short_conditions = ["NewShort", "ShortCovering", "StrongShort", "LastLegOfshort"] 
            final_df.loc[final_df['F&O_Conclusion'].isin(long_conditions), 'Longs'] = final_df['Absolute_OI_Change']
            final_df.loc[final_df['F&O_Conclusion'].isin(short_conditions), 'Shorts'] = final_df['Absolute_OI_Change']
            final_df['Longs'] = final_df['Longs'].fillna(0)
            final_df['Shorts'] = final_df['Shorts'].fillna(0)
            final_df['Longs Till Now'] = final_df['Longs'].cumsum()
            final_df['Shorts Till Now'] = final_df['Shorts'].cumsum()
        else:
            ml_df_labels['ML_Label'] = ml_df_labels.apply(create_label, axis=1)

            # Features for the classifier/regressor
            feature_cols = [
                PRICE_CHANGE_COL, REL_DELIVERY_COL, OI_CHANGE_COL, 'Absolute_OI_Change',
                DELIVERY_VALUE_COL, NEW_5DAD_COL, VWAP_COL
            ]
            # Ensure feature columns exist
            for f in feature_cols:
                if f not in ml_df_labels.columns:
                    ml_df_labels[f] = 0.0

            X = ml_df_labels[feature_cols].fillna(0)
            y = ml_df_labels['ML_Label']

            # If not enough labeled examples to train, fall back to existing simple logic
            if len(ml_df_labels) < MIN_TRAIN_ROWS or y.nunique() == 1:
                print("ML training skipped (not enough data or single-class labels). Using rule-based Longs/Shorts.")
                final_df['Longs'] = 0
                final_df['Shorts'] = 0
                long_conditions = ["NewLongs", "LongCovering", "StrongLong", "LastLegOfLong"]
                short_conditions = ["NewShort", "ShortCovering", "StrongShort", "LastLegOfshort"] 
                final_df.loc[final_df['F&O_Conclusion'].isin(long_conditions), 'Longs'] = final_df['Absolute_OI_Change']
                final_df.loc[final_df['F&O_Conclusion'].isin(short_conditions), 'Shorts'] = final_df['Absolute_OI_Change']
                final_df['Longs'] = final_df['Longs'].fillna(0)
                final_df['Shorts'] = final_df['Shorts'].fillna(0)
                final_df['Longs Till Now'] = final_df['Longs'].cumsum()
                final_df['Shorts Till Now'] = final_df['Shorts'].cumsum()
            else:
                # Standardize features
                scaler = StandardScaler()
                
                # The data going into X is now guaranteed to be numeric due to the fix earlier.
                X_scaled = scaler.fit_transform(X) # <-- This line should now succeed
                
                # FIX for XGBoost: Remap classes [-1, 0, 1] to [0, 1, 2]
                y_mapped = y.copy().replace({-1: 0, 0: 1, 1: 2})
                
                # Split the mapped data
                X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_mapped, test_size=0.2, random_state=RANDOM_STATE, stratify=y_mapped)
                
                # Train classifier
                if XGB_AVAILABLE:
                    # n_estimators=100 is default; keeping it concise
                    clf = XGBClassifier(use_label_encoder=False, eval_metric='mlogloss', random_state=RANDOM_STATE) 
                else:
                    clf = RandomForestClassifier(n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1)

                clf.fit(X_train, y_train)

                # Predict and report (y_test needs to be reversed-mapped for classification_report)
                y_pred = clf.predict(X_test)
                y_pred_unmapped = pd.Series(y_pred).replace({0: -1, 1: 0, 2: 1}).values
                y_test_unmapped = y_test.copy().replace({0: -1, 1: 0, 2: 1}).values
                
                try:
                    # Use the unmapped labels for accurate reporting
                    print("ML classifier report:\n", classification_report(y_test_unmapped, y_pred_unmapped, zero_division=0))
                except Exception:
                    pass

                # Train regressors for magnitude prediction (only on rows where ML_Label != 0)
                reg_features_mask = ml_df_labels['ML_Label'] != 0
                if reg_features_mask.sum() >= 50:
                    X_reg = scaler.transform(ml_df_labels.loc[reg_features_mask, feature_cols].fillna(0))
                    # target is future_oi_change (magnitude)
                    y_reg = ml_df_labels.loc[reg_features_mask, 'future_oi_change'].abs()  # magnitude only

                    if XGB_AVAILABLE:
                        reg = XGBRegressor(random_state=RANDOM_STATE, n_estimators=200)
                    else:
                        reg = RandomForestRegressor(n_estimators=200, random_state=RANDOM_STATE, n_jobs=-1)

                    reg.fit(X_reg, y_reg)
                    # quick MAE
                    y_reg_pred = reg.predict(X_reg)
                    try:
                        print("Regressor MAE on training set:", mean_absolute_error(y_reg, y_reg_pred))
                    except Exception:
                        pass
                else:
                    reg = None
                    print("Not enough samples to train regressors (need >=50).")

                # Save models and scaler for later reuse
                model_base = os.path.join(target_directory, f"{SYMBOL}_ml_models")
                os.makedirs(model_base, exist_ok=True)
                try:
                    joblib.dump(clf, os.path.join(model_base, "ml_classifier.joblib"))
                    joblib.dump(scaler, os.path.join(model_base, "ml_scaler.joblib"))
                    if reg is not None:
                        joblib.dump(reg, os.path.join(model_base, "ml_regressor.joblib"))
                    print(f"Saved ML models to {model_base}")
                except Exception as e:
                    print("Warning: could not save ML models:", e)

                # Apply models to full dataframe (including rows not in ml_df_labels)
                # Need to scale features using saved scaler
                all_X = final_df[feature_cols].fillna(0)
                all_X_scaled = scaler.transform(all_X)

                # Predict and unmap the label back to [-1, 0, 1]
                ml_preds_mapped = clf.predict(all_X_scaled)
                ml_preds = pd.Series(ml_preds_mapped).replace({0: -1, 1: 0, 2: 1}).values
                
                final_df['ML_Label'] = ml_preds

                if reg is not None:
                    pred_mags = reg.predict(all_X_scaled).clip(min=0)
                else:
                    # fallback magnitude = today's Absolute_OI_Change (best-guess)
                    pred_mags = final_df['Absolute_OI_Change'].abs().fillna(0).values

                # Populate Pred_Long_Value / Pred_Short_Value
                final_df['Pred_Long_Value'] = 0.0
                final_df['Pred_Short_Value'] = 0.0

                # Map predictions to predicted magnitudes by index alignment
                # Ensure pred_mags length aligns with final_df index length
                if len(pred_mags) == len(final_df):
                    final_df.loc[final_df['ML_Label'] == 1, 'Pred_Long_Value'] = pred_mags[final_df['ML_Label'] == 1]
                    final_df.loc[final_df['ML_Label'] == -1, 'Pred_Short_Value'] = pred_mags[final_df['ML_Label'] == -1]
                else:
                    # safe mapping via iteration (slower but robust)
                    for idx in final_df.index:
                        try:
                            mag = float(pred_mags[idx])
                        except Exception:
                            mag = 0.0
                        if final_df.at[idx, 'ML_Label'] == 1:
                            final_df.at[idx, 'Pred_Long_Value'] = mag
                        elif final_df.at[idx, 'ML_Label'] == -1:
                            final_df.at[idx, 'Pred_Short_Value'] = mag

                # Final Longs / Shorts numeric fields (use predicted magnitudes)
                final_df['Longs'] = final_df['Pred_Long_Value'].fillna(0)
                final_df['Shorts'] = final_df['Pred_Short_Value'].fillna(0)

                # Cumulative totals (Till Now)
                final_df['Longs Till Now'] = final_df['Longs'].cumsum()
                final_df['Shorts Till Now'] = final_df['Shorts'].cumsum()
    # ------------------ END: MACHINE-LEARNING LONGS/SHORTS (Option D) ------------------

    # ------------------ START: Copy and format DATE column to the end ------------------
    DATE_DISPLAY_COL = 'Date Display (dd-MM-yyyy)'
    final_df[DATE_DISPLAY_COL] = final_df['DATE'].dt.strftime('%d-%m-%Y')
    # ------------------ END: Copy and format DATE column to the end ------------------

    # Column Reordering
    BLANK_COL = ' '
    COLS_TO_MOVE_TO_END = ['Del_Inter', DELIVERY_VALUE_COL, NEW_5DAD_COL, BLANK_COL,
                           PRICE_CHANGE_COL, REL_DELIVERY_COL, OI_CHANGE_COL,
                           'Absolute_OI_Change','Longs','Shorts','Longs Till Now','Shorts Till Now',
                           'Price_Dir','Delivery_Dir','OI_Dir','Scenario_Tuple','F&O_Conclusion','Trade_Signal',
                           DATE_DISPLAY_COL] # Added the new formatted date column here

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

    try:
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
    except ImportError:
        warnings.warn("openpyxl not installed. Skipping Excel styling.", UserWarning)
    except Exception as e:
        print(f"Could not save styled Excel file: {e}")

    return final_df.reset_index(drop=True)

# --------------------------- ENTRY POINT --------------------------------
if __name__ == "__main__":
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1400)
    pd.set_option('display.float_format', '{:.2f}'.format)

    analysis_df = process_analysis_data(TARGET_DIRECTORY, SD_MULTIPLIER, TRADING_QTY)

    if analysis_df is not None and not analysis_df.empty:
        print("Analysis produced rows:", len(analysis_df))
    else:
        print("No analysis output produced; check input files and config.")