import jc
import fabric
from invoke.exceptions import *


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
        round_trip_ms_min: float = None,
        round_trip_ms_avg: float = None,
        round_trip_ms_max: float = None,
        round_trip_ms_stddev: float = None,
    ) -> None:
        self.destination_ip = destination_ip
        self.packets_transmitted = packets_transmitted
        self.packets_received = packets_received
        self.round_trip_ms_min = round_trip_ms_min
        self.round_trip_ms_avg = round_trip_ms_avg
        self.round_trip_ms_max = round_trip_ms_max
        self.round_trip_ms_stddev = round_trip_ms_stddev


class DigResult:
    def __init__(self, a: set[str] = set(), cname: str = None) -> None:
        self.a = a
        self.cname = cname


class ShellAgent:
    def __init__(self, host: str, user: str) -> None:
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
        except:
            raise RemoteCommandError(
                f"Failed to parse {cmd_name} stdout: {result.stdout}"
            )

    def ping(self, host: str, count: int) -> PingResult:
        result = self._run_command(f"ping -c{count} -q {host}")
        statistics = PingResult()
        statistics.destination_ip = result["destination_ip"]
        statistics.packets_transmitted = result["packets_transmitted"]
        statistics.packets_received = result["packets_received"]
        statistics.round_trip_ms_min = result["round_trip_ms_min"]
        statistics.round_trip_ms_avg = result["round_trip_ms_avg"]
        statistics.round_trip_ms_max = result["round_trip_ms_max"]
        statistics.round_trip_ms_stddev = result["round_trip_ms_stddev"]
        return statistics

    def dig(self, host: str) -> DigResult:
        dig_result = DigResult()
        for result in self._run_command(f"dig {host} A {host} CNAME"):
            if result["status"] != "NOERROR":
                continue
            for answer in result["answer"]:
                if answer["type"] == "A":
                    dig_result.a.add(answer["data"])
                elif answer["type"] == "CNAME":
                    dig_result.cname = answer["data"]
                else:
                    continue
        return dig_result


if __name__ == "__main__":
    result = ShellAgent("52.87.148.169", "ec2-user").dig("mail.google.com")
    print(result)
