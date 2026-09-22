"""
One-Click Master Launcher for SIH Forecast Bust Detection Prototype
Starts both the FastAPI backend and Streamlit dashboard, and opens the dashboard in the browser.
"""

import os
import subprocess
import sys
import time
import webbrowser

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

def main():
    print("=" * 70)
    print("  NCMRWF / Ministry of Earth Sciences - SIH Prototype Launcher")
    print("  AI-Based Forecast Bust Detection for Medium-Range NWP Forecasts")
    print("=" * 70)

    # 1. Check if model exists, train if missing
    if not os.path.exists(os.path.join(PROJECT_ROOT, "models", "reliability_model.joblib")):
        print("\n[!] Trained models not detected. Generating non-circular dataset & training models...")
        subprocess.run([sys.executable, "-m", "src.data.synthetic"], cwd=PROJECT_ROOT, check=True)
        subprocess.run([sys.executable, "src/train_model.py"], cwd=PROJECT_ROOT, check=True)

    # 2. Start FastAPI in background
    print("\n[1/3] Launching FastAPI Backend (http://127.0.0.1:8000)...")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=PROJECT_ROOT,
    )
    time.sleep(2)

    # 3. Start Streamlit Dashboard
    print("[2/3] Launching Streamlit Operational Dashboard (http://localhost:8502)...")
    st_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.port", "8502", "--server.headless", "true"],
        cwd=PROJECT_ROOT,
    )
    time.sleep(3)

    # 4. Open browser
    dashboard_url = "http://localhost:8502"
    print(f"\n[3/3] Opening Dashboard in browser: {dashboard_url}")
    webbrowser.open(dashboard_url)

    print("\n" + "=" * 70)
    print("  SYSTEM ONLINE AND READY!")
    print("  - Streamlit Forecaster Dashboard: http://localhost:8502")
    print("  - FastAPI Interactive Docs:       http://127.0.0.1:8000/docs")
    print("  Press Ctrl+C to stop all servers.")
    print("=" * 70 + "\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down services...")
        api_proc.terminate()
        st_proc.terminate()
        print("Servers stopped cleanly.")


if __name__ == "__main__":
    main()
