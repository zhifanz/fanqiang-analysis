import pathlib
import pytest
from google.cloud.bigquery import (
    Client,
    LoadJobConfig,
    SourceFormat,
)
from google.cloud.bigquery import Table
from minerule.socketevents import SocketEventRepository
from minerule.utiltypes import TimeWindow


@pytest.fixture(scope="module")
def repo():
    client = Client()
    ds = client.create_dataset("foo")
    tb = client.create_table(
        Table(ds.table(SocketEventRepository.TABLE_NAME), SocketEventRepository.SCHEMA)
    )
    job_conf = LoadJobConfig(
        source_format=SourceFormat.CSV,
        skip_leading_rows=1,
        schema=SocketEventRepository.SCHEMA,
    )
    with open(pathlib.Path(__file__).parent / "socketevents.csv", "rb") as fp:
        client.load_table_from_file(fp, tb, job_config=job_conf).result()
    yield SocketEventRepository(client, "foo")
    client.delete_dataset(ds, True, not_found_ok=True)
    client.close()


class TestSocketEventRepository:
    def test_aggregate_on_hosts(self, repo: SocketEventRepository):
        hosts = repo.aggregate_on_hosts(TimeWindow(946684801, 946684833))
        assert {"foo1", "bar1", "foo2"} == hosts

    def test_find_correlated_hosts(self, repo: SocketEventRepository):
        assert repo.find_correlated_hosts("foo1", 1) == {"bar1"}
        assert repo.find_correlated_hosts("bar1", 1) == {"foo1"}
        assert not repo.find_correlated_hosts("foo2", 1)
