# scripts/controller_rule_based.py
import os
import sys
from pathlib import Path

# --- SUMO tools on path ---
SUMO_HOME = os.environ.get("SUMO_HOME")
if not SUMO_HOME:
    raise SystemExit("ERROR: SUMO_HOME not set (e.g. D:\\ulster\\SUMO)")
tools_path = Path(SUMO_HOME) / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

import traci  # noqa: E402

# ======= USER SETTINGS =======
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUMO_CFG = PROJECT_ROOT / "north_test.sumocfg"   # change to north_test_ramped.sumocfg if needed
USE_GUI = True
SIM_END = 1800
MIN_GREEN = 10      # s: minimum time we keep a green before switching
CHECK_EVERY = 2     # s: decision cadence

# Paste the exact TLS ID you printed (the one starting with "cluster_3500...")
TLS_ID = "cluster_3500447461_85576972"  # <-- REPLACE with the exact string from your console

# Phase mapping for that TLS (from your printout it alternates in phases 0 and 2)
PHASE_FOR = {"NS": 0, "EW": 2}

# Approach edges (from your RoadEdge.txt). Keep only the edges that queue **into** the junction.
APPROACH_EDGES = {
    # North arm (both directions feeding the junction)
    "N": [
        "498169188#0", "498169188#1", "498169188#2", "498169188#3",
        "24375221#0", "24375221#1", "24375221#2", "24375221#3",
    ],
    # South arm
    "S": [
        "143957229#0", "143957229#1", "143957229#2", "143957229#3",
        "143957229#4", "143957229#5", "143957229#6", "143957229#7",
        "143957229#8", "143957229#9",
        "24375222#1", "24375222#2", "24375222#3", "24375222#4",
        "24375222#5", "24375222#6", "24375222#7", "24375222#8", "24375222#9",
    ],
    # East arm
    "E": [
        "343146616#0", "343146616#1", "343146616#2", "343146616#3",
        "343146616#4", "343146616#5", "343146616#6", "343146616#7",
        "1088038754#0", "1088038754#1", "11075217#0", "11075217#1",
        "11075217#2", "11075217#3",
    ],
    # West arm
    "W": [
        "24449129#9", "24338292#1", "24338292#3", "24338292#4",
        "24338292#5", "24338292#6", "24338292#7",
        "144567412#0", "144567412#1", "144567412#2", "144567412#3",
        "144567412#5", "144567412#6", "144567412#7",
    ],
}
# ============================


def sum_queue(edge_ids):
    q = 0
    for e in edge_ids:
        try:
            q += traci.edge.getLastStepHaltingNumber(e)
        except traci.TraCIException:
            # skip edges not present in current scenario
            pass
    return q


def choose_axis():
    ns = sum_queue(APPROACH_EDGES["N"]) + sum_queue(APPROACH_EDGES["S"])
    ew = sum_queue(APPROACH_EDGES["E"]) + sum_queue(APPROACH_EDGES["W"])
    return ("NS", ns, ew) if ns >= ew else ("EW", ns, ew)


def start_sumo():
    binary = "sumo-gui" if USE_GUI else "sumo"
    traci.start([binary, "-c", str(SUMO_CFG), "--start"])


def main():
    if not SUMO_CFG.exists():
        raise SystemExit(f"Config not found: {SUMO_CFG}")

    start_sumo()
    traci.simulationStep()  # prime APIs

    # Sanity print
    tl_list = list(traci.trafficlight.getIDList())
    if not tl_list:
        traci.close()
        raise SystemExit("No traffic lights in this network.")
    print("TLS list:", tl_list)
    print("Using TLS:", TLS_ID)

    # Optional: verify phases once
    try:
        progs = traci.trafficlight.getAllProgramLogics(TLS_ID)
    except Exception:
        progs = traci.trafficlight.getCompleteRedYellowGreenDefinition(TLS_ID)
    for p in progs:
        print("Program:", getattr(p, "programID", "(no-id)"))
        for i, ph in enumerate(p.phases):
            print(f"  Phase {i}: state={ph.state}, duration={ph.duration}")

    # Initialize to best axis
    target_axis, ns_q, ew_q = choose_axis()
    traci.trafficlight.setPhase(TLS_ID, PHASE_FOR[target_axis])
    last_change = traci.simulation.getTime()

    while traci.simulation.getTime() < SIM_END:
        traci.simulationStep()
        t = traci.simulation.getTime()

        if (t - last_change) >= CHECK_EVERY:
            if (t - last_change) >= MIN_GREEN:
                # What axis is currently green?
                cur_phase = traci.trafficlight.getPhase(TLS_ID)
                cur_axis = "NS" if cur_phase == PHASE_FOR["NS"] else "EW"

                # Decide
                new_axis, ns_q, ew_q = choose_axis()
                if new_axis != cur_axis:
                    traci.trafficlight.setPhase(TLS_ID, PHASE_FOR[new_axis])
                    last_change = t
                    print(f"[t={t:.0f}] Switch to {new_axis} (NS={ns_q}, EW={ew_q})")

    traci.close()


if __name__ == "__main__":
    main()
