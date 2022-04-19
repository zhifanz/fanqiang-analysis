from .shellagent import PingResult
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal


class HostStatistic:
    def __init__(
        self,
        host: str,
        last_updated: Decimal,
        is_ip_address: bool,
        central: PingResult = None,
        domestic: PingResult = None,
        other_continents: dict[str, PingResult] = {},
    ) -> None:
        self.host = host
        self.last_updated = last_updated
        self.is_ip_address = is_ip_address
        self.central = central
        self.domestic = domestic
        self.other_continents = other_continents

    def ip_addresses(self) -> set[str]:
        if self.is_ip_address:
            return {self.host}
        result = set()
        if self.central:
            result.add(self.central.destination_ip)
        if self.domestic:
            result.add(self.domestic.destination_ip)
        result.update([e.destination_ip for e in self.other_continents.values()])
        return result


class HostStatisticRepository:
    def __init__(self, table="hoststatistics") -> None:
        self.table = (
            boto3.resource("dynamodb").Table(table) if type(table) == str else table
        )

    @staticmethod
    def schema() -> dict:
        return {
            "KeySchema": [{"AttributeName": "host", "KeyType": "HASH"}],
            "AttributeDefinitions": [{"AttributeName": "host", "AttributeType": "S"}],
        }

    def exists(self, host: str) -> bool:
        result = self.table.query(
            Select="COUNT", KeyConditionExpression=Key("host").eq(host)
        )
        return result["Count"] > 0

    def ip_exists(self, host: str) -> bool:
        result = self.table.scan(
            Select="COUNT", FilterExpression=Attr("ipAddresses").contains(host)
        )
        return result["Count"] > 0

    @classmethod
    def _dict_to_ping_result(cls, obj: dict) -> PingResult:
        result = PingResult(
            obj["destinationIp"], obj["packetsTransmitted"], obj["packetsReceived"]
        )
        if "roundTripMsMin" in obj:
            result.round_trip_ms_min = obj["roundTripMsMin"]
        if "roundTripMsMax" in obj:
            result.round_trip_ms_max = obj["roundTripMsMax"]
        if "roundTripMsAvg" in obj:
            result.round_trip_ms_avg = obj["roundTripMsAvg"]
        if "roundTripMsStddev" in obj:
            result.round_trip_ms_stddev = obj["roundTripMsStddev"]
        return result

    @classmethod
    def _dict_to_host_statistic(cls, obj: dict) -> HostStatistic:
        result = HostStatistic(obj["host"], obj["lastUpdated"], obj["isIpAddress"])
        if "central" in obj:
            result.central = cls._dict_to_ping_result(obj["central"])
        if "domestic" in obj:
            result.domestic = cls._dict_to_ping_result(obj["domestic"])
        if "otherContinents" in obj:
            result.other_continents = {}
            for continent in obj["otherContinents"]:
                result.other_continents[continent] = cls._dict_to_ping_result(
                    obj["otherContinents"][continent]
                )
        return result

    def find(self, host: str) -> HostStatistic:
        result = self.table.get_item(Key={"host": host})
        return (
            self._dict_to_host_statistic(result["Item"]) if "Item" in result else None
        )

    def find_by_ip(self, host: str) -> list[HostStatistic]:
        result = self.table.scan(
            Select="ALL_ATTRIBUTES", FilterExpression=Attr("ipAddresses").contains(host)
        )
        return [self._dict_to_host_statistic(doc) for doc in result["Items"]]

    @classmethod
    def _ping_result_to_dict(cls, pr: PingResult) -> dict:
        result = {
            "destinationIp": pr.destination_ip,
            "packetsTransmitted": pr.packets_transmitted,
            "packetsReceived": pr.packets_received,
        }
        if pr.round_trip_ms_min:
            result["roundTripMsMin"] = pr.round_trip_ms_min
        if pr.round_trip_ms_max:
            result["roundTripMsMax"] = pr.round_trip_ms_max
        if pr.round_trip_ms_avg:
            result["roundTripMsAvg"] = pr.round_trip_ms_avg
        if pr.round_trip_ms_stddev:
            result["roundTripMsStddev"] = pr.round_trip_ms_stddev
        return result

    @classmethod
    def _host_statistic_to_dict(cls, obj: HostStatistic) -> dict:
        result = {
            "host": obj.host,
            "lastUpdated": obj.last_updated,
            "isIpAddress": obj.is_ip_address,
        }
        if obj.central:
            result["central"] = cls._ping_result_to_dict(obj.central)
        if obj.domestic:
            result["domestic"] = cls._ping_result_to_dict(obj.domestic)
        if obj.other_continents:
            result["otherContinents"] = {}
            for continent in obj.other_continents:
                result["otherContinents"][continent] = cls._ping_result_to_dict(
                    obj.other_continents[continent]
                )
        if not obj.is_ip_address and obj.ip_addresses():
            result["ipAddresses"] = obj.ip_addresses()
        return result

    def save(self, entity: HostStatistic) -> None:
        self.table.put_item(Item=self._host_statistic_to_dict(entity))
