import ipaddress
import time
import logging
from typing import Iterable
from tldextract import TLDExtract

from .socketevents import SocketEventRepository
from .hoststatistics import HostStatistic, HostStatisticRepository
from .shellagent import PingResult, RemoteCommandError, ShellAgent
from .utiltypes import TimeWindow


RouteRules = dict[str, list[str]]
_domain_extrac_func = TLDExtract()


def silent_run_shell(cmd_call, *args):
    try:
        return cmd_call(*args)
    except RemoteCommandError as err:
        logging.error(err)
        return None


def is_ip_address(address: str) -> bool:
    try:
        ipaddress.ip_address(address)
        return True
    except ValueError:
        return False


def is_same_top_domain(d1: str, d2: str) -> bool:
    return _domain_extrac_func(d1).domain == _domain_extrac_func(d2).domain


class HostStatisticsRefreshRunner:
    def __init__(
        self,
        repository: HostStatisticRepository,
        central_vm: ShellAgent,
        domestic_vm: ShellAgent,
        **other_vms: ShellAgent
    ) -> None:
        self.repository = repository
        self.central_vm = central_vm
        self.domestic_vm = domestic_vm
        self.other_vms = other_vms

    def refresh(self, host: str, ping_count: int) -> None:
        if self.repository.exists(host) or self.repository.ip_exists(host):
            return
        result = HostStatistic(host, time.time(), is_ip_address(host))
        result.central = silent_run_shell(self.central_vm.ping, host, ping_count)
        result.domestic = silent_run_shell(self.domestic_vm.ping, host, ping_count)
        for continent in self.other_vms:
            r = silent_run_shell(self.other_vms[continent].ping, host, ping_count)
            if r:
                result.other_continents[continent] = r
        self.repository.save(result)

    def refresh_all(self, hosts: Iterable[str], ping_count: int) -> None:
        for host in hosts:
            self.refresh(host, ping_count)


class RouteEvaluator:
    @staticmethod
    def add_to_scores(scores, key: str, ping_result: PingResult) -> None:
        if not ping_result or ping_result.packets_received == 0:
            scores[key] = -1.0
        if scores[key] < 0:
            return
        scores[key] += ping_result.packets_received / ping_result.packets_transmitted

    @staticmethod
    def init_score(statistics: list[HostStatistic]):
        scores = {"central": 0.0, "domestic": 0.0, "others": {}}
        for s in statistics:
            for c in s.other_continents:
                if c not in scores["others"]:
                    scores["others"][c] = 0.0
        return scores

    @staticmethod
    def determine_route_continent(statistics: list[HostStatistic]) -> str:
        scores = RouteEvaluator.init_score(statistics)

        for statistic in statistics:
            RouteEvaluator.add_to_scores(scores, "central", statistic.central)
            RouteEvaluator.add_to_scores(scores, "domestic", statistic.domestic)
            for continent in scores["others"]:
                RouteEvaluator.add_to_scores(
                    scores["others"],
                    continent,
                    statistic.other_continents[continent]
                    if continent in statistic.other_continents
                    else None,
                )
        optimal_continent = "central"
        max_score = scores["central"]
        if scores["domestic"] > max_score:
            max_score = scores["domestic"]
            optimal_continent = "domestic"
        for continent in scores["others"]:
            if scores["others"][continent] > max_score:
                max_score = scores["others"][continent]
                optimal_continent = continent
        return optimal_continent


class RouteRuleAnalyzer:
    def __init__(
        self,
        socket_event_repository: SocketEventRepository,
        host_statistic_repository: HostStatisticRepository,
        refresh_runner: HostStatisticsRefreshRunner,
    ) -> None:
        self.socket_event_repository = socket_event_repository
        self.host_statistic_repository = host_statistic_repository
        self.refresh_runner = refresh_runner

    @staticmethod
    def create_instance(
        dataset_id: str,
        central_vm: ShellAgent,
        domestic_vm: ShellAgent,
        **other_vms: ShellAgent
    ):
        socket_event_repository = SocketEventRepository(dataset_id)
        host_statistic_repository = HostStatisticRepository()
        refresh_runner = HostStatisticsRefreshRunner(
            host_statistic_repository, central_vm, domestic_vm, **other_vms
        )
        return RouteRuleAnalyzer(
            socket_event_repository, host_statistic_repository, refresh_runner
        )

    def _init_rules(self) -> RouteRules:
        route_rules = {"domestic": []}
        for continent in self.other_vms:
            route_rules[continent] = []
        return route_rules

    def find_related_hosts(
        self, seed: HostStatistic, hosts: set[str]
    ) -> list[HostStatistic]:
        result = [seed]
        i = 0
        while i < len(result):
            ips = hosts & (result[i].ip_addresses() | self.socket_event_repository.find_correlated_hosts(result[i].host))  # fmt: skip
            for ip in ips:
                result.append(self.host_statistic_repository.find(ip))
            hosts -= ips
            if result[i].is_ip_address:
                for s in self.host_statistic_repository.find_by_ip(result[i].host):
                    if s.host not in hosts:
                        continue
                    result.append(s)
                    hosts.remove(s.host)
            else:
                sib_hosts = {h for h in hosts if is_same_top_domain(h, result[i].host)}
                result.extend(
                    [self.host_statistic_repository.find(h) for h in sib_hosts]
                )
                hosts -= sib_hosts
            i += 1
        return result

    def calculate_rules(self, days_delta: int, ping_count: int) -> RouteRules:
        route_rules: RouteRules = self._init_rules()
        snapshot = TimeWindow.past_days(days_delta)
        hosts = self.socket_event_repository.aggregate_on_hosts(snapshot)
        self.refresh_runner.refresh_all(hosts, ping_count)
        while hosts:
            seed = self.host_statistic_repository.find(hosts.pop())
            statistics = self.find_related_hosts(seed, hosts)
            continent = RouteEvaluator.determine_route_continent(statistics)
            if continent in route_rules:
                route_rules[continent].extend([e.host for e in statistics])
        return route_rules
