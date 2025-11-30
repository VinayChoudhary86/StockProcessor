# PlotChart.py

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots
from config_loader import load_config  # type: ignore

# ---------------- CONFIG / CONSTANTS ---------------- #

cfg = load_config()
TARGET_DIR = cfg["TARGET_DIRECTORY"]
SYMBOL = cfg["SYMBOL"]

TRADES_INPUT_FILE_NAME = f"{SYMBOL}_Trades.csv"
CHART_OUTPUT_FILE_NAME = f"{SYMBOL}_Chart.html"

INPUT_FILE = os.path.join(TARGET_DIR, TRADES_INPUT_FILE_NAME)
OUTPUT_INTERACTIVE_CHART_FILE = os.path.join(TARGET_DIR, CHART_OUTPUT_FILE_NAME)

DATE_COL = "DATE"
CLOSE_COL = "close"
VWAP_COL = "vwap"
QUANTITY_TRADED_COL = "Quantity_Traded"
LONG_COL = "Longs Till Now"
SHORT_COL = "Shorts Till Now"


def run_plotting():
    print("\n--- Plotly Interactive Chart Generator ---\n")
    print("Reading trades from:", INPUT_FILE)

    if not os.path.exists(INPUT_FILE):
        print(f"Error: Trade data input file not found: {INPUT_FILE}")
        return

    try:
        # ---------------- LOAD & CLEAN DATA ---------------- #
        df = pd.read_csv(INPUT_FILE, parse_dates=[DATE_COL])

        df.sort_values(DATE_COL, inplace=True)
        df.reset_index(drop=True, inplace=True)

        for col in [CLOSE_COL, VWAP_COL, QUANTITY_TRADED_COL, LONG_COL, SHORT_COL]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            else:
                raise KeyError(f"Required column '{col}' missing in trades file.")

        df[CLOSE_COL] = df[CLOSE_COL].ffill()
        df[VWAP_COL] = df[VWAP_COL].ffill()

        df[QUANTITY_TRADED_COL] = df[QUANTITY_TRADED_COL].fillna(0)
        df[LONG_COL] = df[LONG_COL].fillna(0)
        df[SHORT_COL] = df[SHORT_COL].fillna(0)

        # ---------------- POSITION & PNL LOGIC ---------------- #
        df["Net_Qty"] = df[QUANTITY_TRADED_COL].cumsum()

        df["Prev_Close"] = df[CLOSE_COL].shift(1).ffill()
        df["Daily_PnL_calc"] = (df[CLOSE_COL] - df["Prev_Close"]) * df["Net_Qty"]
        df["Cumulative_PnL_calc"] = df["Daily_PnL_calc"].cumsum()

        # ---------------- INDICATORS ---------------- #
        df["EMA_9"] = df[CLOSE_COL].ewm(span=9, adjust=False).mean()
        df["EMA_21"] = df[CLOSE_COL].ewm(span=21, adjust=False).mean()
        df["EMA_50"] = df[CLOSE_COL].ewm(span=50, adjust=False).mean()
        df["EMA_100"] = df[CLOSE_COL].ewm(span=100, adjust=False).mean()
        df["EMA_200"] = df[CLOSE_COL].ewm(span=200, adjust=False).mean()
        df["EMA_5_Longs"] = df[LONG_COL].ewm(span=5, adjust=False).mean()
        df["EMA_5_Shorts"] = df[SHORT_COL].ewm(span=5, adjust=False).mean()

        # Build synthetic OHLC
        df["Open"] = df[CLOSE_COL].shift(1).fillna(df[CLOSE_COL].iloc[0])
        range_pct = 0.005
        df["High"] = df[[CLOSE_COL, "Open"]].max(axis=1) * (1 + range_pct)
        df["Low"] = df[[CLOSE_COL, "Open"]].min(axis=1) * (1 - range_pct)

        # ---------------- VWAP vs CLOSE GAP % + COLOR ---------------- #
        df["VWAP_Close_Gap_Pct"] = ((df[VWAP_COL] - df[CLOSE_COL]) * 100 / df[CLOSE_COL]).round(2)

        def gap_color(gap):
            if gap > 1:
                return "red"          # VWAP > Price → Bearish pressure
            elif gap < -1:
                return "lime"         # VWAP < Price → Bullish pressure
            else:
                return "yellow"       # Neutral zone

        df["Gap_Color"] = df["VWAP_Close_Gap_Pct"].apply(gap_color)

        # ---------------- HOVER TEXT ---------------- #
        hover_text = []
        for _, row in df.iterrows():
            cum_pnl_val = row["Cumulative_PnL_calc"]
            pnl_color = "lime" if cum_pnl_val >= 0 else "red"

            gap_pct = row["VWAP_Close_Gap_Pct"]
            gap_col = row["Gap_Color"]

            hover_text.append(
                f"<span style='color:{pnl_color}'>Cumulative P&L: {cum_pnl_val:,.2f}</span><br>"
                f"<b>VWAP–Close Gap: <span style='color:{gap_col}'>{gap_pct:.2f}%</span></b><br>"
                f"Open: {row['Open']:.2f}<br>"
                f"High: {row['High']:.2f}<br>"
                f"Low: {row['Low']:.2f}<br>"
                f"Close: {row[CLOSE_COL]:.2f}<br>"
                f"VWAP: {row[VWAP_COL]:.2f}<br>"
                f"Net Qty: {row['Net_Qty']:.0f}<br>"
            )

        # ---------------- TRACES ---------------- #
        candlestick = go.Candlestick(
            x=df[DATE_COL],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df[CLOSE_COL],
            name="Price",
            hovertext=hover_text,
            hoverinfo="text",
        )

        ema9_line = go.Scatter(x=df[DATE_COL], y=df["EMA_9"], mode="lines", name="EMA 9", line=dict(width=1.2, color="yellow"))
        ema21_line = go.Scatter(x=df[DATE_COL], y=df["EMA_21"], mode="lines", name="EMA 21", line=dict(width=1.2, color="cyan"))
        ema50_line = go.Scatter(x=df[DATE_COL], y=df["EMA_50"], mode="lines", name="EMA 50", line=dict(width=1.2, color="magenta"))
        ema100_line = go.Scatter(x=df[DATE_COL], y=df["EMA_100"], mode="lines", name="EMA 100", line=dict(width=1.5, color="white"))
        ema200_line = go.Scatter(x=df[DATE_COL], y=df["EMA_200"], mode="lines", name="EMA 200", line=dict(width=1.5, color="lightgray"))
        vwap_line = go.Scatter(x=df[DATE_COL], y=df[VWAP_COL], mode="lines", name="VWAP", line=dict(width=1.5, color="orange"))

        # ------------- BUY / SELL ARROWS ---------------- #
        buy_trades = df[df[QUANTITY_TRADED_COL] > 0]
        sell_trades = df[df[QUANTITY_TRADED_COL] < 0]

        buy_marker = go.Scatter(
            x=buy_trades[DATE_COL],
            y=buy_trades[CLOSE_COL],
            mode="markers",
            marker=dict(size=16, color="lime", symbol="arrow-up"),
            name="BUY",
            hoverinfo="text",
            hovertext=buy_trades.apply(
                lambda r: f"BUY @ {r[CLOSE_COL]:.2f}<br>Net Qty: {r['Net_Qty']:.0f}",
                axis=1,
            ),
        )

        sell_marker = go.Scatter(
            x=sell_trades[DATE_COL],
            y=sell_trades[CLOSE_COL],
            mode="markers",
            marker=dict(size=16, color="red", symbol="arrow-down"),
            name="SELL",
            hoverinfo="text",
            hovertext=sell_trades.apply(
                lambda r: f"SELL @ {r[CLOSE_COL]:.2f}<br>Net Qty: {r['Net_Qty']:.0f}",
                axis=1,
            ),
        )

        # ---------------- Longs / Shorts Panel ---------------- #
        longs_line = go.Scatter(x=df[DATE_COL], y=df[LONG_COL], mode="lines", name="Longs Till Now", line=dict(width=2, color="lime"))
        ema5_longs_line = go.Scatter(x=df[DATE_COL], y=df["EMA_5_Longs"], mode="lines", name="EMA 5 (Longs)", line=dict(width=1, color="green", dash="dot"))
        shorts_line = go.Scatter(x=df[DATE_COL], y=df[SHORT_COL], mode="lines", name="Shorts Till Now", line=dict(width=2, color="red"))
        ema5_shorts_line = go.Scatter(x=df[DATE_COL], y=df["EMA_5_Shorts"], mode="lines", name="EMA 5 (Shorts)", line=dict(width=1, color="darkred", dash="dot"))

        # ---------------- FIGURE ---------------- #
        fig = make_subplots(
            rows=2, cols=1,
            row_heights=[0.8, 0.2],
            shared_xaxes=True,
            vertical_spacing=0.02,
            subplot_titles=(
                f"Interactive Chart: {os.path.basename(INPUT_FILE)}",
                "Open Interest (Longs / Shorts Till Now)",
            ),
        )

        # PRICE PANEL
        fig.add_trace(candlestick, row=1, col=1)
        fig.add_trace(ema9_line, row=1, col=1)
        fig.add_trace(ema21_line, row=1, col=1)
        fig.add_trace(ema50_line, row=1, col=1)
        fig.add_trace(ema100_line, row=1, col=1)
        fig.add_trace(ema200_line, row=1, col=1)
        fig.add_trace(vwap_line, row=1, col=1)
        fig.add_trace(buy_marker, row=1, col=1)
        fig.add_trace(sell_marker, row=1, col=1)

        # OI PANEL
        fig.add_trace(longs_line, row=2, col=1)
        fig.add_trace(ema5_longs_line, row=2, col=1)
        fig.add_trace(shorts_line, row=2, col=1)
        fig.add_trace(ema5_shorts_line, row=2, col=1)

        # ---------------- PAIR NUMBERING + ARROW CONNECTOR ---------------- #
        df["Prev_Net_Qty"] = df["Net_Qty"].shift(1).fillna(0)

        pair_id = 1
        active_pair = None
        active_type = None
        entry_price = None
        entry_time = None

        for idx, row in df.iterrows():
            qty_traded = row[QUANTITY_TRADED_COL]
            prev_qty = row["Prev_Net_Qty"]
            curr_qty = row["Net_Qty"]

            if qty_traded == 0:
                continue

            price = row[CLOSE_COL]
            time = row[DATE_COL]

            # -------- ENTRY -------- #
            if prev_qty == 0:
                active_type = "LONG" if qty_traded > 0 else "SHORT"
                active_pair = pair_id
                entry_price = price
                entry_time = time

                fig.add_annotation(
                    x=1.0, y=price,
                    text=f"{active_type} ({active_pair})",
                    showarrow=False,
                    font=dict(size=10, color="lime" if active_type=="LONG" else "red"),
                    xanchor="left",
                    yanchor="middle",
                    xref="paper", yref="y1",
                )
                continue

            # -------- EXIT -------- #
            if curr_qty == 0 and active_pair is not None:
                cover_type = "LONG COVER" if active_type == "LONG" else "SHORT COVER"

                fig.add_annotation(
                    x=1.0, y=price,
                    text=f"{cover_type} ({active_pair})",
                    showarrow=False,
                    font=dict(size=10, color="lime" if active_type=="LONG" else "red"),
                    xanchor="left",
                    yanchor="middle",
                    xref="paper", yref="y1",
                )

                # connector line
                fig.add_shape(
                    type="line",
                    x0=entry_time, y0=entry_price,
                    x1=time, y1=price,
                    xref="x1", yref="y1",
                    line=dict(
                        width=2,
                        dash="dot",
                        color="lime" if active_type=="LONG" else "red",
                    )
                )

                # arrow
                fig.add_annotation(
                    x=time,
                    y=price,
                    ax=entry_time,
                    ay=entry_price,
                    xref="x1",
                    yref="y1",
                    axref="x1",
                    ayref="y1",
                    showarrow=True,
                    arrowhead=3,
                    arrowsize=2,
                    arrowcolor="lime" if active_type=="LONG" else "red"
                )

                pair_id += 1
                active_pair = None
                active_type = None
                entry_price = None
                entry_time = None

        # ---------------- LAYOUT ---------------- #
        fig.update_layout(
            template="plotly_dark",
            height=980,
            hovermode="x unified",
            dragmode="pan",
        )

        fig.update_yaxes(title="Price", row=1, col=1)
        fig.update_yaxes(title="Quantity", row=2, col=1)

        fig.update_xaxes(title="Date", row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)

        fig.update_traces(showlegend=False, selector=dict(type="candlestick"))

        final_pnl = df["Cumulative_PnL_calc"].iloc[-1]
        pnl_color = "lime" if final_pnl >= 0 else "red"

        fig.add_annotation(
            x=0.01, y=1.02,
            text=f"Cumulative P&L: {final_pnl:,.2f}",
            showarrow=False,
            font=dict(size=18, color=pnl_color),
            xref="paper",
            yref="paper",
        )

        # ---------------- SAVE HTML ---------------- #
        plot(
            fig,
            filename=OUTPUT_INTERACTIVE_CHART_FILE,
            auto_open=True,
            config={
                "displayModeBar": True,
                "scrollZoom": True,
                "modeBarButtonsToAdd": [
                    "drawline", "drawopenpath", "drawclosedpath",
                    "drawcircle", "drawrect", "eraseshape",
                ],
            },
        )

        print("\nChart generated successfully:")
        print(OUTPUT_INTERACTIVE_CHART_FILE)

    except Exception as e:
        print("An error occurred during chart generation:", e)


if __name__ == "__main__":
    run_plotting()
