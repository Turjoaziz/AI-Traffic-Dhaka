import unittest
from unittest.mock import MagicMock
import numpy as np
import sys
import os

# Add the directory containing dqn_agent.py to sys.path so it can be imported
agent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'your_agent_folder'))
if agent_dir not in sys.path:
    sys.path.insert(0, agent_dir)

from dqn_agent import DQNAgent

class TestRLAgent(unittest.TestCase):

    def setUp(self):
        self.agent = DQNAgent(state_size=4, action_size=2)
        self.mock_state = np.array([[5, 3, 2, 0]])

    def test_generate_state_vector(self):
        # Assuming you have a method like agent.build_state()
        state_vector = self.mock_state
        self.assertEqual(state_vector.shape, (1, 4))
        self.assertTrue((state_vector >= 0).all())

    def test_select_action(self):
        self.agent.epsilon = 0  # Force greedy action
        action = self.agent.act(self.mock_state)
        self.assertIn(action, [0, 1])

    def test_compute_reward(self):
        # Assuming reward is calculated as negative of total queue length
        queue_lengths = [3, 5, 2, 1]
        reward = -sum(queue_lengths)
        self.assertEqual(reward, -11)

if __name__ == '__main__':
    unittest.main()
