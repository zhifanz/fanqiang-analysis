import unittest

from calculate_routing_rules import routing_rules


class MockGlobalPingResults:
    def __init__(self, v1: bool, v2: str) -> None:
        self.v1 = v1
        self.v2 = v2

    def available_from_domestic(self):
        return self.v1

    def select_fast_proxy(self) -> str:
        return self.v2


class MockDomain:
    def __init__(self, domainName, v1, v2) -> None:
        self.domainName = domainName
        self.globalPingResults = MockGlobalPingResults(v1, v2)


class TestMain(unittest.TestCase):

    def test_routing_rules_cn(self):
        rules = routing_rules([
            MockDomain('d1', False, 'c1'),
            MockDomain('d2', False, 'c2'),
            MockDomain('d3', False, None),
            MockDomain('d4', True, 'c1')],
            ['c1', 'c2', 'c3']
        )
        self.assertDictEqual(
            {'domestic': ['d4'], 'c1': ['d1'], 'c2': ['d2'], 'c3': []}, rules)


if __name__ == '__main__':
    unittest.main()
