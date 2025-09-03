# scripts/list_tls_edges.py
import os, sys
from pathlib import Path

USE_GUI = False
CFG_NAME = "north_test.sumocfg"   # or "north_test_ramped.sumocfg"
TLS_ID   = "cluster_3500447614_85576972"  # <-- put your exact ID

SUMO_HOME = os.environ.get("SUMO_HOME")
if not SUMO_HOME:
    raise SystemExit("SUMO_HOME not set")
tools = Path(SUMO_HOME) / "tools"
sys.path.insert(0, str(tools))
import traci  # noqa: E402

proj = Path(__file__).resolve().parents[1]
cfg  = proj / CFG_NAME
binary = "sumo-gui" if USE_GUI else "sumo"

def edge_of(lane_id: str) -> str:
    # lane_id like '498169188#0_0' -> '498169188#0'
    return lane_id.rsplit("_", 1)[0]

traci.start([binary, "-c", str(cfg), "--start"])
try:
    # Show all TLS IDs in the network
    print("TLS IDs in this config:", traci.trafficlight.getIDList())

    ins, outs = set(), set()
    for group in traci.trafficlight.getControlledLinks(TLS_ID):
        for inLane, outLane, viaLane in group:
            ins.add(edge_of(inLane))
            outs.add(edge_of(outLane))

    print("\nInbound edges to TLS:")
    for e in sorted(ins):
        print(" ", e)

    print("\nOutbound edges from TLS:")
    for e in sorted(outs):
        print(" ", e)

finally:
    traci.close()
