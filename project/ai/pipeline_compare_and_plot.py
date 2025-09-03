#!/usr/bin/env python3
"""
Pipeline: Baseline vs AI comparison + graphs.

Input (defaults; override with flags if your names differ):
- baseline dir: runs/baseline/out
- ai dir:       runs/ai/out
- road CSV:     *_kpi_by_road.csv
- trip CSV:     *_tripinfo_kpis.csv

Outputs (in --out, default: out/compare_baseline_vs_ai):
- ai_vs_baseline_road.csv
- ai_vs_baseline_trip.csv
- headline.txt                (from TimeLoss_avg_s)
- road_change_bar.png
- road_wait_pie.png           (if waiting metric present)
- trip_change_bar.png
- trip_wait_pie.png           (if waiting metric present)
"""

import argparse, csv, os, math, glob
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

def pick_path(folder: Path, pattern: str, fallback: str|None=None) -> Path:
    matches = sorted(folder.glob(pattern))
    if matches:
        return matches[0]
    if fallback:
        p = folder/fallback
        if p.exists(): return p
    raise SystemExit(f"❌ Could not find file matching '{pattern}' in {folder}")

def pct_change(base, var):
    try:
        b = float(base); v = float(var)
        if b == 0: return float("nan")
        return (v - b) / b * 100.0
    except Exception:
        return float("nan")

def compare_tables(base_csv: Path, ai_csv: Path, label: str, outdir: Path) -> Path:
    b = pd.read_csv(base_csv)
    a = pd.read_csv(ai_csv)
    if b.shape[1] < 2:
        raise SystemExit(f"❌ {base_csv} needs at least 2 columns (id + metrics).")
    key = b.columns[0]
    m = b.merge(a, on=key, suffixes=("_base", "_ai"))

    rows = []
    for col in b.columns[1:]:
        base_avg = m[f"{col}_base"].mean()
        ai_avg   = m[f"{col}_ai"].mean()
        rows.append({
            "Metric": col,
            "Baseline Avg": round(base_avg, 3),
            "AI Avg": round(ai_avg, 3),
            "Change %": round(pct_change(base_avg, ai_avg), 2)
        })
    df = pd.DataFrame(rows)
    out_csv = outdir/f"ai_vs_baseline_{label}.csv"
    df.to_csv(out_csv, index=False)
    return out_csv

def first_metric_like(cols, candidates):
    cl = [c.lower() for c in cols]
    for cand in candidates:
        for idx, c in enumerate(cl):
            if cand.lower() == c: return cols[idx]
    for cand in candidates:
        for idx, c in enumerate(cl):
            if cand.lower() in c: return cols[idx]
    return None

def bar_and_pie(compare_csv: Path, label: str, outdir: Path):
    df = pd.read_csv(compare_csv)
    # Bar: percent changes per metric
    plt.figure(figsize=(10,6))
    plt.bar(df["Metric"], df["Change %"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Change (%)")
    plt.title(f"AI vs Baseline: {label} KPI change")
    plt.tight_layout()
    bar_path = outdir/f"{label.lower()}_change_bar.png"
    plt.savefig(bar_path, dpi=300)
    plt.close()

    # Pie for waiting metrics (if present)
    wait_rows = df[df["Metric"].str.lower().str.contains("wait")]
    pie_path = None
    if not wait_rows.empty:
        base_total = wait_rows["Baseline Avg"].sum()
        ai_total   = wait_rows["AI Avg"].sum()
        plt.figure(figsize=(6,6))
        plt.pie([base_total, ai_total], labels=["Baseline","AI"], autopct="%1.1f%%")
        plt.title(f"Total Waiting Time Share ({label})")
        plt.tight_layout()
        pie_path = outdir/f"{label.lower()}_wait_pie.png"
        plt.savefig(pie_path, dpi=300)
        plt.close()

    return bar_path, pie_path

def headline_from_trip(trip_base: Path, trip_ai: Path, outdir: Path):
    # Expect columns incl: Group,N,Dur_avg_s,Dur_p5_s,Dur_p95_s,Wait_avg_s,TimeLoss_avg_s
    tb = pd.read_csv(trip_base)
    ta = pd.read_csv(trip_ai)
    def pick_all(df):
        if "Group" in df.columns:
            mask = df["Group"].astype(str).str.lower().eq("all")
            if mask.any(): return df.loc[mask].iloc[0].to_dict()
        return df.mean(numeric_only=True).to_dict()
    b = pick_all(tb); a = pick_all(ta)
    metric = "TimeLoss_avg_s" if "TimeLoss_avg_s" in tb.columns else None
    if not metric:
        # fallback: try a close name
        metric = first_metric_like(tb.columns, ["timeloss", "time_loss"])
    if not metric: return None
    bval = float(b[metric]); aval = float(a[metric])
    delta_pct = pct_change(bval, aval)
    word = "decreased" if aval < bval else "increased"
    text = (f"Average time loss {word} by {abs(delta_pct):.1f}% "
            f"(baseline {bval:.2f}s → AI {aval:.2f}s).")
    (outdir/"headline.txt").write_text(text + "\n", encoding="utf-8")
    return text

def main():
    ap = argparse.ArgumentParser(description="Compare Baseline vs AI (road + trip) and plot graphs.")
    ap.add_argument("--base", default="runs/baseline/out", help="Baseline folder containing *_kpi_by_road.csv and *_tripinfo_kpis.csv")
    ap.add_argument("--ai",   default="runs/ai/out",       help="AI folder containing *_kpi_by_road.csv and *_tripinfo_kpis.csv")
    ap.add_argument("--out",  default="out/compare_baseline_vs_ai", help="Output folder")
    # optional overrides
    ap.add_argument("--base-road", default=None)
    ap.add_argument("--base-trip", default=None)
    ap.add_argument("--ai-road",   default=None)
    ap.add_argument("--ai-trip",   default=None)
    args = ap.parse_args()

    base_dir = Path(args.base); ai_dir = Path(args.ai); outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # Resolve filenames (pattern search with sensible defaults)
    base_road = Path(args.base_road) if args.base_road else pick_path(base_dir, "*kpi_by_road*.csv")
    base_trip = Path(args.base_trip) if args.base_trip else pick_path(base_dir, "*tripinfo_kpis*.csv")
    ai_road   = Path(args.ai_road)   if args.ai_road   else pick_path(ai_dir,   "*kpi_by_road*.csv")
    ai_trip   = Path(args.ai_trip)   if args.ai_trip   else pick_path(ai_dir,   "*tripinfo_kpis*.csv")

    print(f"[INFO] baseline road: {base_road}")
    print(f"[INFO] baseline trip: {base_trip}")
    print(f"[INFO] AI road:       {ai_road}")
    print(f"[INFO] AI trip:       {ai_trip}")
    print(f"[INFO] out:           {outdir}")

    # 1) CSV comparisons
    road_cmp = compare_tables(base_road, ai_road, "road", outdir)
    trip_cmp = compare_tables(base_trip, ai_trip, "trip", outdir)
    print(f"[OK] wrote {road_cmp}")
    print(f"[OK] wrote {trip_cmp}")

    # 2) Headline from trip KPIs
    head = headline_from_trip(base_trip, ai_trip, outdir)
    if head:
        print("[HEADLINE]", head)

    # 3) Graphs (separate)
    rb, rp = bar_and_pie(road_cmp, "Road-level", outdir)
    tb, tp = bar_and_pie(trip_cmp, "Trip-level", outdir)
    print("[OK] charts:", rb, rp, tb, tp)

if __name__ == "__main__":
    main()
