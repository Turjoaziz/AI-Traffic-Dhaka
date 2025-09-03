import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# ---------- paths ----------
BASE_KPI = r"runs\baseline\out\b_kpi_by_road.csv"
VAR_KPI  = r"runs\ramped\out\r_kpi_by_road.csv"
OUTDIR   = Path(r"runs\comparison_graphs")
OUTDIR.mkdir(parents=True, exist_ok=True)

# ---------- helpers ----------
def pick_col(cols, candidates):
    """return first matching column (case-insensitive)"""
    cl = {c.lower(): c for c in cols}
    for cand in candidates:
        for c in cols:
            if c.lower() == cand.lower():
                return c
    # loose contains match
    for cand in candidates:
        for c in cols:
            if cand.lower() in c.lower():
                return c
    raise KeyError(f"None of {candidates} found in columns: {list(cols)}")

# ---------- load ----------
b = pd.read_csv(BASE_KPI)
v = pd.read_csv(VAR_KPI)

# key column (first col, e.g. RoadDir)
key_col = b.columns[0]

# detect KPI columns present in your files
speed_col  = pick_col(b.columns, ["AvgSpeed_kph","avg_speed_kph","avg_speed"])
wait_col   = pick_col(b.columns, ["TotalWaiting_s","waiting","total_waiting"])
tloss_col  = pick_col(b.columns, ["TotalTimeLoss_s","time_loss","total_time_loss"])

# merge with clean suffixes
m = b.merge(v, on=key_col, suffixes=("_b","_r"))

# compute deltas
for col in [speed_col, wait_col, tloss_col]:
    m[f"{col}_delta"] = m[f"{col}_r"] - m[f"{col}_b"]

# save comparison table
m.to_csv(OUTDIR / "kpi_comparison.csv", index=False)
print(f"✅ Saved table → {OUTDIR/'kpi_comparison.csv'}")

# -------- charts --------
# 1) Average speed per road
plt.figure(figsize=(11,6))
plt.bar(m[key_col], m[f"{speed_col}_b"], alpha=0.7, label="Baseline")
plt.bar(m[key_col], m[f"{speed_col}_r"], alpha=0.7, label="Ramped")
plt.xlabel(key_col); plt.ylabel("Average Speed (kph)")
plt.title("Average Speed by Road: Baseline vs Ramped")
plt.xticks(rotation=45, ha="right"); plt.legend(); plt.tight_layout()
plt.savefig(OUTDIR / "avg_speed_comparison.png", dpi=300); plt.close()

# 2) Total time loss per road
plt.figure(figsize=(11,6))
plt.bar(m[key_col], m[f"{tloss_col}_b"], alpha=0.7, label="Baseline")
plt.bar(m[key_col], m[f"{tloss_col}_r"], alpha=0.7, label="Ramped")
plt.xlabel(key_col); plt.ylabel("Total Time Loss (s)")
plt.title("Total Time Loss by Road: Baseline vs Ramped")
plt.xticks(rotation=45, ha="right"); plt.legend(); plt.tight_layout()
plt.savefig(OUTDIR / "time_loss_comparison.png", dpi=300); plt.close()

# 3) Network pie – share of total time loss
tot_b = m[f"{tloss_col}_b"].sum()
tot_r = m[f"{tloss_col}_r"].sum()
plt.figure(figsize=(6,6))
plt.pie([tot_b, tot_r], labels=["Baseline","Ramped"], autopct="%1.1f%%")
plt.title("Share of Total Network Time Loss")
plt.tight_layout()
plt.savefig(OUTDIR / "time_loss_pie.png", dpi=300); plt.close()

print("📊 Saved:",
      OUTDIR / "avg_speed_comparison.png",
      OUTDIR / "time_loss_comparison.png",
      OUTDIR / "time_loss_pie.png", sep="\n• ")
