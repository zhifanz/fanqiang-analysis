from nis import match
from .shellagent import DigResult, PingResult
from google.cloud import firestore


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


def _dig_result_to_dict(dr: DigResult) -> dict:
    return {"a": list(dr.a)}


def _ping_result_to_dict(pr: PingResult) -> dict:
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


def host_access_statistics_to_dict(obj: HostAccessStatistics) -> dict:
    result = {
        "host": obj.host,
        "lastUpdated": obj.last_updated,
    }
    if obj.dig_result:
        set_if_true(result, "dig", _dig_result_to_dict(obj.dig_result))
    if obj.central:
        set_if_true(result, "central", _ping_result_to_dict(obj.central))
    if obj.domestic:
        set_if_true(result, "domestic", _ping_result_to_dict(obj.domestic))
    if obj.other_regions:
        result["otherRegions"] = {}
        for k in obj.other_regions:
            result["otherRegions"][k] = _ping_result_to_dict(obj.other_regions[k])
    return result


def set_if_true(obj: dict, key: str, value):
    if value:
        obj[key] = value


class Repository:
    def __init__(self, project: str = None) -> None:
        self.db = firestore.Client(project=project)
        self.collection = self.db.collection("hostaccessstatistics")

    def exists(self, host: str) -> bool:
        matched = self.collection.where("host", "==", host).get()
        return len(matched) > 0

    def save(self, entity: HostAccessStatistics) -> None:
        self.collection.add(host_access_statistics_to_dict(entity))
