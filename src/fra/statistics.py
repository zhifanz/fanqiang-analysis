from .shellagent import DigResult, PingResult
import pymongo
from pymongo.collection import Collection
import dns


def _dig_result_to_dict(dr: DigResult):
    result = {"a": list(dr.a)}
    if dr.cname:
        result["cname"] = dr.cname
    return result


def _ping_result_to_dict(pr: PingResult):
    result = {}
    if pr.destination_ip:
        result["destinationIp"] = pr.destination_ip
    if pr.packets_transmitted:
        result["packetsTransmitted"] = pr.packets_transmitted
    if pr.packets_received:
        result["packetsReceived"] = pr.packets_received
    if pr.round_trip_ms_min:
        result["roundTripMsMin"] = pr.round_trip_ms_min
    if pr.round_trip_ms_max:
        result["roundTripMsMax"] = pr.round_trip_ms_max
    if pr.round_trip_ms_avg:
        result["roundTripMsAvg"] = pr.round_trip_ms_avg
    if pr.round_trip_ms_stddev:
        result["roundTripMsStddev"] = pr.round_trip_ms_stddev
    return result


class HostAccessStatistics:
    def __init__(
        self,
        host: str,
        last_updated: float,
        dig_result: DigResult = None,
        central: PingResult = None,
        domestic: PingResult = None,
        other_regions: dict[str, PingResult] = {},
    ) -> None:
        self.host = host
        self.last_updated = last_updated
        self.dig_result = dig_result
        self.central = central
        self.domestic = domestic
        self.other_regions = other_regions

    def to_dict(self):
        result = {
            "host": self.host,
            "lastUpdated": self.last_updated,
        }
        if self.dig_result:
            result["dig"] = _dig_result_to_dict(self.dig_result)
        if self.central:
            result["central"] = _ping_result_to_dict(self.central)
        if self.domestic:
            result["domestic"] = _ping_result_to_dict(self.domestic)
        if self.other_regions:
            result["otherRegions"] = {}
            for k in self.other_regions:
                result["otherRegions"][k] = _ping_result_to_dict(self.other_regions[k])
        return result


class Repository:
    def __init__(self, uri: str) -> None:
        self.client = pymongo.MongoClient(uri)
        self.collection: Collection = self.client.fanqiang.hostAccessStatistics

    def exists(self, host: str) -> bool:
        return bool(self.collection.find_one(filter={"host": host}))

    def save(self, entity: HostAccessStatistics) -> None:
        self.collection.insert_one(entity.to_dict())
