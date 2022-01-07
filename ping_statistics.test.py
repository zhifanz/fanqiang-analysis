import unittest
from decimal import Decimal

import test_helper
from domains import DomainRepository
from ping_statistics import arg_parser, parse_statistics, ping, Runner


class TestMain(unittest.TestCase):
    def test_parse_statistics(self):
        stdout = """
PING baidu.com (220.181.38.148) 56(84) bytes of data.

--- baidu.com ping statistics ---
10 packets transmitted, 5 received, 0% packet loss, time 4016ms
rtt min/avg/max/mdev = 62.263/68.017/75.407/4.884 ms
        """
        statistics = parse_statistics(stdout)
        self.assertEqual('220.181.38.148', statistics.destPublicIp)
        self.assertEqual(10, statistics.transmitted)
        self.assertEqual(5, statistics.received)
        self.assertEqual(Decimal('62.263'), statistics.min)
        self.assertEqual(Decimal('68.017'), statistics.avg)
        self.assertEqual(Decimal('75.407'), statistics.max)
        self.assertEqual(Decimal('4.884'), statistics.mdev)

    def test_parse_args(self):
        args = arg_parser().parse_args(
            ['--days', '3', '--pingcount', '5', 'domains', 'ap'])
        self.assertEqual(args.days, 3)
        self.assertEqual(args.pingcount, 5)
        self.assertEqual(args.table, 'domains')
        self.assertEqual(args.continent, 'ap')

    def test_ping(self):
        result = ping('bing.com', 5)
        self.assertEqual(result.code, 0)
        self.assertEqual(result.message, 'success')
        self.assertIsNotNone(result.statistics)

    def test_main(self):
        test_helper.create_dynamodb_table('domains', endpoint_url='http://localhost:8000')
        try:
            repository = DomainRepository('domains', endpoint_url='http://localhost:8000')
            repository.update_domain('baidu.com', 100000000)
            repository.update_domain('bing.com', 100000000)
            repository.update_domain('aliyun.com', 100000000)
            Runner(repository, 30, 10, 'domestic').run()
        finally:
            test_helper.delete_dynamodb_table('domains', endpoint_url='http://localhost:8000')


if __name__ == '__main__':
    unittest.main()
