import time
from typing import Optional


def is_fresh(
    last_received_at: Optional[float],
    timeout_sec: float,
    current_time: Optional[float] = None,
) -> bool:
    if last_received_at is None:
        return False
    now = time.monotonic() if current_time is None else current_time
    age = now - last_received_at
    return 0.0 <= age <= timeout_sec
