# scripts/print_tls_phases.py
import os
import sys
from pathlib import Path

# ---------- CONFIG ----------
USE_GUI = True  # True = sumo-gui, False = sumo
# Pick which config to inspect:
CFG_NAME = "north_test.sumocfg"         # or "north_test_ramped.sumocfg"
# ----------------------------

# Resolve SUMO tools
SUMO_HOME = os.environ.get("SUMO_HOME")
if not SUMO_HOME:
    raise SystemExit("ERROR: SUMO_HOME not set. Set it to your SUMO install folder, e.g. D:\\ulster\\SUMO")

tools_path = Path(SUMO_HOME) / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

import traci  # noqa: E402

# Resolve paths relative to project root (this file is in project/scripts/)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
CFG_PATH = PROJECT_ROOT / CFG_NAME

if not CFG_PATH.exists():
    raise SystemExit(f"ERROR: Config not found: {CFG_PATH}")

SUMO_BINARY = "sumo-gui" if USE_GUI else "sumo"

def get_program_logics(tls_id):
    """
    Use the new API if available to avoid deprecation warnings,
    fall back to the old one for older SUMO versions.
    """
    try:
        # Newer SUMO
        return traci.trafficlight.getAllProgramLogics(tls_id)
    except Exception:
        # Older SUMO
        return traci.trafficlight.getCompleteRedYellowGreenDefinition(tls_id)

def main():
    traci.start([SUMO_BINARY, "-c", str(CFG_PATH), "--start"])
    try:
        tls_ids = traci.trafficlight.getIDList()
        print("TLS IDs:", list(tls_ids))

        if not tls_ids:
            print("No traffic lights in this network.")
            return

        for tls in tls_ids:
            print("\nTLS:", tls)
            progs = get_program_logics(tls)
            for p in progs:
                print(" Program:", getattr(p, "programID", "(no-id)"))
                # p.phases is a list of Phase objects: .state (e.g., rGrG), .duration, etc.
                for i, ph in enumerate(p.phases):
                    print(f"  Phase {i}: state={ph.state}, duration={ph.duration}")
    finally:
        traci.close()

if __name__ == "__main__":
    main()
