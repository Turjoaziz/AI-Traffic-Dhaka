"""
Min-Queue AI TLS Controller (TraCI)
- Controls ONE traffic light (TLS) using a greedy queue-minimising policy.
- Action each decision step: keep current phase OR switch to the phase whose approaches have the highest halting queue.
- Respects a configurable minimum green.

Usage (example):
  python ai/minqueue_tls.py --cfg runs/north_test.sumocfg --tls <TLS_ID> --out runs/ai/out --min-green 8 --step 1.0

Outputs:
  - tripinfo.xml and edgeData.xml inside --out (enable via additional options passed through --sumo-args)
Dependencies:
  - SUMO installed, SUMO_HOME set
"""
import os, sys, time
import argparse
from pathlib import Path

# --- SUMO / TraCI bootstrap ---
SUMO_HOME = os.environ.get("SUMO_HOME")
if not SUMO_HOME:
    raise SystemExit("ERROR: SUMO_HOME not set. Set it to your SUMO installation folder.")
tools = Path(SUMO_HOME) / "tools"
sys.path.insert(0, str(tools))
import traci  # noqa: E402

def parse_args():
    p = argparse.ArgumentParser(description="Min-Queue AI TLS Controller (TraCI)")
    p.add_argument("--cfg", required=True, help="*.sumocfg path")
    p.add_argument("--tls", required=True, help="Traffic light ID to control")
    p.add_argument("--out", required=True, help="Output folder (will be created)")
    p.add_argument("--min-green", type=float, default=8.0, help="Minimum green seconds before allowing a switch")
    p.add_argument("--step", type=float, default=1.0, help="Simulation step length (s)")
    p.add_argument("--nogui", action="store_true", help="Use sumo (CLI) instead of sumo-gui")
    p.add_argument("--until", type=float, default=None, help="Optional hard stop time (s); if omitted, uses cfg end time")
    p.add_argument("--sumo-args", default="", help="Extra args passed to SUMO, e.g. '--time-to-teleport -1'")
    return p.parse_args()

def start_sumo(cfg: str, use_gui: bool, step_len: float, extra_args: str):
    binary = "sumo-gui" if use_gui else "sumo"
    cmd = [binary, "-c", cfg, "--step-length", str(step_len)]
    if extra_args:
        cmd += extra_args.split()
    traci.start(cmd)

def group_links_by_phase(tls_id: str):
    """
    Build:
      - phases: list of phase states (e.g., 'GrGr...')
      - link_phase_map: dict[phase_index] -> set(incoming_lane_ids that are served with green in that phase)
    """
    # We take the current complete program (assumes single program)
    progs = traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)
    if not progs:
        raise RuntimeError(f"No signal program for TLS '{tls_id}'")
    prog = progs[0]
    phases = prog.getPhases()
    # link structure: for each controlled link index, we get tuples of (incoming, outgoing, via)
    links = traci.trafficlight.getControlledLinks(tls_id)  # list[list[ (in, out, via) ]]
    controlled_lanes = [triple[0][0] if triple else None for triple in links]

    link_phase_map = {pi: set() for pi in range(len(phases))}
    for pi, ph in enumerate(phases):
        st = ph.state
        # For each signal group index (character in phase state)
        for gi, ch in enumerate(st):
            if gi < len(controlled_lanes) and ch in ("G", "g"):
                lane_in = controlled_lanes[gi]
                if lane_in:
                    link_phase_map[pi].add(lane_in)
    return phases, link_phase_map

def queue_for_lanes(lanes: set[str]) -> int:
    q = 0
    for ln in lanes:
        try:
            q += traci.lane.getLastStepHaltingNumber(ln)
        except traci.TraCIException:
            # Lane might disappear in some dynamic nets; ignore gracefully
            pass
    return q

def run_controller(tls_id: str, min_green: float, decision_period: float, until: float|None):
    phases, link_phase_map = group_links_by_phase(tls_id)
    if len(phases) == 0:
        raise RuntimeError(f"TLS '{tls_id}' has no phases.")

    last_switch_time = -1e9
    sim_time = traci.simulation.getTime()
    # Ensure we’re on a valid phase index
    cur_phase = traci.trafficlight.getPhase(tls_id)

    while True:
        sim_time = traci.simulation.getTime()
        if until is not None and sim_time >= until:
            break
        if traci.simulation.getMinExpectedNumber() <= 0:
            # no vehicles left and no ones are expected
            break

        # Decide only every 'decision_period' seconds (aligned to step-length)
        # Here we simply check every step; you can throttle if you like.
        time_since_switch = sim_time - last_switch_time

        # Compute queues by candidate phase
        phase_queues = []
        for pi in range(len(phases)):
            q = queue_f_
