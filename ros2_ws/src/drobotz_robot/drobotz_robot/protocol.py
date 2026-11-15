import math
import re
from typing import Optional


_COMMAND_SEQUENCE = re.compile(r"^[FBLRS](?:\d{1,5})?(?:,[FBLRS](?:\d{1,5})?)*$")
_AI_COMMAND = re.compile(r"\b([FBLRS])(\d{0,5})\b", re.IGNORECASE)


def normalize_motion_command(command: str, *, require_duration: bool = False) -> Optional[str]:
    """Validate a firmware movement command and bound every timed movement."""
    candidate = command.strip().upper()
    if not candidate or not _COMMAND_SEQUENCE.fullmatch(candidate):
        return None

    normalized = []
    for token in candidate.split(","):
        action, duration_text = token[0], token[1:]
        if require_duration and action != "S" and not duration_text:
            return None
        if duration_text:
            duration = int(duration_text)
            minimum = 300 if action in "LR" else 500 if action in "FB" else 0
            duration = min(max(duration, minimum), 5000)
            token = f"{action}{duration}" if action != "S" else "S"
        normalized.append(token)

    if len(normalized) > 8:
        return None
    if require_duration and normalized[-1] != "S":
        normalized.append("S")
    return ",".join(normalized)


def extract_ai_command(response: str) -> Optional[str]:
    """Extract bounded movement tokens from an AI response."""
    matches = _AI_COMMAND.findall(response)
    if not matches:
        return None

    tokens = []
    for action, duration_text in matches[:7]:
        action = action.upper()
        if action == "S":
            tokens.append("S")
            continue
        duration = int(duration_text) if duration_text else (500 if action in "LR" else 800)
        minimum = 300 if action in "LR" else 500
        tokens.append(f"{action}{min(max(duration, minimum), 5000)}")

    if not tokens or tokens[-1] != "S":
        tokens.append("S")
    return normalize_motion_command(",".join(tokens), require_duration=True)


def front_sector_minimum(
    ranges: list[float],
    angle_min: float,
    angle_increment: float,
    range_min: float,
    range_max: float,
    front_angle_degrees: float = 60.0,
) -> Optional[float]:
    """Return the closest valid reading in a centered forward scan sector."""
    half_angle = front_angle_degrees * 0.5 * 3.141592653589793 / 180.0
    valid = []
    for index, distance in enumerate(ranges):
        angle = angle_min + index * angle_increment
        angle = (angle + 3.141592653589793) % (2 * 3.141592653589793) - 3.141592653589793
        if (
            math.isfinite(angle)
            and math.isfinite(distance)
            and abs(angle) <= half_angle
            and range_min <= distance <= range_max
        ):
            valid.append(distance)
    return min(valid) if valid else None
