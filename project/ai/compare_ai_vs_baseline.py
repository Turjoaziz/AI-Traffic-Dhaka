"""
Compare Baseline vs AI KPIs
- Expects baseline CSVs and AI CSVs (produced by your KPI script).
- Produces a text summary and several PNG charts for the report.

Defaults (adjust as needed):
  Baseline CSVs: data/baseline/kpi_by_road.csv  and data/baseline/tripinfo_kpis.csv
  AI CSVs:       runs/ai/out/kpi_by_road.csv    and runs/ai/out/tripinfo_kpis.csv
  Outputs:       data/comparison/

Usage:
  python ai/compare_ai_vs_baseline.py
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json

BASE_KPI_BY_ROAD = Path("data/baseline/kpi_by_road.csv")
BASE_TRIP_KPIS   = Path("data/baseline/tripinfo_kpis.csv")
AI_KPI_BY_ROAD   = Path("runs/ai/out/kpi_by_road.csv")
AI_TRIP_KPIS     = Path("runs/ai/out/tripinfo_kpis.csv")
OUT_DIR          = Path("data/comparison")

def pct(a, b):
    return (a - b) / b * 100.0 if b != 0 else np.nan

def ensure_out():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_csvs():
    b1 = pd.read_csv(BASE_KPI_BY_ROAD)
    a1 = pd.read_csv(AI_KPI_BY_ROAD)
    bt = pd.read_csv(BASE_TRIP_KPIS)
    at = pd.read_csv(AI_TRIP_KPIS)
    return b1, a1, bt, at

def summarize_tripinfo(bt: pd.DataFrame, at: pd.DataFrame):
    # Expect columns: Group, N, Dur_avg_s, Wait_avg_s, TimeLoss_avg_s (your KPI script should emit something like this)
    b_overall = bt[bt["Group"] == "overall"].iloc[0]
    a_overall = at[at["Group"] == "overall"].iloc[0]
    summary = {
        "N_diff": int(a_overall["N"] - b_overall["N"]),
        "Dur_avg_pct": pct(a_overall["Dur_avg_s"], b_overall["Dur_avg_s"]),
        "Wait_avg_pct": pct(a_overall["Wait_avg_s"], b_overall["Wait_avg_s"]),
        "TimeLoss_avg_pct": pct(a_overall["TimeLoss_avg_s"], b_overall["TimeLoss_avg_s"]),
    }
    return summary

def bar_compare(df_b, df_a, col, title, out_png):
    # Merge on RoadDir (or whatever id your KPI has)
    key = "RoadDir" if "RoadDir" in df_b.columns else df_b.columns[0]
    m = df_b[[key, col]].merge(df_a[[key, col]], on=key, suffixes=("_base", "_ai"))
    m = m.sort_values(col + "_base").reset_index(drop=True)

    plt.figure()
    X = np.arange(len(m))
    plt.bar(X - 0.2, m[col + "_base"], width=0.4, label="Baseline")
    plt.bar(X + 0.2, m[col + "_ai"],   width=0.4, label="AI")
    plt.xticks(X, m[key], rotation=60, ha="right")
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=160)
    plt.close()

def main():
    ensure_out()
    b1, a1, bt, at = load_csvs()

    # Text summary (overall)
    overall = summarize_tripinfo(bt, at)
    (OUT_DIR / "overall_summary.json").write_text(json.dumps(overall, indent=2))
    print("Overall deltas (% change vs baseline):", overall)

    # Charts by road
    metrics = [
        ("AvgSpeed_kph", "Average Speed (kph) by Road", OUT_DIR / "byroad_speed.png"),
        ("TotalWaiting_s", "Total Waiting Time (s) by Road", OUT_DIR / "byroad_wait.png"),
        ("TotalTimeLoss_s", "Total Time Loss (s) by Road", OUT_DIR / "byroad_timeloss.png"),
    ]
    for col, title, out_png in metrics:
        if col in b1.columns and col in a1.columns:
            bar_compare(b1, a1, col, title, out_png)

    print("Comparison outputs saved to:", OUT_DIR)

if __name__ == "__main__":
    main()
