import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from config_loader import load_config  # type: ignore

# --------------------------------------------
# CONFIG
# --------------------------------------------
cfg = load_config()

TARGET_DIR = cfg["TARGET_DIRECTORY"]
SYMBOL = cfg["SYMBOL"]
ANALYSIS_FILE_NAME = f"{SYMBOL}_Analysis.csv"
TRADES_FILE_NAME   = f"{SYMBOL}_Trades_ML_WF.csv"


ANALYSIS_FILE = os.path.join(TARGET_DIR, ANALYSIS_FILE_NAME) 
TRADES_FILE   = os.path.join(TARGET_DIR, TRADES_FILE_NAME)

# --------------------------------------------
# LOAD DATA
# --------------------------------------------
if not os.path.exists(ANALYSIS_FILE):
    raise FileNotFoundError(f"Analysis file not found: {ANALYSIS_FILE}")

if not os.path.exists(TRADES_FILE):
    raise FileNotFoundError(f"Trades file not found: {TRADES_FILE}")

df_prices = pd.read_csv(ANALYSIS_FILE)
df_trades = pd.read_csv(TRADES_FILE)

# Normalize column names
df_prices.columns = df_prices.columns.str.lower()
df_trades.columns = df_trades.columns.str.lower()

# Merge on date
df_prices['date'] = pd.to_datetime(df_prices['date'])
df_trades['date'] = pd.to_datetime(df_trades['date'])

df = pd.merge(df_prices, df_trades[['date', 'cumulative_pnl']], on="date", how="left")

# --------------------------------------------
# CREATE SUBPLOTS
# --------------------------------------------
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.05,
    row_heights=[0.7, 0.3],
    subplot_titles=("Price (Candlestick)", "Cumulative PnL")
)

# --------------------------------------------
# CANDLESTICK CHART
# --------------------------------------------
fig.add_trace(
    go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="Candlestick"
    ),
    row=1, col=1
)

# --------------------------------------------
# CUMULATIVE PNL LINE
# --------------------------------------------
fig.add_trace(
    go.Scatter(
        x=df['date'],
        y=df['cumulative_pnl'],
        mode="lines",
        line=dict(width=2),
        name="Cumulative PnL"
    ),
    row=2, col=1
)

# --------------------------------------------
# LAYOUT SETTINGS
# --------------------------------------------
fig.update_layout(
    title="Candlestick + Cumulative PnL",
    xaxis1=dict(rangeslider=dict(visible=False)),
    height=900,
    template="plotly_white"
)

fig.update_yaxes(title_text="Price", row=1, col=1)
fig.update_yaxes(title_text="PnL", row=2, col=1)

# --------------------------------------------
# SHOW PLOT
# --------------------------------------------
fig.show()
