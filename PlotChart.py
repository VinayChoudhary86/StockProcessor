import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.offline import plot
from plotly.subplots import make_subplots
from openpyxl import load_workbook
from config_loader import load_config  # type: ignore
from utils_progress import print_progress_bar # type: ignore

# ---------------- CONFIG / CONSTANTS ---------------- #

cfg = load_config()
TARGET_DIR = cfg["TARGET_DIRECTORY"]
SYMBOL = cfg["SYMBOL"]

TRADES_INPUT_FILE_NAME = f"{SYMBOL}_Trades_ML.csv"
CHART_OUTPUT_FILE_NAME = f"{SYMBOL}_Chart.html"

INPUT_FILE = os.path.join(TARGET_DIR, TRADES_INPUT_FILE_NAME)
OUTPUT_INTERACTIVE_CHART_FILE = os.path.join(TARGET_DIR, CHART_OUTPUT_FILE_NAME)

DATE_COL = "DATE"
OPEN_COL = "OPEN"
CLOSE_COL = "close"
VWAP_COL = "vwap"
QUANTITY_TRADED_COL = "Quantity_Traded"
LONG_COL = "Longs Till Now"
SHORT_COL = "Shorts Till Now"


def sign(q: float) -> int:
    """Return sign of quantity: +1, -1, or 0."""
    if q > 0:
        return 1
    elif q < 0:
        return -1
    return 0


def run_plotting():
    print("\n--- Plotly Interactive Chart Generator (ML Trades) ---\n")
    print("Reading trades from:", INPUT_FILE)

    if not os.path.exists(INPUT_FILE):
        print(f"Error: Trade data input file not found: {INPUT_FILE}")
        return

    try:
        # ---------------- LOAD & CLEAN DATA ---------------- #
        df = pd.read_csv(INPUT_FILE, parse_dates=[DATE_COL])

        df.sort_values(DATE_COL, inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Required columns
        required_cols = [
            DATE_COL, OPEN_COL, CLOSE_COL, VWAP_COL,
            QUANTITY_TRADED_COL, LONG_COL, SHORT_COL,
            "Position", "Daily_PnL", "Cumulative_PnL"
        ]
        for col in required_cols:
            if col not in df.columns:
                raise KeyError(f"Required column '{col}' missing in trades file.")

        # Numeric cleanup
        df[OPEN_COL] = pd.to_numeric(df[OPEN_COL], errors="coerce")
        df[CLOSE_COL] = pd.to_numeric(df[CLOSE_COL], errors="coerce")
        df[VWAP_COL] = pd.to_numeric(df[VWAP_COL], errors="coerce")
        df[QUANTITY_TRADED_COL] = pd.to_numeric(df[QUANTITY_TRADED_COL], errors="coerce")
        df[LONG_COL] = pd.to_numeric(df[LONG_COL], errors="coerce")
        df[SHORT_COL] = pd.to_numeric(df[SHORT_COL], errors="coerce")
        df["Position"] = pd.to_numeric(df["Position"], errors="coerce")
        df["Daily_PnL"] = pd.to_numeric(df["Daily_PnL"], errors="coerce")
        df["Cumulative_PnL"] = pd.to_numeric(df["Cumulative_PnL"], errors="coerce")

        # Fill NaNs
        df[OPEN_COL] = df[OPEN_COL].ffill()
        df[CLOSE_COL] = df[CLOSE_COL].ffill()
        df[VWAP_COL] = df[VWAP_COL].ffill()
        df[QUANTITY_TRADED_COL] = df[QUANTITY_TRADED_COL].fillna(0)
        df[LONG_COL] = df[LONG_COL].fillna(0)
        df[SHORT_COL] = df[SHORT_COL].fillna(0)
        df["Position"] = df["Position"].fillna(0)
        df["Daily_PnL"] = df["Daily_PnL"].fillna(0)
        df["Cumulative_PnL"] = df["Cumulative_PnL"].fillna(0)

        # ---------------- POSITION & PNL LOGIC ---------------- #
        df["Net_Qty"] = df["Position"]
        df["Prev_Net_Qty"] = df["Net_Qty"].shift(1).fillna(0)

        df["Daily_PnL_calc"] = df["Daily_PnL"]
        df["Cumulative_PnL_calc"] = df["Cumulative_PnL"]

        # ---------------- INDICATORS ---------------- #
        df["EMA_9"] = df[CLOSE_COL].ewm(span=9, adjust=False).mean()
        df["EMA_21"] = df[CLOSE_COL].ewm(span=21, adjust=False).mean()
        df["EMA_50"] = df[CLOSE_COL].ewm(span=50, adjust=False).mean()
        df["EMA_100"] = df[CLOSE_COL].ewm(span=100, adjust=False).mean()
        df["EMA_200"] = df[CLOSE_COL].ewm(span=200, adjust=False).mean()
        df["EMA_5_Longs"] = df[LONG_COL].ewm(span=5, adjust=False).mean()
        df["EMA_5_Shorts"] = df[SHORT_COL].ewm(span=5, adjust=False).mean()

        # ---------------- OHLC FOR CANDLE (synthetic high/low) ---------------- #
        df["Open"] = df[OPEN_COL]
        range_pct = 0.005
        df["High"] = df[[CLOSE_COL, "Open"]].max(axis=1) * (1 + range_pct)
        df["Low"] = df[[CLOSE_COL, "Open"]].min(axis=1) * (1 - range_pct)

        # ---------------- CLOSE vs EMA50 GAP % + COLOR ---------------- #
        df["EMA50_Close_Gap_Pct"] = ((df[CLOSE_COL] - df["EMA_50"]) * 100 / df["EMA_50"]).round(2)

        def gap_color(gap):
            if gap > 1:
                return "lime"
            elif gap < -1:
                return "red"
            else:
                return "yellow"

        df["Gap_Color"] = df["EMA50_Close_Gap_Pct"].apply(gap_color)

        # ---------------- HOVER TEXT ---------------- #
        hover_text = []
        for _, row in df.iterrows():
            cum_pnl_val = row["Cumulative_PnL_calc"]
            pnl_color = "lime" if cum_pnl_val >= 0 else "red"

            gap_pct = row["EMA50_Close_Gap_Pct"]
            gap_col = row["Gap_Color"]

            hover_text.append(
                f"<span style='color:{pnl_color}'>Cumulative P&L: {cum_pnl_val:,.2f}</span><br>"
                f"<b>Close–EMA50 Gap: <span style='color:{gap_col}'>{gap_pct:.2f}%</span></b><br>"
                f"Open: {row['Open']:.2f}<br>"
                f"High: {row['High']:.2f}<br>"
                f"Low: {row['Low']:.2f}<br>"
                f"Close: {row[CLOSE_COL]:.2f}<br>"
                f"EMA50: {row['EMA_50']:.2f}<br>"
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

        ema9_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_9"],
            mode="lines", name="EMA 9",
            line=dict(width=1.2, color="yellow")
        )
        ema21_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_21"],
            mode="lines", name="EMA 21",
            line=dict(width=1.2, color="cyan")
        )
        ema50_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_50"],
            mode="lines", name="EMA 50",
            line=dict(width=1.2, color="magenta")
        )
        ema100_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_100"],
            mode="lines", name="EMA 100",
            line=dict(width=1.5, color="white")
        )
        ema200_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_200"],
            mode="lines", name="EMA 200",
            line=dict(width=1.5, color="lightgray")
        )
        vwap_line = go.Scatter(
            x=df[DATE_COL], y=df[VWAP_COL],
            mode="lines", name="VWAP",
            line=dict(width=1.5, color="orange")
        )

        # ---------------- Longs / Shorts Panel ---------------- #
        longs_line = go.Scatter(
            x=df[DATE_COL], y=df[LONG_COL], mode="lines",
            name="Longs Till Now", line=dict(width=2, color="lime")
        )
        ema5_longs_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_5_Longs"], mode="lines",
            name="EMA 5 (Longs)", line=dict(width=1, color="green", dash="dot")
        )
        shorts_line = go.Scatter(
            x=df[DATE_COL], y=df[SHORT_COL], mode="lines",
            name="Shorts Till Now", line=dict(width=2, color="red")
        )
        ema5_shorts_line = go.Scatter(
            x=df[DATE_COL], y=df["EMA_5_Shorts"], mode="lines",
            name="EMA 5 (Shorts)", line=dict(width=1, color="darkred", dash="dot")
        )

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

        # OI PANEL
        fig.add_trace(longs_line, row=2, col=1)
        fig.add_trace(ema5_longs_line, row=2, col=1)
        fig.add_trace(shorts_line, row=2, col=1)
        fig.add_trace(ema5_shorts_line, row=2, col=1)

        # ---------------- ENTRY / EXIT TRIANGLES + PAIR LOGIC + TRADELIST ---------------- #
        entry_x, entry_y, entry_text, entry_color = [], [], [], []
        exit_x, exit_y, exit_text, exit_color = [], [], [], []

        trade_records = []
        current_entry = None  # for TradeList

        pair_id = 1
        active_pair = None
        active_type = None
        pair_entry_price = None
        pair_entry_time = None

        total_rows = len(df)
        print(f"\nBuilding trade list from {total_rows} rows...")

        for idx, row in df.iterrows():
            # progress bar for scanning rows
            print_progress_bar(idx + 1, total_rows, label="Building trade list")

            qty_traded = row[QUANTITY_TRADED_COL]
            prev_qty = row["Prev_Net_Qty"]
            curr_qty = row["Net_Qty"]

            if qty_traded == 0:
                continue  # no trade this bar

            dt = row[DATE_COL]
            price = row["Open"]
            cumulative = row["Cumulative_PnL_calc"]

            prev_s = sign(prev_qty)
            curr_s = sign(curr_qty)

            # ---------- CASE 1: PURE ENTRY (0 -> non-zero) ----------
            if prev_qty == 0 and curr_qty != 0:
                direction = "LONG" if curr_qty > 0 else "SHORT"

                entry_x.append(dt)
                entry_y.append(price)
                entry_text.append(f"{direction} ENTRY ({pair_id})")
                entry_color.append("lime" if direction == "LONG" else "red")

                active_pair = pair_id
                active_type = direction
                pair_entry_price = price
                pair_entry_time = dt

                fig.add_annotation(
                    x=1.0, y=price,
                    text=f"{active_type} ({pair_id})",
                    showarrow=False,
                    font=dict(size=10, color="lime" if active_type == "LONG" else "red"),
                    xanchor="left",
                    yanchor="middle",
                    xref="paper", yref="y1",
                )

                current_entry = {
                    "Entry_Date": dt,
                    "Entry_Row": idx,
                    "Entry_Price": price,
                    "Qty": curr_qty,
                    "Cumulative_At_Entry": cumulative,
                }
                continue

            # ---------- CASE 2: PURE EXIT (non-zero -> 0) ----------
            if prev_qty != 0 and curr_qty == 0:
                direction = "LONG" if prev_qty > 0 else "SHORT"

                exit_x.append(dt)
                exit_y.append(price)
                exit_text.append(f"{direction} EXIT ({pair_id})")
                exit_color.append("lime" if direction == "LONG" else "red")

                # Pair connector
                if active_pair is not None and pair_entry_time is not None:
                    cover_type = "LONG COVER" if active_type == "LONG" else "SHORT COVER"

                    fig.add_annotation(
                        x=1.0, y=price,
                        text=f"{cover_type} ({active_pair})",
                        showarrow=False,
                        font=dict(size=10, color="lime" if active_type == "LONG" else "red"),
                        xanchor="left",
                        yanchor="middle",
                        xref="paper", yref="y1",
                    )

                    fig.add_shape(
                        type="line",
                        x0=pair_entry_time, y0=pair_entry_price,
                        x1=dt, y1=price,
                        xref="x1", yref="y1",
                        line=dict(
                            width=2,
                            dash="dot",
                            color="lime" if active_type == "LONG" else "red",
                        ),
                    )

                    fig.add_annotation(
                        x=dt,
                        y=price,
                        ax=pair_entry_time,
                        ay=pair_entry_price,
                        xref="x1",
                        yref="y1",
                        axref="x1",
                        ayref="y1",
                        showarrow=True,
                        arrowhead=3,
                        arrowsize=2,
                        arrowcolor="lime" if active_type == "LONG" else "red",
                    )

                # TradeList close
                if current_entry is not None:
                    entry_idx = current_entry["Entry_Row"]
                    entry_date = current_entry["Entry_Date"]
                    entry_price = current_entry["Entry_Price"]
                    qty = current_entry["Qty"]
                    trade_direction = "LONG" if qty > 0 else "SHORT"

                    trade_pnl = cumulative - current_entry["Cumulative_At_Entry"]
                    trade_days = (dt - entry_date).days

                    if trade_direction == "LONG":
                        ret_pct = ((price - entry_price) / entry_price) * 100.0
                    else:
                        ret_pct = ((entry_price - price) / entry_price) * 100.0

                    trade_records.append({
                        "Entry_Row": entry_idx,
                        "Exit_Row": idx,
                        "Trade_PnL": trade_pnl,
                        "Cumulative_PnL_At_Entry": current_entry["Cumulative_At_Entry"],
                        "Cumulative_PnL_At_Exit": cumulative,
                        "Entry_Date": entry_date,
                        "Exit_Date": dt,
                        "Trade_Days": trade_days,
                        "Direction": trade_direction,
                        "Qty": qty,
                        "Entry_Price": entry_price,
                        "Exit_Price": price,
                        "Return_%": ret_pct,
                    })

                pair_id += 1
                active_pair = None
                active_type = None
                pair_entry_price = None
                pair_entry_time = None
                current_entry = None
                continue

            # ---------- CASE 3: REVERSAL (non-zero -> non-zero, sign change) ----------
            if prev_qty != 0 and curr_qty != 0 and prev_s != 0 and curr_s != 0 and prev_s != curr_s:
                # 3A: treat as EXIT for old direction
                old_direction = "LONG" if prev_qty > 0 else "SHORT"

                exit_x.append(dt)
                exit_y.append(price)
                exit_text.append(f"{old_direction} EXIT ({pair_id})")
                exit_color.append("lime" if old_direction == "LONG" else "red")

                if active_pair is not None and pair_entry_time is not None:
                    cover_type = "LONG COVER" if active_type == "LONG" else "SHORT COVER"

                    fig.add_annotation(
                        x=1.0, y=price,
                        text=f"{cover_type} ({active_pair})",
                        showarrow=False,
                        font=dict(size=10, color="lime" if active_type == "LONG" else "red"),
                        xanchor="left",
                        yanchor="middle",
                        xref="paper", yref="y1",
                    )

                    fig.add_shape(
                        type="line",
                        x0=pair_entry_time, y0=pair_entry_price,
                        x1=dt, y1=price,
                        xref="x1", yref="y1",
                        line=dict(
                            width=2,
                            dash="dot",
                            color="lime" if active_type == "LONG" else "red",
                        ),
                    )

                    fig.add_annotation(
                        x=dt,
                        y=price,
                        ax=pair_entry_time,
                        ay=pair_entry_price,
                        xref="x1",
                        yref="y1",
                        axref="x1",
                        ayref="y1",
                        showarrow=True,
                        arrowhead=3,
                        arrowsize=2,
                        arrowcolor="lime" if active_type == "LONG" else "red",
                    )

                if current_entry is not None:
                    entry_idx = current_entry["Entry_Row"]
                    entry_date = current_entry["Entry_Date"]
                    entry_price = current_entry["Entry_Price"]
                    qty = current_entry["Qty"]
                    trade_direction = "LONG" if qty > 0 else "SHORT"

                    trade_pnl = cumulative - current_entry["Cumulative_At_Entry"]
                    trade_days = (dt - entry_date).days

                    if trade_direction == "LONG":
                        ret_pct = ((price - entry_price) / entry_price) * 100.0
                    else:
                        ret_pct = ((entry_price - price) / entry_price) * 100.0

                    trade_records.append({
                        "Entry_Row": entry_idx,
                        "Exit_Row": idx,
                        "Trade_PnL": trade_pnl,
                        "Cumulative_PnL_At_Entry": current_entry["Cumulative_At_Entry"],
                        "Cumulative_PnL_At_Exit": cumulative,
                        "Entry_Date": entry_date,
                        "Exit_Date": dt,
                        "Trade_Days": trade_days,
                        "Direction": trade_direction,
                        "Qty": qty,
                        "Entry_Price": entry_price,
                        "Exit_Price": price,
                        "Return_%": ret_pct,
                    })

                pair_id += 1

                # 3B: treat as ENTRY for new direction
                new_direction = "LONG" if curr_qty > 0 else "SHORT"

                entry_x.append(dt)
                entry_y.append(price)
                entry_text.append(f"{new_direction} ENTRY ({pair_id})")
                entry_color.append("lime" if new_direction == "LONG" else "red")

                active_pair = pair_id
                active_type = new_direction
                pair_entry_price = price
                pair_entry_time = dt

                fig.add_annotation(
                    x=1.0, y=price,
                    text=f"{active_type} ({active_pair})",
                    showarrow=False,
                    font=dict(size=10, color="lime" if active_type == "LONG" else "red"),
                    xanchor="left",
                    yanchor="middle",
                    xref="paper", yref="y1",
                )

                current_entry = {
                    "Entry_Date": dt,
                    "Entry_Row": idx,
                    "Entry_Price": price,
                    "Qty": curr_qty,
                    "Cumulative_At_Entry": cumulative,
                }
                continue

            # Any other odd case is ignored.

        # ---------------- ADD TRIANGLE TRACES ---------------- #
        # entry_markers = go.Scatter(
        #     x=entry_x,
        #     y=entry_y,
        #     mode="markers",
        #     marker=dict(size=18, symbol="triangle-up", color=entry_color),
        #     name="Entry",
        #     hoverinfo="text",
        #     hovertext=entry_text,
        # )

        # exit_markers = go.Scatter(
        #     x=exit_x,
        #     y=exit_y,
        #     mode="markers",
        #     marker=dict(size=18, symbol="triangle-down", color=exit_color),
        #     name="Exit",
        #     hoverinfo="text",
        #     hovertext=exit_text,
        # )

        # fig.add_trace(entry_markers, row=1, col=1)
        # fig.add_trace(exit_markers, row=1, col=1)

        # ---------------- LAYOUT ---------------- #
        fig.update_layout(
            template="plotly_dark",
            height=980,
            hovermode="x unified",
            dragmode="pan",
        )

        fig.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.12,
                xanchor="left",
                x=0,
                font=dict(size=12),
            )
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

        # ---------------- EXPORT TRADE LIST TO EXCEL (FINAL) ---------------- #
        trades_df = pd.DataFrame(trade_records)

        if not trades_df.empty:
            # MAE/MFE using CLOSE only (optimized with numpy array)
            closes_all = df[CLOSE_COL].to_numpy()
            maes, mfes = [], []

            total_trades = len(trades_df)
            # print(f"\nCalculating MAE/MFE for {total_trades} trades...")

            # for i, trow in enumerate(trades_df.itertuples(index=False), start=1):
            #     entry_idx = int(trow.Entry_Row)
            #     exit_idx = int(trow.Exit_Row)
            #     entry_price = trow.Entry_Price
            #     direction = trow.Direction

            #     closes = closes_all[entry_idx:exit_idx + 1]

            #     if direction == "LONG":
            #         diffs = closes - entry_price
            #     else:
            #         diffs = entry_price - closes

            #     maes.append(diffs.min())
            #     mfes.append(diffs.max())

            #     print_progress_bar(i, total_trades, label="Calculating MAE/MFE")

            # trades_df["MAE"] = maes
            # trades_df["MFE"] = mfes

            # Sort & cumulative trade PnL
            trades_df = trades_df.sort_values(by="Entry_Date").reset_index(drop=True)
            trades_df["Cumulative_Trade_PnL"] = trades_df["Trade_PnL"].cumsum()

            # Format dates as dd-MM-yy (force datetime first)
            trades_df["Entry_Date"] = pd.to_datetime(trades_df["Entry_Date"]).dt.strftime("%d-%m-%y")
            trades_df["Exit_Date"] = pd.to_datetime(trades_df["Exit_Date"]).dt.strftime("%d-%m-%y")

            # Drop internal row index columns
            trades_df = trades_df.drop(columns=["Entry_Row", "Exit_Row"])

            # Final column order
            trades_df = trades_df[
                [
                    "Entry_Date",
                    "Exit_Date",
                    "Trade_Days",
                    "Direction",
                    "Entry_Price",
                    "Exit_Price",
                    "Qty",
                    "Trade_PnL",
                    "Return_%",
                    "Cumulative_Trade_PnL",
                ]
            ]

            trade_output_file = os.path.join(TARGET_DIR, f"{SYMBOL}_TradeList.xlsx")

            print("\nWriting TradeList Excel...")
            print_progress_bar(0, 1, label="Writing Excel")
            trades_df.to_excel(trade_output_file, index=False)
            print_progress_bar(1, 1, label="Writing Excel")

            # Freeze header row
            wb = load_workbook(trade_output_file)
            ws = wb.active
            ws.freeze_panes = "A2"  # freeze first row
            wb.save(trade_output_file)

            print("\nTrade List Excel (FINAL) created at:")
            print(trade_output_file)
        else:
            print("\nNo completed trades found; TradeList Excel not created.")

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
