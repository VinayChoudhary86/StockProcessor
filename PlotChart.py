# Plot_1.py

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot
from config_loader import load_config  # type: ignore

# Load configuration
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
VWAP_COL = 'vwap'


def run_plotting():
    print(f"--- Plotly Interactive Chart Generator ---\n")

    if not os.path.exists(INPUT_FILE):
        print(f"Error: Trade data input file not found: {INPUT_FILE}")
        return

    try:
        # Load trades CSV
        df = pd.read_csv(INPUT_FILE, parse_dates=[DATE_COL], thousands=',')
        df.sort_values(DATE_COL, inplace=True)

        df[CLOSE_COL] = pd.to_numeric(df[CLOSE_COL], errors='coerce').fillna(method='ffill')
        df[QUANTITY_TRADED_COL] = pd.to_numeric(df[QUANTITY_TRADED_COL], errors='coerce').fillna(0)

        # VWAP
        if VWAP_COL in df.columns:
            df[VWAP_COL] = pd.to_numeric(df[VWAP_COL], errors='coerce').fillna(method='ffill')
        else:
            raise KeyError("ERROR: 'vwap' column missing in *_Trades.csv. Please update Trader_11 first.")

        # Compute net quantity
        df['Net_Qty'] = df[QUANTITY_TRADED_COL].cumsum()

        # Compute Cumulative P&L (mark-to-market)
        df['Prev_Close'] = df[CLOSE_COL].shift(1).fillna(df[CLOSE_COL].iloc[0])
        df['PnL'] = (df[CLOSE_COL] - df['Prev_Close']) * df['Net_Qty']
        df['Cumulative_PnL'] = df['PnL'].cumsum()

        # Compute EMAs
        df["EMA_9"] = df[CLOSE_COL].ewm(span=9, adjust=False).mean()
        df["EMA_21"] = df[CLOSE_COL].ewm(span=21, adjust=False).mean()
        df["EMA_50"] = df[CLOSE_COL].ewm(span=50, adjust=False).mean()

        # Approximate OHLC
        df['Open'] = df[CLOSE_COL].shift(1).fillna(df[CLOSE_COL].iloc[0])
        range_pct = 0.005
        df['High'] = df[['Open', CLOSE_COL]].max(axis=1) * (1 + range_pct)
        df['Low'] = df[['Open', CLOSE_COL]].min(axis=1) * (1 - range_pct)

        # Hover text
        hover_text = [
            f"Date: {row[DATE_COL].strftime('%Y-%m-%d')}<br>"
            f"<span style='color:{'lime' if row['Cumulative_PnL'] >= 0 else 'red'}'>"
            f"Cumulative P&L: {row['Cumulative_PnL']:,.2f}</span><br>"
            f"Open: {row['Open']:.2f}<br>"
            f"High: {row['High']:.2f}<br>"
            f"Low: {row['Low']:.2f}<br>"
            f"Close: {row[CLOSE_COL]:.2f}<br>"
            f"Net Qty: {row['Net_Qty']}<br>"
            for _, row in df.iterrows()
        ]

        # Candlestick
        candlestick = go.Candlestick(
            x=df[DATE_COL],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df[CLOSE_COL],
            name='Price',
            hovertext=hover_text,
            hoverinfo='text'
        )

        # EMA lines
        ema9_line = go.Scatter(x=df[DATE_COL], y=df["EMA_9"], mode='lines',
                               name='EMA 9', line=dict(width=1.2, color='yellow'))

        ema21_line = go.Scatter(x=df[DATE_COL], y=df["EMA_21"], mode='lines',
                                name='EMA 21', line=dict(width=1.2, color='cyan'))

        ema50_line = go.Scatter(x=df[DATE_COL], y=df["EMA_50"], mode='lines',
                                name='EMA 50', line=dict(width=1.2, color='magenta'))

        # VWAP
        vwap_line = go.Scatter(x=df[DATE_COL], y=df[VWAP_COL], mode='lines',
                               name='VWAP', line=dict(width=1.5, color='orange'))

        # BUY / SELL markers
        buy_trades = df[df[QUANTITY_TRADED_COL] > 0]
        sell_trades = df[df[QUANTITY_TRADED_COL] < 0]

        buy_marker = go.Scatter(
            x=buy_trades[DATE_COL], y=buy_trades[CLOSE_COL],
            mode='markers',
            marker=dict(size=12, color='white', symbol='triangle-up'),
            name='BUY',
            hoverinfo='text',
            hovertext=buy_trades.apply(
                lambda row: f"BUY @ {row[CLOSE_COL]:.2f}<br>Net Qty: {row['Net_Qty']}", axis=1)
        )

        sell_marker = go.Scatter(
            x=sell_trades[DATE_COL], y=sell_trades[CLOSE_COL],
            mode='markers',
            marker=dict(size=12, color='orange', symbol='triangle-down'),
            name='SELL',
            hoverinfo='text',
            hovertext=sell_trades.apply(
                lambda row: f"SELL @ {row[CLOSE_COL]:.2f}<br>Net Qty: {row['Net_Qty']}", axis=1)
        )

        # Layout with panning enabled
        layout = go.Layout(
            title=f'Interactive Chart: {os.path.basename(INPUT_FILE)}',
            xaxis=dict(title='Date', rangeslider_visible=False, showspikes=True),
            # fixedrange=False ensures the y-axis is not locked (from previous request)
            yaxis=dict(title='Price (INR)', showspikes=True, fixedrange=False), 
            template='plotly_dark',
            height=950,
            hovermode='x unified',

            # ⭐ ENABLE CLICK-AND-DRAG PANNING ⭐
            dragmode='pan'
        )

        # Figure
        fig = go.Figure(
            data=[
                candlestick, ema9_line, ema21_line, ema50_line,
                vwap_line, buy_marker, sell_marker
            ],
            layout=layout
        )

        # Cumulative P&L annotation
        final_pnl = df['Cumulative_PnL'].iloc[-1]
        pnl_color = 'lime' if final_pnl >= 0 else 'red'

        fig.add_annotation(
            x=df[DATE_COL].iloc[-1],
            y=df[CLOSE_COL].max() * 1.05,
            text=f"Cumulative P&L: {final_pnl:,.2f}",
            showarrow=False,
            font=dict(size=18, color=pnl_color),
            xanchor='right',
            yanchor='bottom'
        )

        # Save chart with drawing tools + panning
        plot(
            fig,
            filename=OUTPUT_INTERACTIVE_CHART_FILE,
            auto_open=True,
            config={
                'displayModeBar': True,
                # CORRECTION: Set scrollZoom to True to enable scroll zoom on BOTH X and Y axes
                'scrollZoom': True, 

                # ⭐ ENABLE DRAWING TOOLS ⭐
                'modeBarButtonsToAdd': [
                    'drawline',
                    'drawopenpath',
                    'drawclosedpath',
                    'drawcircle',
                    'drawrect',
                    'eraseshape'
                ]
            }
        )

        print(f"\nChart generated successfully:\n{OUTPUT_INTERACTIVE_CHART_FILE}")

    except Exception as e:
        print(f"An error occurred during chart generation: {e}")


if __name__ == "__main__":
    run_plotting()