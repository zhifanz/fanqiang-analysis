import time
from decimal import Decimal
import pytest
from minerule.shellagent import PingResult
from minerule.hoststatistics import HostStatistic, HostStatisticRepository
import boto3
from boto3.dynamodb.conditions import Key, Attr


@pytest.fixture
def repo() -> HostStatisticRepository:
    t = boto3.resource("dynamodb").create_table(
        TableName="hoststatistics",
        BillingMode="PAY_PER_REQUEST",
        **HostStatisticRepository.schema(),
    )
    t.wait_until_exists()
    repo = HostStatisticRepository(t)
    yield repo
    repo.table.delete()
    repo.table.wait_until_not_exists()


@pytest.fixture
def foo() -> HostStatistic:
    return HostStatistic("foo.com", Decimal(1000000), False)


def test_dynamodb_query(repo):
    repo.table.put_item(Item={"host": "baidu.com"})
    result = repo.table.query(
        Select="COUNT", KeyConditionExpression=Key("host").eq("baidu.com")
    )
    assert result["Count"] == 1
    result = repo.table.query(
        Select="COUNT", KeyConditionExpression=Key("host").eq("google.com")
    )
    assert result["Count"] == 0


def test_dynamodb_scan(repo):
    repo.table.put_item(Item={"host": "baidu.com", "ipAddresses": ["0.0.0.0"]})
    result = repo.table.scan(
        Select="COUNT", FilterExpression=Attr("ipAddresses").contains("0.0.0.0")
    )
    assert result["Count"] == 1
    result = repo.table.scan(
        Select="COUNT", FilterExpression=Attr("ipAddresses").contains("1.1.1.1")
    )
    assert result["Count"] == 0


def test_dynamodb_get_item(repo):
    repo.table.put_item(Item={"host": "baidu.com", "attr1": Decimal("7.6")})
    result = repo.table.get_item(Key={"host": "baidu.com"})
    doc = result["Item"]
    assert doc["host"] == "baidu.com"
    assert doc["attr1"] == Decimal("7.6")
    result = repo.table.get_item(Key={"host": "notexists.com"})
    assert "Item" not in result


class TestHostStatisticRepository:
    def test_save(self, repo: HostStatisticRepository):
        repo.save(
            HostStatistic(
                "baidu.com",
                Decimal.from_float(time.time()),
                False,
                central=PingResult("8.8.8.8"),
            )
        )
        assert repo.exists("baidu.com") is True
        assert repo.exists("google.com") is False
        assert repo.ip_exists("8.8.8.8") is True
        assert repo.ip_exists("7.7.7.7") is False

    def test_exists(self, repo: HostStatisticRepository, foo: HostStatistic):
        repo.save(foo)
        assert repo.exists("foo.com")
        assert not repo.exists("bar.com")

    def test_ip_exists(self, repo: HostStatisticRepository, foo: HostStatistic):
        assert not repo.ip_exists("0.0.0.0")
        foo.central = PingResult("0.0.0.0", 0, 0)
        foo.domestic = PingResult("1.1.1.1", 0, 0)
        foo.other_continents = {"NA": PingResult("2.2.2.2", 0, 0)}
        repo.save(foo)
        assert repo.ip_exists("0.0.0.0")
        assert repo.ip_exists("1.1.1.1")
        assert repo.ip_exists("2.2.2.2")
        assert not repo.ip_exists("3.3.3.3")

    def test_find(self, repo: HostStatisticRepository, foo: HostStatistic):
        foo.central = PingResult("0.0.0.0", 2, 1)
        foo.domestic = PingResult("1.1.1.1", 10, 5)
        foo.other_continents = {"NA": PingResult("2.2.2.2", 7, 3)}
        repo.save(foo)
        v = repo.find("foo.com")
        assert v.host == "foo.com"
        assert v.last_updated == 1000000
        assert v.is_ip_address is False
        assert v.central.destination_ip == "0.0.0.0"
        assert v.central.packets_transmitted == 2
        assert v.central.packets_received == 1
        assert v.domestic.destination_ip == "1.1.1.1"
        assert v.domestic.packets_transmitted == 10
        assert v.domestic.packets_received == 5
        assert v.other_continents["NA"].destination_ip == "2.2.2.2"
        assert v.other_continents["NA"].packets_transmitted == 7
        assert v.other_continents["NA"].packets_received == 3

    def test_find_by_ip(self, repo: HostStatisticRepository, foo: HostStatistic):
        foo.central = PingResult("0.0.0.0", 2, 1)
        foo.domestic = PingResult("1.1.1.1", 10, 5)
        foo.other_continents = {"NA": PingResult("2.2.2.2", 7, 3)}
        repo.save(foo)
        found = repo.find_by_ip("1.1.1.1")
        assert len(found) == 1
        v = found[0]
        assert v.host == "foo.com"
        assert v.last_updated == 1000000
        assert v.is_ip_address is False
        assert v.central.destination_ip == "0.0.0.0"
        assert v.central.packets_transmitted == 2
        assert v.central.packets_received == 1
        assert v.domestic.destination_ip == "1.1.1.1"
        assert v.domestic.packets_transmitted == 10
        assert v.domestic.packets_received == 5
        assert v.other_continents["NA"].destination_ip == "2.2.2.2"
        assert v.other_continents["NA"].packets_transmitted == 7
        assert v.other_continents["NA"].packets_received == 3
        assert not repo.find_by_ip("3.3.3.3")


class TestHostStatistic:
    def test_no_ip_addresses(self, foo: HostStatistic):
        assert not foo.ip_addresses()

    def test_central_ip_addresses(self, foo: HostStatistic):
        foo.central = PingResult("0.0.0.0")
        s = foo.ip_addresses()
        assert type(s) == set
        assert s == {"0.0.0.0"}

    def test_domestic_ip_addresses(self, foo: HostStatistic):
        foo.domestic = PingResult("0.0.0.0")
        s = foo.ip_addresses()
        assert type(s) == set
        assert s == {"0.0.0.0"}

    def test_other_continents_ip_addresses(self, foo: HostStatistic):
        foo.other_continents = {"NA": PingResult("0.0.0.0")}
        s = foo.ip_addresses()
        assert type(s) == set
        assert s == {"0.0.0.0"}

    def test_removce_duplicate_ip_addresses(self, foo: HostStatistic):
        foo.central = PingResult("0.0.0.0")
        foo.domestic = PingResult("0.0.0.0")
        foo.other_continents = {
            "C1": PingResult("1.1.1.1"),
            "C2": PingResult("1.1.1.1"),
        }
        s = foo.ip_addresses()
        assert type(s) == set
        assert s == {"0.0.0.0", "1.1.1.1"}
