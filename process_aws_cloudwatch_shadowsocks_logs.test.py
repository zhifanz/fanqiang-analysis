import unittest

from process_aws_cloudwatch_shadowsocks_logs import extract_domain


class TestMain(unittest.TestCase):
    def test_extract_domain(self):
        self.assertEqual('w12t.anyhost.com.cn', extract_domain('<-> w12t.anyhost.com.cn:8766 info'))
        self.assertEqual('8.8.8.8', extract_domain('<-> 8.8.8.8:8766 info'))
        self.assertIsNone(extract_domain('<-> k8s:8766 info'))
        self.assertIsNone(extract_domain('baidu.com'))
        self.assertIsNone(extract_domain('baidu.com:80'))


if __name__ == '__main__':
    unittest.main()
