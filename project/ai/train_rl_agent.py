import traci
import numpy as np
from dqn_agent import DQNAgent

EPISODES = 100
STATE_SIZE = 4  # You can adjust this based on your actual state features
ACTION_SIZE = 2  # Example: [keep current phase, switch phase]

# Edge groupings for state monitoring
edges = {
    "north": ["498169188#0", "498169188#1", "498169188#2", "498169188#3"],
    "south": ["24375221#0", "24375221#1", "24375221#2", "24375221#3"],
    "north_2": ["143957229#0", "143957229#1", "143957229#2", "143957229#3", "143957229#4", "143957229#5", "143957229#6", "143957229#7", "143957229#8", "143957229#9"],
    "south_2": ["24375222#1", "24375222#2", "24375222#3", "24375222#4", "24375222#5", "24375222#6", "24375222#7", "24375222#8", "24375222#9"],
    "east": ["343146616#0", "343146616#1", "343146616#2", "343146616#3", "343146616#4", "343146616#5", "343146616#6", "343146616#7"],
    "west": ["1088038754#0", "1088038754#1", "11075217#0", "11075217#1", "11075217#2", "11075217#3"],
    "east_2": ["24449129#9", "24338292#1", "24338292#3", "24338292#4", "24338292#5", "24338292#6", "24338292#7"],
    "west_2": ["144567412#0", "144567412#1", "144567412#2", "144567412#3", "144567412#5", "144567412#6", "144567412#7"]
}

agent = DQNAgent(STATE_SIZE, ACTION_SIZE)

for e in range(EPISODES):
    traci.start(["sumo", "-c", "simulation/config.sumocfg"])
    total_reward = 0
    done = False
    step = 0

    def get_state():
        state = []
        for direction in edges:
            vehicle_count = 0
            for edge in edges[direction]:
                val = traci.edge.getLastStepVehicleNumber(edge)
                if isinstance(val, tuple):
                    val = val[0]
                vehicle_count += float(val)
            state.append(vehicle_count)
        return np.array([state[:STATE_SIZE]])

    state = get_state()

    min_expected = traci.simulation.getMinExpectedNumber()
    if isinstance(min_expected, tuple):
        min_expected = min_expected[0]
    while min_expected > 0:
        action = agent.act(state)

        # Example signal logic: simple 2-phase toggle
        if action == 1:
            current_phase = traci.trafficlight.getPhase("junction_id")
            if isinstance(current_phase, tuple):
                current_phase = current_phase[0]
            traci.trafficlight.setPhase("junction_id", (current_phase + 1) % 2)

        traci.simulationStep()

        next_state = get_state()
        reward = -sum(next_state[0])  # Negative of total vehicle count as penalty

        done = step > 1000
        agent.remember(state, action, reward, next_state, done)

        state = next_state
        step += 1
        total_reward += reward

        if done:
            print(f"Episode {e+1}/{EPISODES}, Reward: {total_reward}, Epsilon: {agent.epsilon:.2f}")
            break

    agent.replay()
    agent.save("checkpoints/dqn_weights.h5")
    traci.close()
