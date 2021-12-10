import unittest

from ping_statistics import parse_statistics


class TestMain(unittest.TestCase):
    def test_parse_statistics(self):
        stdout ="""
PING baidu.com (220.181.38.148) 56(84) bytes of data.

--- baidu.com ping statistics ---
10 packets transmitted, 5 received, 0% packet loss, time 4016ms
rtt min/avg/max/mdev = 62.263/68.017/75.407/4.884 ms
        """
        statistics = parse_statistics(stdout)
        self.assertEqual('220.181.38.148', statistics['public_ip'])
        self.assertEqual(10, statistics['transmitted'])
        self.assertEqual(5, statistics['received'])
        self.assertEqual(62.263, statistics['min'])
        self.assertEqual(68.017, statistics['avg'])
        self.assertEqual(75.407, statistics['max'])
        self.assertEqual(4.884, statistics['mdev'])


if __name__ == '__main__':
    unittest.main()
