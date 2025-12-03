import subprocess
import sys
import os

# --- Script file names (make sure these match exactly your filenames) ---
SCRIPT_1 = "GenerateThresholds.py"       # Analysis generator
SCRIPT_2 = "GenerateAnalysis.py"
SCRIPT_3 = "MLTrainer.py"

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

    run_script(SCRIPT_1)   # Step 1 → Train ML
    run_script(SCRIPT_2)   # Step 2 → Generate Analysis
    run_script(SCRIPT_3)   # Step 3 → Generate Trades
    # run_script(SCRIPT_4)   # Step 4 → Generate final Plotly chart

    print("\n🎉 ALL SCRIPTS EXECUTED SUCCESSFULLY!")
