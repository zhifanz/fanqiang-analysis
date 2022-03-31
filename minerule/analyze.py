from .shellagent import RemoteCommandError, ShellAgent
from .statistics import HostAccessStatistics, Repository
from google.cloud import bigquery
import time
import logging


class HostsQuery:
    def __init__(
        self,
        dataset_id: str,
        table_id: str,
        data_column: str,
        condition_column: str,
        from_time: float,
        to_time: float,
    ) -> None:
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.data_column = data_column
        self.condition_column = condition_column
        self.from_time = from_time
        self.to_time = to_time


class Proxies:
    def __init__(
        self,
        central_vm: ShellAgent,
        domestic_vm: ShellAgent,
        other_vms: dict[str, ShellAgent] = {},
    ) -> None:
        self.central_vm = central_vm
        self.domestic_vm = domestic_vm
        self.other_vms = other_vms


def find_hosts(query: HostsQuery) -> list[str]:
    query_job = bigquery.Client().query(
        f"select distinct {query.data_column} as host from {query.dataset_id}.{query.table_id} where {query.condition_column} >= ? and {query.condition_column} < ?",
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter(None, "TIMESTAMP", query.from_time),
                bigquery.ScalarQueryParameter(None, "TIMESTAMP", query.to_time),
            ]
        ),
    )
    return [row.host for row in query_job]


def slient_run_shell(cmd_call, *args):
    try:
        return cmd_call(*args)
    except RemoteCommandError as err:
        logging.error(err)
        return None


def analyze_rules(query: HostsQuery, proxies: Proxies, ping_count: int) -> None:
    repository = Repository()
    for host in find_hosts(query):
        if repository.exists(host):
            continue
        statistics = HostAccessStatistics(host, time.time())
        statistics.dig_result = slient_run_shell(proxies.central_vm.dig, host)
        statistics.central = slient_run_shell(proxies.central_vm.ping, host, ping_count)
        statistics.domestic = slient_run_shell(
            proxies.domestic_vm.ping, host, ping_count
        )
        for k in proxies.other_vms:
            r = slient_run_shell(proxies.other_vms[k].ping, host, ping_count)
            if r:
                statistics.other_regions[k] = r
        repository.save(statistics)
