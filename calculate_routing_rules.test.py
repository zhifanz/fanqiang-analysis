import unittest

from calculate_routing_rules import routing_rules


class TestMain(unittest.TestCase):

    def test_routing_rules_cn(self):
        rules = routing_rules([
            {
                'domainName': 'd1',
                'ping_cn': {'code': 0, 'statistics': {'transmitted': 10, 'received': 10}},
                'ping_na': {'code': 0, 'statistics': {'transmitted': 10, 'received': 10}}
            }
        ])
        self.assertDictEqual({'name': 'domestic', 'domains': ['d1']}, rules[0])
        self.assertDictEqual({'name': 'ap', 'domains': []}, rules[1])
        self.assertDictEqual({'name': 'eu', 'domains': []}, rules[2])
        rules = routing_rules([
            {
                'domainName': 'd1',
                'ping_cn': {'code': 2},
                'ping_na': {'code': 0, 'statistics': {'transmitted': 10, 'received': 10, 'avg': 10.23}}
            }
        ])
        self.assertDictEqual({'name': 'domestic', 'domains': []}, rules[0])

    def test_routing_rules_auto(self):
        rules = routing_rules([
            {
                'domainName': 'd1',
                'ping_cn': {'code': 2},
                'ping_ap': {'code': 2},
                'ping_na': {'code': 2},
                'ping_eu': {'code': 2}
            }
        ])
        self.assertDictEqual({'name': 'domestic', 'domains': []}, rules[0])
        self.assertDictEqual({'name': 'ap', 'domains': []}, rules[1])
        self.assertDictEqual({'name': 'eu', 'domains': []}, rules[2])

    def test_routing_rules_ap(self):
        rules = routing_rules([
            {
                'domainName': 'd1',
                'ping_cn': {'code': 2},
                'ping_ap': {'code': 0, 'statistics': {'avg': 10.23}},
                'ping_na': {'code': 2},
                'ping_eu': {'code': 2}
            }
        ])
        self.assertDictEqual({'name': 'domestic', 'domains': []}, rules[0])
        self.assertDictEqual({'name': 'ap', 'domains': ['d1']}, rules[1])
        self.assertDictEqual({'name': 'eu', 'domains': []}, rules[2])

    def test_routing_rules_eu(self):
        rules = routing_rules([
            {
                'domainName': 'd1',
                'ping_cn': {'code': 2},
                'ping_ap': {'code': 2},
                'ping_na': {'code': 2},
                'ping_eu': {'code': 0, 'statistics': {'avg': 10.23}}
            }
        ])
        self.assertDictEqual({'name': 'domestic', 'domains': []}, rules[0])
        self.assertDictEqual({'name': 'ap', 'domains': []}, rules[1])
        self.assertDictEqual({'name': 'eu', 'domains': ['d1']}, rules[2])

    def test_routing_rules_compare(self):
        rules = routing_rules([
            {
                'domainName': 'd1',
                'ping_cn': {'code': 2},
                'ping_ap': {'code': 0, 'statistics': {'avg': 13.23}},
                'ping_na': {'code': 0, 'statistics': {'avg': 12.23}},
                'ping_eu': {'code': 0, 'statistics': {'avg': 11.23}}
            }
        ])
        self.assertDictEqual({'name': 'domestic', 'domains': []}, rules[0])
        self.assertDictEqual({'name': 'ap', 'domains': []}, rules[1])
        self.assertDictEqual({'name': 'eu', 'domains': ['d1']}, rules[2])


if __name__ == '__main__':
    unittest.main()
