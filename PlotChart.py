# Plot_1.py

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot
from config_loader import load_config  # type: ignore

# Load ONCE
cfg = load_config()
TARGET_DIR = cfg["TARGET_DIRECTORY"]
SYMBOL = cfg["SYMBOL"]

TRADES_INPUT_FILE_NAME = f"{SYMBOL}_Trades.csv"
CHART_OUTPUT_FILE_NAME = f"{SYMBOL}_Chart.html"

INPUT_FILE = os.path.join(TARGET_DIR, TRADES_INPUT_FILE_NAME)
OUTPUT_INTERACTIVE_CHART_FILE = os.path.join(TARGET_DIR, CHART_OUTPUT_FILE_NAME)

DATE_COL = 'DATE'
CLOSE_COL = 'close'
QUANTITY_TRADED_COL = 'Quantity_Traded'
VWAP_COL = 'vwap'     # <-- NEW
SIGNAL_COL = 'Signal'


def run_plotting():
    print(f"--- Plotly Interactive Chart Generator ---\n")

    if not os.path.exists(INPUT_FILE):
        print(f"Error: Trade data input file not found: {INPUT_FILE}")
        return

    try:
        df = pd.read_csv(INPUT_FILE, parse_dates=[DATE_COL], thousands=',')
        df.sort_values(DATE_COL, inplace=True)

        df[CLOSE_COL] = pd.to_numeric(df[CLOSE_COL], errors='coerce').fillna(method='ffill')
        df[QUANTITY_TRADED_COL] = pd.to_numeric(df[QUANTITY_TRADED_COL], errors='coerce').fillna(0)

        # === VWAP from Trades File ===
        if VWAP_COL in df.columns:
            df[VWAP_COL] = pd.to_numeric(df[VWAP_COL], errors='coerce').fillna(method='ffill')
        else:
            raise KeyError("ERROR: 'vwap' column missing in *_Trades.csv. Please update Trader_11 first.")

        # === Compute EMAs from Close Price ===
        df["EMA_9"] = df[CLOSE_COL].ewm(span=9, adjust=False).mean()
        df["EMA_21"] = df[CLOSE_COL].ewm(span=21, adjust=False).mean()
        df["EMA_50"] = df[CLOSE_COL].ewm(span=50, adjust=False).mean()

        # === Approximate OHLC ===
        df['Open'] = df[CLOSE_COL].shift(1).fillna(df[CLOSE_COL].iloc[0])
        range_pct = 0.005
        df['High'] = df[[CLOSE_COL, 'Open']].max(axis=1) * (1 + range_pct)
        df['Low'] = df[[CLOSE_COL, 'Open']].min(axis=1) * (1 - range_pct)

        # Candlestick
        candlestick = go.Candlestick(
            x=df[DATE_COL],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df[CLOSE_COL],
            name='Price'
        )

        # === EMA Lines ===
        ema9_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_9"],
            mode='lines', name='EMA 9', line=dict(width=1.2, color='yellow')
        )
        ema21_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_21"],
            mode='lines', name='EMA 21', line=dict(width=1.2, color='cyan')
        )
        ema50_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_50"],
            mode='lines', name='EMA 50', line=dict(width=1.2, color='magenta')
        )

        # === VWAP LINE (from trades CSV) ===
        vwap_line = go.Scatter(
            x=df[DATE_COL], y=df[VWAP_COL],
            mode='lines', name='VWAP', line=dict(width=1.5, color='orange')
        )

        # BUY / SELL markers
        buy_trades = df[df[QUANTITY_TRADED_COL] > 0].copy()
        sell_trades = df[df[QUANTITY_TRADED_COL] < 0].copy()

        buy_marker = go.Scatter(
            x=buy_trades[DATE_COL],
            y=buy_trades[CLOSE_COL],
            mode='markers',
            marker=dict(size=12, color='white', symbol='triangle-up'),
            name='BUY',
            hoverinfo='text',
            hovertext=buy_trades.apply(
                lambda row: f"BUY @ {row[CLOSE_COL]:.2f}<br>Qty: {row[QUANTITY_TRADED_COL]}",
                axis=1
            )
        )

        sell_marker = go.Scatter(
            x=sell_trades[DATE_COL],
            y=sell_trades[CLOSE_COL],
            mode='markers',
            marker=dict(size=12, color='orange', symbol='triangle-down'),
            name='SELL',
            hoverinfo='text',
            hovertext=sell_trades.apply(
                lambda row: f"SELL @ {row[CLOSE_COL]:.2f}<br>Qty: {row[QUANTITY_TRADED_COL]}",
                axis=1
            )
        )

        layout = go.Layout(
            title=f'Interactive Chart: {os.path.basename(INPUT_FILE)}',
            xaxis=dict(title='Date', rangeslider_visible=False, showspikes=True),
            yaxis=dict(title='Price (INR)', showspikes=True),
            template='plotly_dark',
            height=950,
            hovermode='x unified'
        )

        fig = go.Figure(
            data=[
                candlestick,
                ema9_line,
                ema21_line,
                ema50_line,
                vwap_line,
                buy_marker,
                sell_marker
            ],
            layout=layout
        )

        plot(fig,
             filename=OUTPUT_INTERACTIVE_CHART_FILE,
             auto_open=False,
             config={'displayModeBar': True}
        )

        print(f"\nChart generated successfully:\n{OUTPUT_INTERACTIVE_CHART_FILE}")

    except Exception as e:
        print(f"An error occurred during chart generation: {e}")


if __name__ == "__main__":
    run_plotting()
