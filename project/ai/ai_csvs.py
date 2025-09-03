"""
AI KPI CSV Generator (wrapper)
- Reads AI run outputs (tripinfo.xml, edgeData.xml) and produces KPI CSVs.
- Thin wrapper around your existing 'scripts/kpi_by_road.py'. If that script
  is not found, it will error with a clear message.

Usage:
  python ai/ai_csvs.py --edge runs/ai/out/edgeData.xml --trip runs/ai/out/tripinfo.xml --out runs/ai/out
"""
import argparse
import subprocess
from pathlib import Path
import sys

def parse_args():
    p = argparse.ArgumentParser(description="Generate KPI CSVs from AI run outputs")
    p.add_argument("--edge", required=True, help="edgeData.xml path")
    p.add_argument("--trip", required=True, help="tripinfo.xml path")
    p.add_argument("--out",  required=True, help="output folder for CSVs")
    return p.parse_args()

def main():
    args = parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    kpi_script = Path("scripts") / "kpi_by_road.py"
    if not kpi_script.exists():
        sys.exit("ERROR: scripts/kpi_by_road.py not found. Put your KPI script there or adjust paths.")

    cmd = [sys.executable, str(kpi_script),
           "--edge", args.edge,
           "--trip", args.trip,
           "--out", str(out)]
    print("Running:", " ".j
