import unittest

from ping_statistics import arg_parser, parse_statistics, ping


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
        self.assertEqual(62.263, statistics.min)
        self.assertEqual(68.017, statistics.avg)
        self.assertEqual(75.407, statistics.max)
        self.assertEqual(4.884, statistics.mdev)

    def test_parse_args(self):
        args = arg_parser().parse_args(
            ['--days', '3', '--pingcount', '5', 'domains', 'ap'])
        self.assertEqual(args.days, 3)
        self.assertEqual(args.pingcount, 5)
        self.assertEqual(args.table, 'domains')
        self.assertEqual(args.continent, 'ap')

    def test_ping(self):
        result = ping('google.com', 5)
        self.assertEqual(result.code, 0)
        self.assertEqual(result.message, 'success')
        self.assertIsNotNone(result.statistics)


if __name__ == '__main__':
    unittest.main()
