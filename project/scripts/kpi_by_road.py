# kpi_by_road.py
# Summarize SUMO outputs: per-road/direction KPIs from edgeData.xml,
# and overall/by-type trip KPIs from tripinfo.xml.

from pathlib import Path
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
import csv
import math

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "out"
EDGE_XML = OUT_DIR / "edgeData.xml"
TRIP_XML = OUT_DIR / "tripinfo.xml"

# ---- Update if you change edges in your routes ----
EDGE_GROUPS = {
    "North_up":  ["498169188#0","498169188#1","498169188#2","498169188#3"],
    "North_down":["24375221#0","24375221#1","24375221#2","24375221#3"],

    "South_up":  ["143957229#0","143957229#1","143957229#2","143957229#3",
                  "143957229#4","143957229#5","143957229#6","143957229#7",
                  "143957229#8","143957229#9"],
    "South_down":["24375222#1","24375222#2","24375222#3","24375222#4",
                  "24375222#5","24375222#6","24375222#7","24375222#8",
                  "24375222#9"],

    "East_up":   ["343146616#0","343146616#1","343146616#2","343146616#3",
                  "343146616#4","343146616#5","343146616#6","343146616#7"],
    "East_down": ["1088038754#0","1088038754#1",
                  "11075217#0","11075217#1","11075217#2","11075217#3"],

    "West_up":   ["24449129#9","24338292#1","24338292#3","24338292#4",
                  "24338292#5","24338292#6","24338292#7"],
    "West_down": ["144567412#0","144567412#1","144567412#2","144567412#3",
                  "144567412#5","144567412#6","144567412#7"],
}

def pct(values, p):
    if not values:
        return float("nan")
    values = sorted(values)
    k = (len(values)-1) * (p/100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return values[int(k)]
    d0 = values[f] * (c - k)
    d1 = values[c] * (k - f)
    return d0 + d1

def summarize_edgeData(xml_path: Path):
    if not xml_path.exists():
        raise SystemExit(f"[ERROR] Missing {xml_path}")
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # aggregate by our custom road groups
    sums = defaultdict(lambda: {
        "sampledSeconds":0.0,
        "nVehContrib":0.0,
        "waitingTime":0.0,
        "timeLoss":0.0,
        "speed_weighted_sum":0.0,  # m/s * weight
        "weight_sum":0.0
    })

    # quick reverse map: edge_id -> group
    edge_to_group = {}
    for g, edges in EDGE_GROUPS.items():
        for e in edges:
            edge_to_group[e] = g

    for interval in root.findall("interval"):
        for e in interval.findall("edge"):
            eid = e.attrib.get("id", "")
            g = edge_to_group.get(eid)
            if not g:
                continue  # ignore edges outside our groups

            ss  = float(e.attrib.get("sampledSeconds", 0.0))
            nvc = float(e.attrib.get("nVehContrib", 0.0))
            wt  = float(e.attrib.get("waitingTime", 0.0))
            tl  = float(e.attrib.get("timeLoss", 0.0))
            spd = float(e.attrib.get("speed", 0.0))  # m/s

            weight = nvc if nvc > 0 else ss
            sums[g]["sampledSeconds"]      += ss
            sums[g]["nVehContrib"]         += nvc
            sums[g]["waitingTime"]         += wt
            sums[g]["timeLoss"]            += tl
            sums[g]["speed_weighted_sum"]  += spd * weight
            sums[g]["weight_sum"]          += weight

    # compute KPIs
    rows = []
    for g, v in sums.items():
        denom = v["weight_sum"] if v["weight_sum"] > 0 else 1.0
        avg_speed_mps = v["speed_weighted_sum"] / denom
        rows.append({
            "RoadDir": g,
            "AvgSpeed_mps": round(avg_speed_mps, 3),
            "AvgSpeed_kph": round(avg_speed_mps * 3.6, 3),
            "TotalWaiting_s": round(v["waitingTime"], 2),
            "TotalTimeLoss_s": round(v["timeLoss"], 2),
            "Samples_weight": round(denom, 2),
            "nVehContrib_sum": round(v["nVehContrib"], 2),
        })
    return rows

def summarize_tripinfo(xml_path: Path):
    if not xml_path.exists():
        raise SystemExit(f"[ERROR] Missing {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # overall and by vType
    durations_by = defaultdict(list)
    wait_by = defaultdict(list)
    loss_by = defaultdict(list)

    for ti in root.findall("tripinfo"):
        vtype = ti.attrib.get("vType", "ALL")
        dur = float(ti.attrib.get("duration", 0.0))
        wt  = float(ti.attrib.get("waitingTime", 0.0))
        tl  = float(ti.attrib.get("timeLoss", 0.0))

        durations_by["ALL"].append(dur)
        wait_by["ALL"].append(wt)
        loss_by["ALL"].append(tl)

        durations_by[vtype].append(dur)
        wait_by[vtype].append(wt)
        loss_by[vtype].append(tl)

    def make_rows(label):
        arr_d = durations_by[label]
        arr_w = wait_by[label]
        arr_l = loss_by[label]
        n = len(arr_d)
        if n == 0:
            return {
                "Group": label, "N": 0,
                "Dur_avg_s": "NA", "Dur_p50_s": "NA", "Dur_p95_s": "NA",
                "Wait_avg_s": "NA", "TimeLoss_avg_s": "NA"
            }
        return {
            "Group": label,
            "N": n,
            "Dur_avg_s": round(sum(arr_d)/n, 3),
            "Dur_p50_s": round(pct(arr_d, 50), 3),
            "Dur_p95_s": round(pct(arr_d, 95), 3),
            "Wait_avg_s": round(sum(arr_w)/n, 3),
            "TimeLoss_avg_s": round(sum(arr_l)/n, 3),
        }

    labels = list(durations_by.keys())
    rows = [make_rows(lbl) for lbl in sorted(labels, key=lambda x: (x!="ALL", x))]
    return rows

def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
def _parse_args():
    ap = argparse.ArgumentParser(description="SUMO KPI extractor")
    ap.add_argument("--edge", default="out/edgeData.xml", help="path to edgeData.xml")
    ap.add_argument("--trip", default="out/tripinfo.xml", help="path to tripinfo.xml")
    ap.add_argument("--out",  dest="outdir", default="out", help="output directory for CSVs")
    return ap.parse_args()

def main():
    args = _parse_args()

    # use globals if your helpers reference these names
    global EDGE_XML, TRIP_XML, OUT_DIR
    EDGE_XML = Path(args.edge)
    TRIP_XML = Path(args.trip)
    OUT_DIR  = Path(args.outdir)

    print(f"[INFO] Reading: {EDGE_XML}")
    print(f"[INFO] Reading: {TRIP_XML}")

    print("[INFO] Reading:", EDGE_XML)
    edge_rows = summarize_edgeData(EDGE_XML)
    edge_csv = OUT_DIR / "kpi_by_road.csv"
    write_csv(edge_csv, edge_rows, fieldnames=[
        "RoadDir","AvgSpeed_mps","AvgSpeed_kph",
        "TotalWaiting_s","TotalTimeLoss_s",
        "Samples_weight","nVehContrib_sum"
    ])
    print("[OK] Wrote", edge_csv)

    print("[INFO] Reading:", TRIP_XML)
    trip_rows = summarize_tripinfo(TRIP_XML)
    trip_csv = OUT_DIR / "tripinfo_kpis.csv"
    write_csv(trip_csv, trip_rows, fieldnames=[
        "Group","N","Dur_avg_s","Dur_p50_s","Dur_p95_s","Wait_avg_s","TimeLoss_avg_s"
    ])
    print("[OK] Wrote", trip_csv)

    # Also print to console for a quick glance
    print("\n=== Per Road/Direction (edgeData) ===")
    for r in edge_rows:
        print(r)
    print("\n=== Trip KPIs (tripinfo) ===")
    for r in trip_rows:
        print(r)

if __name__ == "__main__":
    main()
