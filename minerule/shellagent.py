from decimal import Decimal
import jc
import fabric
from invoke.exceptions import Failure, ThreadException
from paramiko import PKey


class RemoteCommandError(RuntimeError):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(*args)
        self.message = message


class PingResult:
    def __init__(
        self,
        destination_ip: str = None,
        packets_transmitted: int = None,
        packets_received: int = None,
        round_trip_ms_min: Decimal = None,
        round_trip_ms_avg: Decimal = None,
        round_trip_ms_max: Decimal = None,
        round_trip_ms_stddev: Decimal = None,
    ) -> None:
        self.destination_ip = destination_ip
        self.packets_transmitted = packets_transmitted
        self.packets_received = packets_received
        self.round_trip_ms_min = round_trip_ms_min
        self.round_trip_ms_avg = round_trip_ms_avg
        self.round_trip_ms_max = round_trip_ms_max
        self.round_trip_ms_stddev = round_trip_ms_stddev


class ShellAgent:
    def __init__(self, host: str, user: str, pkey: PKey = None) -> None:
        if pkey:
            self.connection = fabric.Connection(
                host,
                user=user,
                connect_kwargs={"pkey": pkey},
            )
        else:
            self.connection = fabric.Connection(host, user=user)

    def _run_command(self, command: str):
        cmd_name = command.split(" ")[0]
        try:
            result = self.connection.run(command, hide=True)
        except (Failure, ThreadException) as err:
            raise RemoteCommandError(f"Failed to run command: {cmd_name}") from err
        if not result.stdout:
            raise RemoteCommandError(f"Output of command {cmd_name} is empty")
        try:
            return jc.parse(cmd_name, result.stdout)
        except BaseException:
            raise RemoteCommandError(
                f"Failed to parse {cmd_name} stdout: {result.stdout}"
            )

    def ping(self, host: str, count: int) -> PingResult:
        result = self._run_command(f"ping -c{count} -q {host}")
        if result.keys() >= {
            "destination_ip",
            "packets_transmitted",
            "packets_received",
        }:
            statistics = PingResult()
            statistics.destination_ip = result["destination_ip"]
            statistics.packets_transmitted = result["packets_transmitted"]
            statistics.packets_received = result["packets_received"]
            if "round_trip_ms_min" in result:
                statistics.round_trip_ms_min = Decimal.from_float(
                    result["round_trip_ms_min"]
                )
            if "round_trip_ms_avg" in result:
                statistics.round_trip_ms_avg = Decimal.from_float(
                    result["round_trip_ms_avg"]
                )
            if "round_trip_ms_max" in result:
                statistics.round_trip_ms_max = Decimal.from_float(
                    result["round_trip_ms_max"]
                )
            if "round_trip_ms_stddev" in result:
                statistics.round_trip_ms_stddev = Decimal.from_float(
                    result["round_trip_ms_stddev"]
                )
            return statistics
        else:
            raise RemoteCommandError("Missing key attributes from ping result")
