import os
import pandas as pd
from openpyxl import load_workbook
from utils_progress import print_progress_bar  # type: ignore
from config_loader import load_config  # type: ignore

cfg = load_config()
TARGET_DIR = cfg["TARGET_DIRECTORY"]
SYMBOL = cfg["SYMBOL"]

TEMP_FILE = os.path.join(TARGET_DIR, f"{SYMBOL}_TradeRecords_TMP.csv")
OUTPUT_EXCEL = os.path.join(TARGET_DIR, f"{SYMBOL}_TradeList.xlsx")


def generate_excel():
    print("\n--- Excel TradeList Generator ---\n")

    if not os.path.exists(TEMP_FILE):
        print("ERROR: Temp file not found:", TEMP_FILE)
        return

    df = pd.read_csv(TEMP_FILE, parse_dates=["Entry_Date", "Exit_Date"])

    if df.empty:
        print("No trades found. Excel not generated.")
        return

    df.sort_values("Entry_Date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Format date columns
    df["Entry_Date"] = df["Entry_Date"].dt.strftime("%d-%m-%y")
    df["Exit_Date"] = df["Exit_Date"].dt.strftime("%d-%m-%y")

    # Use Return_% already computed from PlotChart (DO NOT RECALCULATE)
    if "Return_%" not in df.columns:
        df["Return_%"] = ((df["Exit_Price"] - df["Entry_Price"]) / df["Entry_Price"] * 100) \
            .where(df["Direction"] == "LONG",
                   (df["Entry_Price"] - df["Exit_Price"]) / df["Entry_Price"] * 100)

    # Cumulative P&L
    df["Cumulative_Trade_PnL"] = df["Trade_PnL"].cumsum()

    # Column order
    cols = [
        "Entry_Date", "Exit_Date", "Trade_Days",
        "Direction", "Entry_Price", "Exit_Price", "Qty",
        "Trade_PnL", "Return_%", "Cumulative_Trade_PnL"
    ]
    df = df[cols]

    print("\nWriting Excel file...")
    print_progress_bar(0, 1, label="Writing Excel")
    df.to_excel(OUTPUT_EXCEL, index=False)
    print_progress_bar(1, 1, label="Writing Excel finished")

    # Freeze header
    wb = load_workbook(OUTPUT_EXCEL)
    ws = wb.active
    ws.freeze_panes = "A2"
    wb.save(OUTPUT_EXCEL)

    print("\nExcel file created:", OUTPUT_EXCEL)


if __name__ == "__main__":
    generate_excel()
