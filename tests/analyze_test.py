import decimal
import pytest
from minerule.analyze import (
    RouteEvaluator,
    HostStatisticsRefreshRunner,
    RouteRuleAnalyzer,
    is_ip_address,
    is_same_top_domain,
)
from unittest.mock import MagicMock
from minerule.hoststatistics import HostStatistic, HostStatisticRepository
from minerule.shellagent import PingResult, RemoteCommandError, ShellAgent
from minerule.socketevents import SocketEventRepository


def test_is_ip_address():
    assert is_ip_address("192.168.1.1") is True
    assert is_ip_address("84.23.187.3") is True
    assert is_ip_address("baidu.com") is False
    assert is_ip_address("300.98.2.14") is False


def test_is_same_top_domain():
    assert is_same_top_domain("api.baidu.com", "www.baidu.com")
    assert is_same_top_domain("baidu.com", "www.baidu.com")
    assert not is_same_top_domain("google.com", "baidu.com")


class TestHostStatisticsRefreshRunner:
    @pytest.fixture
    def setup(self):
        return MagicMock(), MagicMock(), MagicMock()

    def test_refresh_host_already_exists(
        self, setup: tuple[HostStatisticRepository, MagicMock, MagicMock]
    ):
        (repo, central_vm, domestic_vm) = setup
        repo.exists = MagicMock(return_value=True)
        repo.ip_exists = MagicMock(return_value=False)
        HostStatisticsRefreshRunner(repo, central_vm, domestic_vm).refresh("h1", 10)
        central_vm.assert_not_called()
        domestic_vm.assert_not_called()

    def test_refresh_ip_already_exists(
        self, setup: tuple[HostStatisticRepository, MagicMock, MagicMock]
    ):
        (repo, central_vm, domestic_vm) = setup
        repo.exists = MagicMock(return_value=False)
        repo.ip_exists = MagicMock(return_value=True)
        HostStatisticsRefreshRunner(repo, central_vm, domestic_vm).refresh("h1", 10)
        central_vm.assert_not_called()
        domestic_vm.assert_not_called()

    @pytest.fixture
    def other_vm(self):
        return MagicMock()

    def test_refresh(
        self,
        setup: tuple[HostStatisticRepository, ShellAgent, ShellAgent],
        other_vm: ShellAgent,
    ):
        (repo, central_vm, domestic_vm) = setup
        repo.exists = MagicMock(return_value=False)
        repo.ip_exists = MagicMock(return_value=False)
        central_vm.ping = MagicMock(return_value=PingResult("1.1.1.1", 10, 10))
        domestic_vm.ping = MagicMock(side_effect=RemoteCommandError("Call error"))
        other_vm.ping = MagicMock(return_value=PingResult("1.1.1.1", 10, 10))
        runner = HostStatisticsRefreshRunner(repo, central_vm, domestic_vm, ap=other_vm)
        runner.refresh("baidu.com", 10)
        repo.save.assert_called_once()


class TestRouteEvaluator:
    @classmethod
    def statistic(cls, **kw):
        return HostStatistic("foo", decimal.Decimal("16000000"), False, **kw)

    @classmethod
    def ping_result(cls, c1, c2):
        return PingResult("0.0.0.0", c1, c2)

    def test_determine_route_continent_single(self):
        f = RouteEvaluator.determine_route_continent
        assert f([self.statistic(central=self.ping_result(10, 10))]) == "central"
        assert f([self.statistic(domestic=self.ping_result(10, 10))]) == "domestic"
        assert f([self.statistic(other_continents={'ap': PingResult('a', 10, 10)})]) == "ap"  # fmt: skip

    def test_determine_route_continent_compare(self):
        s = self.statistic(
            central=self.ping_result(10, 8), domestic=self.ping_result(10, 10)
        )
        assert RouteEvaluator.determine_route_continent([s]) == "domestic"

    def test_determine_route_continent_multiple_simple(self):
        s1 = self.statistic(domestic=self.ping_result(10, 10))
        s2 = self.statistic(domestic=self.ping_result(10, 8))
        assert RouteEvaluator.determine_route_continent([s1, s2]) == "domestic"
        s1 = self.statistic(other_continents={"ap": self.ping_result(10, 8)})
        s2 = self.statistic(other_continents={"ap": self.ping_result(10, 7)})
        assert RouteEvaluator.determine_route_continent([s1, s2]) == "ap"

    def test_determine_route_continent_compare_central_domestic(self):
        s1 = self.statistic(
            central=self.ping_result(10, 8), domestic=self.ping_result(10, 10)
        )
        s2 = self.statistic(
            central=self.ping_result(10, 9), domestic=self.ping_result(10, 8)
        )
        assert RouteEvaluator.determine_route_continent([s1, s2]) == "domestic"

    def test_determine_route_continent_compare_central_others(self):
        s1 = self.statistic(
            central=self.ping_result(10, 8),
            other_continents={"ap": self.ping_result(10, 10)},
        )
        s2 = self.statistic(
            central=self.ping_result(10, 9),
            other_continents={"ap": self.ping_result(10, 8)},
        )
        assert RouteEvaluator.determine_route_continent([s1, s2]) == "ap"

    def test_determine_route_continent_not_compatible(self):
        s1 = self.statistic(domestic=self.ping_result(10, 8))
        s2 = self.statistic(
            other_continents={"ap": self.ping_result(10, 8)},
        )
        assert RouteEvaluator.determine_route_continent([s1, s2]) == "central"

    def test_determine_route_continent_less_optimal_win(self):
        s1 = self.statistic(domestic=self.ping_result(10, 1))
        s2 = self.statistic(
            domestic=self.ping_result(10, 1),
            other_continents={"ap": self.ping_result(10, 10)},
        )
        assert RouteEvaluator.determine_route_continent([s1, s2]) == "domestic"


class TestRouteRuleAnalyzer:
    @pytest.fixture
    def setup(self):
        r1 = MagicMock()
        r2 = MagicMock()
        return r1, r2, RouteRuleAnalyzer(r1, r2, None)

    def statistic(self, host: str, is_ip: bool) -> HostStatistic:
        return HostStatistic(host, decimal.Decimal(), is_ip)

    def test_find_related_hosts_simple(
        self,
        setup: tuple[SocketEventRepository, HostStatisticRepository, RouteRuleAnalyzer],
    ):
        (socket_event_repository, host_statistic_repository, analyzer) = setup
        s = self.statistic("baidu.com", False)
        assert analyzer.find_related_hosts(s, set()) == [s]
        assert analyzer.find_related_hosts(s, {"google.com"}) == [s]

    def test_find_related_hosts_domain(
        self,
        setup: tuple[SocketEventRepository, HostStatisticRepository, RouteRuleAnalyzer],
    ):
        (socket_event_repository, host_statistic_repository, analyzer) = setup
        socket_event_repository.find_correlated_hosts.return_value = set()
        host_statistic_repository.find.return_value = self.statistic(
            "subdomain.baidu.com", False
        )
        s = self.statistic("api.baidu.com", False)
        result = analyzer.find_related_hosts(s, {"subdomain.baidu.com"})
        assert len(result) == 2
        assert result[0].host == "api.baidu.com"
        assert result[1].host == "subdomain.baidu.com"

    def test_find_related_hosts_by_ip(
        self,
        setup: tuple[SocketEventRepository, HostStatisticRepository, RouteRuleAnalyzer],
    ):
        (socket_event_repository, host_statistic_repository, analyzer) = setup
        socket_event_repository.find_correlated_hosts.return_value = set()
        host_statistic_repository.find_by_ip.return_value = [
            self.statistic("baidu.com", False),
            self.statistic("google.com", False),
        ]
        s = self.statistic("8.8.8.8", True)
        result = analyzer.find_related_hosts(s, {"baidu.com", "others.com"})
        assert len(result) == 2
        assert result[0].host == "8.8.8.8"
        assert result[1].host == "baidu.com"

    def test_find_related_hosts_correlated(
        self,
        setup: tuple[SocketEventRepository, HostStatisticRepository, RouteRuleAnalyzer],
    ):
        (socket_event_repository, host_statistic_repository, analyzer) = setup
        socket_event_repository.find_correlated_hosts.return_value = {
            "api.bing.com",
            "about.bing.com",
        }
        host_statistic_repository.find.side_effect = [
            self.statistic("api.bing.com", False),
            self.statistic("about.bing.com", False),
        ]
        s = self.statistic("baidu.com", False)
        result = analyzer.find_related_hosts(s, {"api.bing.com", "others.com"})
        assert len(result) == 2
        assert result[0].host == "baidu.com"
        assert result[1].host == "api.bing.com"

    def test_find_related_hosts_cascading(
        self,
        setup: tuple[SocketEventRepository, HostStatisticRepository, RouteRuleAnalyzer],
    ):
        (socket_event_repository, host_statistic_repository, analyzer) = setup
        socket_event_repository.find_correlated_hosts.return_value = set()
        host_statistic_repository.find_by_ip.side_effect = [
            [self.statistic("1.1.1.1", True)],
            [self.statistic("2.2.2.2", True)],
            [],
        ]
        s = self.statistic("0.0.0.0", True)
        result = analyzer.find_related_hosts(s, {"1.1.1.1", "2.2.2.2", "3.3.3.3"})
        assert len(result) == 3
        assert result[0].host == "0.0.0.0"
        assert result[1].host == "1.1.1.1"
        assert result[2].host == "2.2.2.2"
