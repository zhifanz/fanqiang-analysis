import time
import datetime


class TimeWindow:
    def __init__(self, from_time: float, to_time: float) -> None:
        self.from_time = from_time
        self.to_time = to_time

    def in_seconds(self) -> int:
        return int(self.to_time - self.from_time)

    @staticmethod
    def past_days(days_delta: int):
        current_time = time.time()
        return TimeWindow(
            current_time - datetime.timedelta(days=days_delta).total_seconds(),
            current_time,
        )
