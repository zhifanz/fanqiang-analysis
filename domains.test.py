import unittest
import json

from domains import Domain, PingResult, PingStatistics


class Foo:
    def __init__(self) -> None:
        self.k1 = None
        self.k2 = None


class TestMain(unittest.TestCase):
    def test_create(self):
        self.assertIsNotNone(Foo())

    def test_json_to_object(self):
        foo = Foo()
        foo.__dict__.update(**{'k1': 7, 'k2': 12})
        self.assertEqual(7, foo.k1)

    def test_ping_result_to_dict(self):
        s = PingStatistics()
        s.destPublicIp = '8.8.8.8'
        s.transmitted = 10
        s.received = 9
        s.avg = 12.34
        s.min = 10.81
        s.max = 15.09
        s.mdev = 10.71
        d = PingResult(0, 'success', s).to_dict()
        self.assertEqual(0, d['code'])
        self.assertEqual('success', d['message'])
        self.assertEqual('8.8.8.8', d['statistics']['destPublicIp'])
        self.assertEqual(10, d['statistics']['transmitted'])
        self.assertEqual(9, d['statistics']['received'])
        self.assertEqual(12.34, d['statistics']['avg'])
        self.assertEqual(10.81, d['statistics']['min'])
        self.assertEqual(15.09, d['statistics']['max'])
        self.assertEqual(10.71, d['statistics']['mdev'])

    def test_create_domain_from_dict(self):
        d = Domain({'domainName': 'aws.amazon.com', 'lastAccessEpoch': 10000,
                   'globalPingResults': {'domestic': {'code': 0, 'message': 'success',
                                                      'statistics': {'destPublicIp': '8.8.8.8', 'transmitted': 10, 'received': 9, 'avg': 12.43}}, 'eu': {'code': 1, 'message': 'failed'}}})
        self.assertEqual('aws.amazon.com', d.domainName)
        self.assertEqual(10000, d.lastAccessEpoch)
        self.assertEqual(0, d.globalPingResults['domestic'].code)
        self.assertEqual('success', d.globalPingResults['domestic'].message)
        self.assertIsNotNone(d.globalPingResults['domestic'].statistics)
        self.assertEqual(1, d.globalPingResults['eu'].code)
        self.assertIsNone(d.globalPingResults['eu'].statistics)


if __name__ == '__main__':
    unittest.main()
