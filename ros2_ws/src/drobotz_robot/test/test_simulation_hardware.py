import unittest

from drobotz_robot.nodes.simulation_hardware_node import action_to_velocity


class SimulationCommandMappingTest(unittest.TestCase):
    def test_motion_actions_map_to_car_velocity(self):
        self.assertEqual(action_to_velocity("F", 0.25, 0.25), (0.25, 0.0))
        self.assertEqual(action_to_velocity("B", 0.25, 0.25), (-0.25, 0.0))
        self.assertEqual(action_to_velocity("L", 0.25, 0.25), (0.25, 0.25))
        self.assertEqual(action_to_velocity("R", 0.25, 0.25), (0.25, -0.25))
        self.assertEqual(action_to_velocity("S", 0.25, 0.25), (0.0, 0.0))

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            action_to_velocity("X", 0.25, 0.8)


if __name__ == "__main__":
    unittest.main()
