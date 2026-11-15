import math
import unittest

from drobotz_robot.protocol import (
    extract_ai_command,
    front_sector_minimum,
    normalize_motion_command,
)
from drobotz_robot.status import is_fresh


class CommandProtocolTest(unittest.TestCase):
    def test_bounds_timed_commands_and_requires_stop_for_ai(self):
        self.assertEqual(normalize_motion_command("F0,L9999,S"), "F500,L5000,S")
        self.assertEqual(
            normalize_motion_command("F10000,L50", require_duration=True),
            "F5000,L300,S",
        )

    def test_rejects_malformed_and_oversized_sequences(self):
        self.assertIsNone(normalize_motion_command("F;rm"))
        self.assertIsNone(normalize_motion_command("F,B,L,R,F,B,L,R,S"))
        self.assertIsNone(normalize_motion_command("F", require_duration=True))

    def test_extracts_only_bounded_motion_commands(self):
        self.assertEqual(
            extract_ai_command("Moving forward: F9000 then turn L100."),
            "F5000,L300,S",
        )
        self.assertIsNone(extract_ai_command("I am ready."))


class ForwardLaserSectorTest(unittest.TestCase):
    def test_uses_only_valid_ranges_in_the_forward_sector(self):
        distances = [4.0, 0.8, 0.3, 0.5, 2.0]
        self.assertAlmostEqual(
            front_sector_minimum(
                distances,
                angle_min=-math.pi / 2,
                angle_increment=math.pi / 4,
                range_min=0.1,
                range_max=10.0,
            ),
            0.3,
        )

    def test_returns_none_when_no_valid_forward_ranges_exist(self):
        self.assertIsNone(
            front_sector_minimum(
                [float("inf"), float("nan"), -1.0, 1.0],
                angle_min=-math.pi,
                angle_increment=math.pi / 2,
                range_min=0.1,
                range_max=5.0,
            )
        )


class DeviceStatusTest(unittest.TestCase):
    def test_absent_or_expired_data_is_disconnected(self):
        self.assertFalse(is_fresh(None, timeout_sec=5.0, current_time=10.0))
        self.assertTrue(is_fresh(7.0, timeout_sec=5.0, current_time=10.0))
        self.assertFalse(is_fresh(4.0, timeout_sec=5.0, current_time=10.0))


if __name__ == "__main__":
    unittest.main()
