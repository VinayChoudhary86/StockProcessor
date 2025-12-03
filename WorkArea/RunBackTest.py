import subprocess
import sys
import os

# Order of execution:
# 1. Generate thresholds
# 2. Generate analysis
# 3. Run walk-forward ML trainer
# 4. Generate walk-forward trades
# 5. (Optional) Plot chart

SCRIPTS = [
    "GenerateThresholds.py",
    "GenerateAnalysis.py",
    "WalkForwardTrainer.py",
    "GenerateMLTrades_WF.py",
    # "PlotChart.py",   # Uncomment if you want chart generation automatically
]

def run_script(script_name):
    print(f"\n=======================================")
    print(f" RUNNING: {script_name}")
    print(f"=======================================\n")

    if not os.path.exists(script_name):
        print(f"❌ ERROR: Script not found: {script_name}")
        sys.exit(1)

    result = subprocess.run([sys.executable, script_name])

    if result.returncode != 0:
        print(f"❌ ERROR: Script failed: {script_name}")
        sys.exit(result.returncode)

    print(f"\n✅ COMPLETED: {script_name}\n")


def main():
    print("\n=======================================")
    print(" WALK-FORWARD ML BACKTEST PIPELINE")
    print("=======================================\n")

    for script in SCRIPTS:
        run_script(script)

    print("\n=======================================")
    print(" PIPELINE COMPLETED SUCCESSFULLY 🎉")
    print("=======================================\n")


if __name__ == "__main__":
    main()
