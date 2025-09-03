"""
Per-Road KPI Charts (Baseline vs AI)
- Produces bar charts and a pie chart of vehicle composition if available.

Inputs (adjust if your KPI headers differ):
  Baseline: data/baseline/kpi_by_road.csv
  AI:       runs/ai/out/kpi_by_road.csv

Outputs:
  data/comparison/*png
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

BASE = Path("data/baseline/kpi_by_road.csv")
AI   = Path("runs/ai/out/kpi_by_road.csv")
OUT  = Path("data/comparison")

def ensure_out(): OUT.mkdir(parents=True, exist_ok=True)

def load():
    return pd.read_csv(BASE), pd.read_csv(AI)

def bar_pair(df_b, df_a, key, col, title, out_png):
    m = df_b[[key, col]].merge(df_a[[key, col]], on=key, suffixes=("_base", "_ai"))
    m = m.sort_values(col + "_base").reset_index(drop=True)
    x = np.arange(len(m))
    plt.figure()
    plt.bar(x - 0.2, m[col + "_base"], width=0.4, label="Baseline")
    plt.bar(x + 0.2, m[col + "_ai"],   width=0.4, label="AI")
    plt.xticks(x, m[key], rotation=60, ha="right")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

def main():
    ensure_out()
    b, a = load()
    key = "RoadDir" if "RoadDir" in b.columns else b.columns[0]

    charts = [
        ("AvgSpeed_kph",   "Avg Speed (kph) by Road",   OUT / "roads_speed.png"),
        ("TotalWaiting_s", "Total Waiting (s) by Road", OUT / "roads_wait.png"),
        ("TotalTimeLoss_s","Total Time Loss (s) by Road", OUT / "roads_timeloss.png"),
    ]
    for col, title, out_png in charts:
        if col in b.columns and col in a.columns:
            bar_pair(b, a, key, col, title, out_png)

    print("Saved charts to", OUT)

if __name__ == "__main__":
    main()
