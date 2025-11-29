import subprocess
import sys
import os

# --- Script file names (make sure these match exactly your filenames) ---
SCRIPT_1 = "TrainModel.py"       # Analysis generator
SCRIPT_2 = "GenerateAnalysis.py"
SCRIPT_3 = "GenerateTrades.py"   # Trade generator
SCRIPT_4 = "PlotChart.py"      # Interactive chart1

# --- Helper to run a script ---
def run_script(script_name):
    print("\n" + "="*80)
    print(f"RUNNING: {script_name}")
    print("="*80)

    if not os.path.exists(script_name):
        print(f"ERROR: Script not found: {script_name}")
        sys.exit(1)

    result = subprocess.run([sys.executable, script_name])
    if result.returncode != 0:
        print(f"\n❌ ERROR running {script_name}")
        sys.exit(result.returncode)
    else:
        print(f"\n✅ COMPLETED: {script_name}")

# --- Main sequence ---
if __name__ == "__main__":
    print("\n========================")
    print(" V- RUNNING FULL PIPELINE ")
    print("========================")

    run_script(SCRIPT_1)   # Step 1 → Generate analysis file
    run_script(SCRIPT_2)   # Step 2 → Generate trades
    run_script(SCRIPT_3)   # Step 3 → Generate final Plotly chart
    run_script(SCRIPT_4)

    print("\n🎉 ALL SCRIPTS EXECUTED SUCCESSFULLY!")
