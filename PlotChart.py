# Plot_1.py

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots 
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

# Define the names for the existing OI columns
LONG_COL = 'Longs Till Now'
SHORT_COL = 'Shorts Till Now'


def run_plotting():
    print(f"--- Plotly Interactive Chart Generator ---\n")

    if not os.path.exists(INPUT_FILE):
        print(f"Error: Trade data input file not found: {INPUT_FILE}")
        return

    try:
        # Load trades CSV
        # Assuming Longs Till Now and Shorts Till Now are already present in the CSV
        df = pd.read_csv(INPUT_FILE, parse_dates=[DATE_COL], thousands=',')
        df.sort_values(DATE_COL, inplace=True)

        df[CLOSE_COL] = pd.to_numeric(df[CLOSE_COL], errors='coerce').fillna(method='ffill')
        df[QUANTITY_TRADED_COL] = pd.to_numeric(df[QUANTITY_TRADED_COL], errors='coerce').fillna(0)
        
        # Ensure Longs and Shorts columns are numeric (critical check)
        if LONG_COL in df.columns and SHORT_COL in df.columns:
            df[LONG_COL] = pd.to_numeric(df[LONG_COL], errors='coerce').fillna(0)
            df[SHORT_COL] = pd.to_numeric(df[SHORT_COL], errors='coerce').fillna(0)
        else:
            raise KeyError(f"Error: Required column '{LONG_COL}' or '{SHORT_COL}' missing in the input file.")

        # VWAP
        if VWAP_COL in df.columns:
            df[VWAP_COL] = pd.to_numeric(df[VWAP_COL], errors='coerce').fillna(method='ffill')
        else:
            raise KeyError("ERROR: 'vwap' column missing in *_Trades.csv.")

        # Compute net quantity and P&L
        df['Net_Qty'] = df[QUANTITY_TRADED_COL].cumsum()
        df['Prev_Close'] = df[CLOSE_COL].shift(1).fillna(df[CLOSE_COL].iloc[0])
        df['PnL'] = (df[CLOSE_COL] - df['Prev_Close']) * df['Net_Qty']
        df['Cumulative_PnL'] = df['PnL'].cumsum()
        
        # Calculate 5 EMA directly on the existing Longs/Shorts columns
        df["EMA_5_Longs"] = df[LONG_COL].ewm(span=5, adjust=False).mean()
        df["EMA_5_Shorts"] = df[SHORT_COL].ewm(span=5, adjust=False).mean()
        

        # Compute EMAs for price chart
        df["EMA_9"] = df[CLOSE_COL].ewm(span=9, adjust=False).mean()
        df["EMA_21"] = df[CLOSE_COL].ewm(span=21, adjust=False).mean()
        df["EMA_50"] = df[CLOSE_COL].ewm(span=50, adjust=False).mean()
        df["EMA_100"] = df[CLOSE_COL].ewm(span=100, adjust=False).mean()
        df["EMA_200"] = df[CLOSE_COL].ewm(span=200, adjust=False).mean()

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

        # --- TRACE DEFINITIONS ---
        
        # 1. Candlestick (Row 1)
        candlestick = go.Candlestick(
            x=df[DATE_COL],
            open=df['Open'], high=df['High'], low=df['Low'], close=df[CLOSE_COL],
            name='Price', hovertext=hover_text, hoverinfo='text',
        )

        # 2. Price EMAs (Row 1)
        ema9_line = go.Scatter(x=df[DATE_COL], y=df["EMA_9"], mode='lines', name='EMA 9', line=dict(width=1.2, color='yellow'))
        ema21_line = go.Scatter(x=df[DATE_COL], y=df["EMA_21"], mode='lines', name='EMA 21', line=dict(width=1.2, color='cyan'))
        ema50_line = go.Scatter(x=df[DATE_COL], y=df["EMA_50"], mode='lines', name='EMA 50', line=dict(width=1.2, color='magenta'))
        ema100_line = go.Scatter(x=df[DATE_COL], y=df["EMA_100"], mode='lines', name='EMA 100', line=dict(width=1.5, color='white'))
        ema200_line = go.Scatter(x=df[DATE_COL], y=df["EMA_200"], mode='lines', name='EMA 200', line=dict(width=1.5, color='lightgray'))
        vwap_line = go.Scatter(x=df[DATE_COL], y=df[VWAP_COL], mode='lines', name='VWAP', line=dict(width=1.5, color='orange'))

        # 3. BUY / SELL markers (Row 1)
        buy_trades = df[df[QUANTITY_TRADED_COL] > 0]
        sell_trades = df[df[QUANTITY_TRADED_COL] < 0]

        buy_marker = go.Scatter(x=buy_trades[DATE_COL], y=buy_trades[CLOSE_COL], mode='markers',
            marker=dict(size=12, color='white', symbol='triangle-up'), name='BUY', hoverinfo='text',
            hovertext=buy_trades.apply(lambda row: f"BUY @ {row[CLOSE_COL]:.2f}<br>Net Qty: {row['Net_Qty']}", axis=1)
        )
        sell_marker = go.Scatter(x=sell_trades[DATE_COL], y=sell_trades[CLOSE_COL], mode='markers',
            marker=dict(size=12, color='orange', symbol='triangle-down'), name='SELL', hoverinfo='text',
            hovertext=sell_trades.apply(lambda row: f"SELL @ {row[CLOSE_COL]:.2f}<br>Net Qty: {row['Net_Qty']}", axis=1)
        )
        
        # 4. Longs/Shorts Quantity (Row 2) - Uses the existing columns
        longs_line = go.Scatter(
            x=df[DATE_COL], y=df[LONG_COL], mode='lines', 
            name='Longs till now', line=dict(width=2, color='lime')
        )
        ema5_longs_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_5_Longs"], mode='lines',
            name='EMA 5 (Longs)', line=dict(width=1, color='green', dash='dot')
        )
        shorts_line = go.Scatter(
            x=df[DATE_COL], y=df[SHORT_COL], mode='lines', 
            name='Shorts till now', line=dict(width=2, color='red')
        )
        ema5_shorts_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_5_Shorts"], mode='lines',
            name='EMA 5 (Shorts)', line=dict(width=1, color='darkred', dash='dot')
        )


        # --- FIGURE CREATION (Subplots) ---

        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.8, 0.2], 
            shared_xaxes=True,
            vertical_spacing=0.02,
            subplot_titles=(f'Interactive Chart: {os.path.basename(INPUT_FILE)}', 'Open Interest Components')
        )

        # Row 1: Price Chart Traces
        fig.add_trace(candlestick, row=1, col=1)
        fig.add_trace(ema9_line, row=1, col=1)
        fig.add_trace(ema21_line, row=1, col=1)
        fig.add_trace(ema50_line, row=1, col=1)
        fig.add_trace(ema100_line, row=1, col=1)
        fig.add_trace(ema200_line, row=1, col=1)
        fig.add_trace(vwap_line, row=1, col=1)
        fig.add_trace(buy_marker, row=1, col=1)
        fig.add_trace(sell_marker, row=1, col=1)

        # Row 2: Cumulative Quantity Traces
        fig.add_trace(longs_line, row=2, col=1)
        fig.add_trace(ema5_longs_line, row=2, col=1)
        fig.add_trace(shorts_line, row=2, col=1)
        fig.add_trace(ema5_shorts_line, row=2, col=1)


        # --- LAYOUT AND AXIS UPDATES ---

        fig.update_layout(
            template='plotly_dark',
            height=950,
            hovermode='x unified',
            dragmode='pan',
            # Move legend to top right for better visibility
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # Update Axes
        # Main Price Chart (Row 1)
        fig.update_yaxes(title='Price (INR)', showspikes=True, fixedrange=False, row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, showspikes=True, row=1, col=1, visible=False) # Hide X-axis on top chart

        # Cumulative Quantity Chart (Row 2)
        fig.update_yaxes(title='Quantity', showspikes=True, fixedrange=False, row=2, col=1)
        fig.update_xaxes(title='Date', showspikes=True, row=2, col=1)
        
        # Hide the candlestick trace from the legend
        fig.update_traces(showlegend=False, selector=dict(type='candlestick'))


        # Cumulative P&L annotation (MOVED to top left header using paper coordinates)
        final_pnl = df['Cumulative_PnL'].iloc[-1]
        pnl_color = 'lime' if final_pnl >= 0 else 'red'

        fig.add_annotation(
            # X coordinate: 0.01 for left-most position on the paper
            x=0.01, 
            # Y coordinate: 1.02 to place it just above the plot area/subplot title
            y=1.02,
            text=f"Cumulative P&L: {final_pnl:,.2f}",
            showarrow=False,
            font=dict(size=18, color=pnl_color),
            xanchor='left', 
            yanchor='bottom',
            # Use paper coordinates to place it in the figure header area
            xref='paper', 
            yref='paper'
        )

        # Save chart with drawing tools + panning
        plot(
            fig,
            filename=OUTPUT_INTERACTIVE_CHART_FILE,
            auto_open=True,
            config={
                'displayModeBar': True,
                'scrollZoom': True, 

                # ⭐ ENABLE DRAWING TOOLS ⭐
                'modeBarButtonsToAdd': [
                    'drawline', 'drawopenpath', 'drawclosedpath',
                    'drawcircle', 'drawrect', 'eraseshape'
                ]
            }
        )

        print(f"\nChart generated successfully:\n{OUTPUT_INTERACTIVE_CHART_FILE}")

    except Exception as e:
        print(f"An error occurred during chart generation: {e}")


if __name__ == "__main__":
    run_plotting()