import pprint
from fra.shellagent import DigResult, PingResult
from fra.statistics import HostAccessStatistics, Repository
import time


def test_repository():
    repository = Repository("mongodb://localhost:27017")
    assert not repository.exists("unknow_host")
    data = HostAccessStatistics(
        "google.com",
        time.time(),
        DigResult({"8.8.8.8", "8.8.8.9"}, "google.l.com"),
        PingResult("8.8.8.8", 5, 5, 6.5, 7.2, 10.5, 4),
    )
    repository.save(data)
    assert repository.exists("google.com")
    results = [d for d in repository.collection.find()]
    assert len(results) == 1
